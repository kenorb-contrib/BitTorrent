#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
unichr, unichars, unilen, and uniord are workarounds for narrow python
builds; to_utf8 is useful when passing Unicode strings to UTF-8
library functions (filesystem, for example); to_unicode is useful when
passing UTF-8 strings to Unicode library functions (gui toolkits, for
example).
'''

import unicodedata
import re

def to_utf8(s):
    '''
    convert to utf-8 if not a bytestring, preserve otherwise
    '''
    if type(s) == type(''):
        pass
    elif type(s) == type(u''):
        s = s.encode('utf-8', 'replace')
    else:
        s = unicode(s).encode('utf-8', 'replace')
    return s

_fix_utf16_re = re.compile(ur'([\ud800-\udbff])([\udc00-\udfff])')

def fix_utf16(s):
    '''
    Convert UTF-16 surrogate pairs to corresponding Unicode characters.
    '''
    def _fix_utf16_pair(match):
        return (r'\U%08.8x' % (
            (((ord(match.group(1)) & 0x3ff) << 10) | (ord(match.group(2)) & 0x3ff)) + 0x10000)
                ).decode('unicode-escape')
    return to_unicode(_fix_utf16_re.sub(_fix_utf16_pair, to_unicode(s)))

def to_unicode(s):
    '''
    convert to unicode if not a unicode string, preserve otherwise; bytestrings are assumed to be utf-8
    '''
    return to_utf8(s).decode('utf-8')

_builtin_unichr = unichr

def _wide_unichr(i):
    '''
    unichr(i) -> Unicode character
    
    Return a Unicode string of one logical character with ordinal i; 0 <= i <= 0x10ffff.
    On a narrow python build this sometimes returns a surrogate pair.
    '''
    try:
        return _builtin_unichr(i)
    except ValueError, e:
        return (r'\U%08.8x' % i).decode('unicode-escape')

if len(u'\U0010fffd') == 2:
    unichr = _wide_unichr
else:
    unichr = _builtin_unichr

def unichars(us):
    '''
    This iterator yields each logical character in Unicode string us.
    On a narrow python build this sometimes yields a surrogate pair.
    '''
    assert type(us) == type(u'')
    resid = u''
    for ch in us:
        if len(u'\U0010fffd') == 2 and (((ord(ch) >> 10) << 10) == 0xd800):
            if resid:
                yield resid
            resid = ch
        elif resid and (((ord(ch) >> 10) << 10) == 0xdc00):
            yield resid + ch
            resid = u''
        else:
            if resid:
                assert len(resid == 1)
                yield resid
            yield ch
    if resid:
        yield resid

def unilen(us):
    '''
    Return the number of logical characters in the Unicode string us.
    On a narrow python build a surrogate pair counts as a single logical character.
    '''
    assert type(us) == type(u'')
    if len(u'\U0010fffd') == 2:
        return len([ uch for uch in unichars(us) ])
    return len(us)

def uniord(uch):
    '''
    uniord(uch) -> integer

    Return the integer ordinal of a one-character unicode string.
    On a narrow python build this will decode a surrogate pair.
    '''
    assert type(uch) == type(u'')
    if (len(uch) != 2) or (unilen(uch) != 1) or ((ord(uch[0]) >> 10) << 10) != 0xd800 or ((ord(uch[1]) >> 10) << 10) != 0xdc00:
        return ord(uch)
    return (((ord(uch[0]) & 0x3ff) << 10) | (ord(uch[1]) & 0x3ff)) + 0x10000

_unirepr_basic = {
    u'\n': r'\n',
    u'\r': r'\r',
    u'\t': r'\t',
    }

def unirepr(s):
    '''
    return a verbose equivalent of repr(s).

    NOTE: the output of this function is not portable across machines as it depends on the unicodedata revision.
    '''
    assert type(s) == type(u'')
    o = []
    for uch in unichars(s):
        try:
            o.append(r'\N{%s}' % unicodedata.name(uch))
        except:
            och = uniord(uch)
            if uch in _unirepr_basic:
                o.append(_unirepr_basic[uch])
            elif och < 0x100:
                o.append(r'\x%02.2x' % och)
            elif och < 0x10000:
                o.append(r'\u%04.4x' % och)
            else:
                o.append(r'\U%08.8x' % och)
    return r"u'%s'" % ''.join(o)

def test():
    '''
    smoke test to make sure the module is working.
    '''
    for i, o in (
        (1, '1'),
        ('hello, world!', 'hello, world!'),
        (u'hello, world!', 'hello, world!'),
        (u'hello, world! \u00ff \U0010fffd \N{WHITE SMILING FACE}',
         u'hello, world! \u00ff \U0010fffd \N{WHITE SMILING FACE}'.encode('utf-8')),
        (u'hello, world! \u00ff \U0010fffd \N{WHITE SMILING FACE}'.encode('utf-8'),
         u'hello, world! \u00ff \U0010fffd \N{WHITE SMILING FACE}'.encode('utf-8')),
        ):
        assert to_utf8(i) == o
        assert type(to_utf8(i)) == type('')
    for i, o in (
        (1, u'1'),
        ('hello, world!', u'hello, world!'),
        (u'hello, world!', u'hello, world!'),
        (u'hello, world! \u00ff \U0010fffd \N{WHITE SMILING FACE}',
         u'hello, world! \u00ff \U0010fffd \N{WHITE SMILING FACE}'),
        (u'hello, world! \u00ff \U0010fffd \N{WHITE SMILING FACE}'.encode('utf-8'),
         u'hello, world! \u00ff \U0010fffd \N{WHITE SMILING FACE}'),
        ):
        assert to_unicode(i) == o
        assert type(to_unicode(i)) == type(u'')
    for i, o in (
        (0, u'\0'),
        (0xa, u'\n'),
        (0x41, u'A'),
        (0x7f, u'\x7f'),
        (0x80, u'\x80'),
        (0x100, u'\u0100'),
        (0x10fffd, u'\U0010fffd'),
        ):
        assert unichr(i) == o
        assert uniord(o) == i
        assert eval(unirepr(o)) == o
    for i, o in (
        (u'hello, world!',
         (u'h', u'e', u'l', u'l', u'o', u',', u' ', u'w', u'o', u'r', u'l', u'd', u'!')),
        (u'hello, world! \u00ff \U0010fffd \N{WHITE SMILING FACE}',
         (u'h', u'e', u'l', u'l', u'o', u',', u' ', u'w', u'o', u'r', u'l', u'd', u'!', u' ', u'\u00ff', u' ', u'\U0010fffd', u' ', u'\N{WHITE SMILING FACE}')),
        ):
        assert tuple(unichars(i)) == o
        assert unilen(i) == len(o)
    for i, o in (
        (1, '1'),
        ('hello, world!', 'hello, world!'),
        (u'hello, world!', 'hello, world!'),
        (u'hello, world! \u00ff \U0010fffd \N{WHITE SMILING FACE}',
         u'hello, world! \u00ff \U0010fffd \N{WHITE SMILING FACE}'.encode('utf-8')),
        (u'hello, world! \u00ff \U0010fffd \N{WHITE SMILING FACE}'.encode('utf-8'),
         u'hello, world! \u00ff \U0010fffd \N{WHITE SMILING FACE}'.encode('utf-8')),
        (u'\ud800',
         u'\ud800'),
        (u'\udc00',
         u'\udc00'),
        (u'\ud800\udc00',
         u'\U00010000'),
        (u'\udbff\udfff',
         u'\U0010ffff'),
        ):
        assert fix_utf16(i) == to_unicode(o)
    pass

test()
