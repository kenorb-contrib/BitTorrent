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

Which type is encoded is determined by the first character, 'i', 'n',
'd', 'l' and any digit. They indicate integer, null, dict, list, and 
string, respectively.

Strings are length-prefixed in base 10, followed by a colon.

bencode('spam') == '4:spam'

Nulls are indicated by a single 'n'.

bencode(None) == 'n'

integers are encoded base 10 and terminated with an 'e'.

bencode(3) == 'i3e'
bencode(-20) == 'i-20e'

Lists are encoded in list order, terminated by an 'e' -

bencode(['abc', 'd']) == 'l3:abc1:de'
bencode([2, 'f']) == 'li2e1:fe'

Dicts are encoded by containing alternating keys and values, 
with the keys in sorted order, terminated by an 'e'. For example -

bencode({'spam': 'eggs'}) == 'd4:spam4:eggse'
bencode({'ab': 2, 'a': None}) == 'd1:an2:abi2ee'

Truncated strings come first, so in sort order 'a' comes before 'abc'.

If a function is passed to bencode, it's called and it's return value 
is included as a raw string, for example -

bdecode(bencode(lambda: None)) == None
"""

# This file is licensed under the GNU Lesser General Public License v2.1.
# originally written for Mojo Nation by Bryce Wilcox, Bram Cohen, and Greg P. Smith
# since then, almost completely rewritten by Bram Cohen

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
    encoder = encoders.get(type(data))
    assert encoder is not None, 'unsupported data type: ' + `type(data)`
    encoder(data, result)

encoders = {}

def encode_int(data, result):
    result.write('i' + str(data) + 'e')

encoders[IntType] = encode_int
encoders[LongType] = encode_int

def encode_list(data, result):
    result.write('l')
    for i in data:
        bwrite(i, result)
    result.write('e')

encoders[TupleType] = encode_list
encoders[ListType] = encode_list

def encode_string(data, result):
    result.write(str(len(data)) + ':' + data)

encoders[StringType] = encode_string

def encode_dict(data, result):
    result.write('d')
    keys = data.keys()
    keys.sort()
    for key in keys:
        assert type(key) is StringType, 'bencoded dictionary key must be a string'
        bwrite(key, result)
        bwrite(data[key], result)
    result.write('e')

encoders[DictType] = encode_dict

encoders[NoneType] = lambda data, result: result.write('n')

encoders[FunctionType] = lambda data, result: result.write(data())
encoders[MethodType] = encoders[FunctionType]

def bdecode(s):
    """
    Does the opposite of bencode. Raises a ValueError if there's a problem.
    """
    try:
        result, index = bread(s, 0)
        if index != len(s):
            raise ValueError('left over stuff at end')
        return result
    except IndexError, e:
        raise ValueError(str(e))
    except KeyError, e:
        raise ValueError(str(e))

def bread(s, index):
    return decoders[s[index]](s, index)

decoders = {}

_bre = re.compile(r'(0|[1-9][0-9]*):')

def decode_raw_string(s, index):
    x = _bre.match(s, index)
    if x is None:
        raise ValueError('invalid integer encoding')
    endindex = x.end() + long(s[index:x.end() - 1])
    if endindex > len(s):
        raise ValueError('length encoding indicated premature end of string')
    return s[x.end(): endindex], endindex

for c in '0123456789':
    decoders[c] = decode_raw_string

_int_re = re.compile(r'i(0|-?[1-9][0-9]*)e')

def decode_int(s, index):
    x = _int_re.match(s, index)
    if x is None:
        raise ValueError('invalid integer encoding')
    return long(s[index + 1:x.end() - 1]), x.end()

decoders['i'] = decode_int

decoders['n'] = lambda s, index: (None, index + 1)

def decode_list(s, index):
    result = []
    index += 1
    while s[index] != 'e':
        next, index = bread(s, index)
        result.append(next)
    return result, index + 1

decoders['l'] = decode_list

def decode_dict(s, index):
    result = {}
    index += 1
    prevkey = None
    while s[index] != 'e':
        key, index = decode_raw_string(s, index)
        if key <= prevkey:
            raise ValueError("out of order keys")
        prevkey = key
        value, index = bread(s, index)
        result[key] = value
    return result, index + 1

decoders['d'] = decode_dict

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
    except ValueError:
        pass
    try:
        decode_raw_string('', 0)
        assert 0, 'failed'
    except ValueError:
        pass
    try:
        decode_raw_string('5:a', 0)
        assert 0, 'failed'
    except ValueError:
        pass

def test_dict_enforces_order():
    bdecode('d1:an1:bne')
    try:
        bdecode('d1:bn1:ane')
        assert 0, 'failed'
    except ValueError:
        pass

def test_dict_forbids_non_string_key():
    try:
        bdecode('di3ene')
        assert 0, 'failed'
    except ValueError:
        pass

def test_dict_forbids_key_repeat():
    try:
        bdecode('d1:an1:ane')
        assert 0, 'failed'
    except ValueError:
        pass

def test_empty_dict():
    assert bdecode('de') == {}

def test_ValueError_in_decode_unknown():
    try:
        bdecode('x')
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
        bdecode('i03e')
        assert 0
    except ValueError:
        pass
    try:
        bdecode('i3 e')
        assert 0
    except ValueError:
        pass
    try:
        bdecode('i 3e')
        assert 0
    except ValueError:
        pass
    try:
        bdecode('i-0e')
        assert 0
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
        bdecode('ln')
        assert 0
    except ValueError:
        pass

def test_unfinished_dict():
    try:
        bdecode('d')
        assert 0
    except ValueError:
        pass
    try:
        bdecode('d1:a')
        assert 0
    except ValueError:
        pass
