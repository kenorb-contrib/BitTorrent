"""
A library for streaming and unstreaming of simple objects, designed
for speed, compactness, and ease of implementation.

The basic functions are bencode and bdecode. bencode takes an object 
and returns a string, bdecode takes a string and returns an object.
bdecode raises a ValueError if you give it an invalid string.

The objects passed in may be nested dicts, lists, ints, strings, 
and None. For example, all of the following may be bencoded -

{'a': [0, 1], 'b': None}

[None, ['a', 2, ['c', None]]]

{'spam': (2,3,4)}

{'name': 'Cronus', 'spouse': 'Rhea', 'children': ['Hades', 'Poseidon']}

In general bdecode(bencode(spam)) == spam, but tuples and lists are 
encoded the same, so bdecode(bencode((0, 1))) is [0, 1] rather 
than (0, 1). Longs and ints are also encoded the same way, so 
bdecode(bencode(4)) is a long.

dict keys are required to be strings, to avoid a mess of potential 
implementation incompatibilities. bencode is intended to be used 
for protocols which are going to be re-implemented many times, so 
it's very conservative in that regard.

Encoding is done as s-expressions. Strings are encoded in the raw, 
while other data structures are encoded as a list with the first 
element identifying the type, for example -

bencode('spam') == '4:spam'
bencode(None) == '(4:null)'
bencode(3) == '(3:int1:3)'
bencode(-20) == '(3:int3:-20)'

Lists are encoded in list order before the close parentheses, 
for example -

bencode(['abc', 'd']) == '(4:list1:abc3:d)'
bencode([2, 'f']) == '(4:list(3:int1:2)1:f)'

Dicts are encoded by containing alternating keys and values, 
with the keys in sorted order. For example -

bencode({'spam': 'eggs'}) == '(4:dict4:spam4:eggs)'
bencode({'ab': 2, 'a': None}) == '(4:dict1:a(4:null)2:ab(3:int1:2))'

Truncated strings come first, so in sort order 'a' comes before 'abc'.

If a function is passed to bencode, it's called and it's return value 
is included as a raw string, for example -

bdecode(bencode(lambda s = bencode('lots of stuff'): s)) == 'lots of stuff'

bencode and bdecode are very fascist. bwrite and bread are slightly 
more flexible, but harder to use properly. See their individual 
docstrings for more detail.
"""

# This file is licensed under the GNU Lesser General Public License v2.1.
# originally written for Mojo Nation, by Bram Cohen, based on an earlier version by Bryce Wilcox,
# with some speedups by Greg P. Smith
# The authors disclaim all liability for any damages resulting from
# any use of this software.

from types import *
from cStringIO import StringIO
import re

def bencode(data):
    """
    encodes objects as strings, see module documentation for more info
    """
    result = StringIO()
    bwrite(data, result)
    return result.getvalue()

def bwrite(data, result):
    """
    Repeatedly calls the write() method of result, passing it parts 
    of data encoded as an object.
    
    Mostly for internal use by bencode, but also can be used to do 
    the encoding directly to a stream.
    """
    encoder = encoders.get(type(data))
    assert encoder is not None, 'unsupported data type: ' + `type(data)`
    encoder(data, result)

encoders = {}

def encode_int(data, result):
    enc = str(data)
    # remove the ending 'L' that python 1.5.2 adds
    if enc[-1] == 'L':
        enc = enc[:-1]
    result.write('(3:int' + str(len(enc)) + ':' + enc + ')')

encoders[IntType] = encode_int
encoders[LongType] = encode_int

def encode_list(data, result):
    result.write('(4:list')
    for i in data:
        bwrite(i, result)
    result.write(')')

encoders[TupleType] = encode_list
encoders[ListType] = encode_list

encoders[StringType] = lambda data, result: result.write(str(len(data)) + ':' + data)
encoders[BufferType] = lambda data, result: result.write(str(len(data)) + ':' + str(data))

def encode_dict(data, result):
    result.write('(4:dict')
    keys = data.keys()
    keys.sort()
    for key in keys:
        assert type(key) in (StringType, BufferType), 'bencoded dictionary key ' + `key` + ' was not a string'
        bwrite(key, result)
        bwrite(data[key], result)
    result.write(')')

encoders[DictType] = encode_dict

encoders[NoneType] = lambda data, result: result.write('(4:null)')

encoders[FunctionType] = lambda data, result: result.write(data())
encoders[MethodType] = encoders[FunctionType]

def bdecode(s):
    """
    Does the opposite of bencode. Raises a ValueError if there's a problem.
    """
    assert type(s) == StringType

    try:
        result, index = bread(s, 0)
        if index != len(s):
            raise ValueError('left over stuff at end: ' + `s[index:]`)
        return result
    except IndexError, e:
        raise ValueError(str(e))

def bread(s, index):
    """
    reads an object off s starting at index
    
    returns the object read followed by the index after it - 
    s-expressions are self-delimiting
    
    Raises an IndexError if there's a problem which may have been 
    caused by truncation. Raises a ValueError if there's been some 
    garbling. Always gives strings the benefit of the doubt if 
    possible when deciding which exception to raise.
    
    mostly for internal use by bdecode, but can be used separately
    
    not pronounced like cooked fermented grain
    """
    if s[index] != '(':
        return decode_raw_string(s, index)
    next_type, index = decode_raw_string(s, index + 1)
    decoder = decoders.get(next_type)
    if decoder is None:
        raise ValueError('unknown data type ' + `next_type`)
    result, index = decoder(s, index)
    if s[index] != ')':
        raise ValueError('object encodings must end with a close parentheses, was ' + `s[index]`)
    return result, index + 1

decoders = {}

# being canonical, simply using int() wouldn't complain about 01 or -0
_nonnegative_int_re = re.compile(r'^(0|[1-9][0-9]*)$')

def decode_raw_string(s, index):
    index2 = s.find(':', index)
    if index2 == -1:
        if index == len(s) or _nonnegative_int_re.match(s[index:]):
            raise IndexError('length encoding clipped before colon')
        raise ValueError('invalid integer encoding ' + `s[index:]`)
    numstring = s[index:index2]
    if not _nonnegative_int_re.match(numstring):
        raise ValueError('invalid integer encoding: ' + `numstring`)
    endindex = index2 + 1 + int(numstring)
    if endindex > len(s):
        raise IndexError('length encoding indicated premature end of string')
    return s[index2 + 1: endindex], endindex

_int_re = re.compile(r'^(0|-?[1-9][0-9]*)$')

def decode_int(s, index):
    n, index = decode_raw_string(s, index)
    if not _int_re.match(n):
        raise ValueError("non canonical integer: " + `n`)
    return long(n), index

decoders['int'] = decode_int

decoders['null'] = lambda s, index: (None, index)

def decode_list(s, index):
    result = []
    while s[index] != ')':
        next, index = bread(s, index)
        result.append(next)
    return result, index

decoders['list'] = decode_list

def decode_dict(s, index):
    result = {}
    firstkey = 1

    while s[index] != ')':
        key, index = bread(s, index)
        if type(key) is not StringType:
            raise ValueError, 'keys other than strings not permitted'
        value, index = bread(s, index)
        if firstkey:
            firstkey = 0
        else:
            if key <= prevkey:
                raise ValueError("out of order keys, %s is not greater than %s" % (`key`, `prevkey`))
        prevkey = key
        result[key] = value
    return result, index

decoders['dict'] = decode_dict

def test_decode_raw_string():
    assert decode_raw_string('1:a', 0) == ('a', 3)
    assert decode_raw_string('0:', 0) == ('', 2)
    assert decode_raw_string('10:aaaaaaaaaaaaaaaaaaaaaaaaa', 0) == ('aaaaaaaaaa', 13)
    assert decode_raw_string('10:', 1) == ('', 3)
    try:
        decode_raw_string('01:a', 0)
        assert 0, 'failed'
    except ValueError:
        pass
    try:
        decode_raw_string('--1:a', 0)
        assert 0, 'failed'
    except ValueError:
        pass
    try:
        decode_raw_string('h', 0)
        assert 0, 'failed'
    except ValueError:
        pass
    try:
        decode_raw_string('h:', 0)
        assert 0, 'failed'
    except ValueError:
        pass
    try:
        decode_raw_string('1', 0)
        assert 0, 'failed'
    except IndexError:
        pass
    try:
        decode_raw_string('', 0)
        assert 0, 'failed'
    except IndexError:
        pass
    try:
        decode_raw_string('5:a', 0)
        assert 0, 'failed'
    except IndexError:
        pass

def test_dict_enforces_order():
    bdecode('(4:dict1:a(4:null)1:b(4:null))')
    try:
        bdecode('(4:dict1:b(4:null)1:a(4:null))')
        assert 0, 'failed'
    except ValueError:
        pass

def test_dict_forbids_non_string_key():
    try:
        bdecode('(4:dict(3:int1:3)(4:null))')
        assert 0, 'failed'
    except ValueError:
        pass

def test_dict_forbids_key_repeat():
    try:
        bdecode('(4:dict1:a(4:null)1:a(4:null))')
        assert 0, 'failed'
    except ValueError:
        pass

def test_forbids_non_raw_string_dict_key():
    try:
        bdecode('(4:dict(5:string1:a)(4:null))')
        assert 0, 'failed'
    except ValueError:
        pass

def test_empty_dict():
    assert bdecode('(4:dict)') == {}

def test_ValueError_in_decode_unknown():
    try:
        bdecode('(7:garbage)')
        assert 0, 'flunked'
    except ValueError:
        pass

def test_encode_and_decode_none():
    assert bdecode(bencode(None)) == None

def test_encode_and_decode_long():
    assert bdecode(bencode(-23452422452342L)) == -23452422452342L

def test_encode_and_decode_int():
    assert bdecode(bencode(2)) == 2

def test_decode_noncanonical_int():
    try:
        bdecode('(3:int2:03)')
        assert 0, "non canonical integer allowed '03'"
    except ValueError:
        pass
    try:
        bdecode('(3:int2:3 )')
        assert 0, "non canonical integer allowed '3 '"
    except ValueError:
        pass
    try:
        bdecode('(3:int2: 3)')
        assert 0, "non canonical integer allowed ' 3'"
    except ValueError:
        pass
    try:
        bdecode('(3:int2:-0)')
        assert 0, "non canonical integer allowed '-0'"
    except ValueError:
        pass

def test_encode_and_decode_dict():
    x = {'42': 3}
    assert bdecode(bencode(x)) == x

def test_encode_and_decode_list():
    assert bdecode(bencode([])) == []

def test_encode_and_decode_tuple():
    assert bdecode(bencode(())) == []

def test_encode_and_decode_empty_dict():
    assert bdecode(bencode({})) == {}

def test_encode_and_decode_complex_object():
    spam = [[], 0, -3, -345234523543245234523L, {}, 'spam', None, {'a': [3]}, {}]
    assert bencode(bdecode(bencode(spam))) == bencode(spam)
    assert bdecode(bencode(spam)) == spam

def test_unfinished_list():
    try:
        bdecode('(4:list')
        assert 0
    except ValueError:
        pass

def test_unfinished_dict():
    try:
        bdecode('(4:dict')
        assert 0
    except ValueError:
        pass
    try:
        bdecode('(4:dict1:a')
        assert 0
    except ValueError:
        pass

def test_buffertype():
    assert bdecode(bencode(buffer('a'))) == 'a'
    assert bdecode(bencode({buffer('a'): 'b'})) == {'a': 'b'}
