#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
escaping functions for XML, XHTML, URIs, IRIs, JavaScript and ECMAScript
'''

import re
import urllib
import cgi
import string

from BTL.canonical.unicode import unichr, uniord, to_unicode, to_utf8, fix_utf16
from BTL.canonical.user import canon_lang as _canon_lang

_xmlutf8_re = re.compile(r'((?:[\xc4-\xcf\xd2\xd4][\x80-\xbf]|\xc2[\xa0-\xbf]|[\xc3\xd0\xd1\xd3\xd5-\xdf][\x80-\xbf]|[\xe1-\xec][\x80-\xbf]{2,2}|[\x09\x0a\x0d\x20-\x7e]|\xe0[\xa0-\xbf][\x80-\xbf]|[\xf2\xf3](?:[\x8f\x9f\xaf\xbf](?:[\x80-\xbe][\x80-\xbf]|\xbf[\x80-\xbd])|[\x80-\x8e\x90-\x9e\xa0-\xae\xb0-\xbd][\x80-\xbf]{2,2}|\xbe[\x80-\xbf]{2,2})|\xed[\x80-\x9f][\x80-\xbf]|\xef(?:[\x80-\xbe][\x80-\xbf]|\xbf[\x80-\xbd])|\xee[\x80-\xbf]{2,2}|\xf1(?:[\x8f\x9f\xaf\xbf](?:[\x80-\xbe][\x80-\xbf]|\xbf[\x80-\xbd])|[\x80-\x8e\x90-\x9e\xa0-\xae\xb0-\xbd][\x80-\xbf]{2,2}|\xbe[\x80-\xbf]{2,2})|\xf0(?:[\x9f\xaf\xbf](?:[\x80-\xbe][\x80-\xbf]|\xbf[\x80-\xbd])|[\x90-\x9e\xa0-\xae\xb0-\xbd][\x80-\xbf]{2,2}|\xbe[\x80-\xbf]{2,2})|\xf4(?:[\x80-\x8e][\x80-\xbf]{2,2}|\x8f(?:[\x80-\xbe][\x80-\xbf]|\xbf[\x80-\xbd]))){1,1024})|.', re.DOTALL)

def fix_xmlutf8(s):
    '''
    Convert control characters (C0 and C1) and invalid UTF-8 sequences to the UTF-8 encoding of the Unicode replacement character.
    '''
    o = []
    for match in _xmlutf8_re.finditer(to_utf8(s)):
        if match.group(1):
            o.append(match.group(1))
        else:
            o += [ u'\ufffd'.encode('utf-8') * len(match.group(0)) ]
    return ''.join(o)

_xml_escapes_re = re.compile(ur'([<&>\"]{1,1024})|([\'\s])|[^<&>"\'\s]{1,1024}', re.DOTALL | re.UNICODE)
def xml_escape(s):
    '''
    Serialize a UTF-8 or Unicode string for use inside a UTF-8 XML or XHTML document.

    Characters not allowed in XML or XHTML documents are converted to the Unicode replacement character.

    Whitespace characters are encoded as numeric character references.
    '''
    o = []
    for match in _xml_escapes_re.finditer(to_unicode(fix_xmlutf8(s))):
        if match.group(1):
            o.append(cgi.escape(match.group(0).encode('utf-8', 'replace'), quote = True))
        elif match.group(2):
            o.append('&#%d;' % uniord(match.group(0)))
        else:
            o.append(match.group(0).encode('utf-8', 'replace'))
    return ''.join(o)

def uri_escape(s):
    '''
    Escape a UTF-8 or Unicode string for use inside a URI or IRI.
    '''
    return urllib.quote(to_utf8(s), safe = '')

_js_escape_re = re.compile(ur'(?P<pyquote>[\n\r\t])|(?P<backslash>[\\\"\'])|(?P<uniquote>[^\x20-\x7e])|(?P<empty>/>)|(?P<close></)|(?P<ccdata>]]>)|(?P<entityref>&)')

def js_escape(s):
    '''
    Escape a UTF-8 or Unicode string for use inside a JavaScript or
    ECMAScript string literal, potentially for embedding in SGML or
    XML PCDATA or CDATA.
    '''
    def _js_escape_char(match):
        ch = match.group(0)
        if match.groupdict()['pyquote']:
            return ch.encode('unicode-escape')
        if match.groupdict()['backslash']:
            return r'\%s' % ch
        if match.groupdict()['empty']:
            return r'\x2f>'
        if match.groupdict()['close']:
            return r'<\x2f'
        if match.groupdict()['ccdata']:
            return r'\x5d]>'
        if match.groupdict()['entityref']:
            return r'\x26'
        och = uniord(ch)
        if och > 0x10ffff:
            assert "Codepoints outside the UTF-16 range are not supported." [:0]
        if och > 0xffff:
            # do UTF-16 encoding for chars outside the BMP
            return r'\u%04.4x\u%04.4x' % (
                ((och - 0x10000) >> 10) | 0xd800,
                ((och - 0x10000) & 0x3ff) | 0xdc00)
        if och > 0xff:
            return r'\u%04.04x' % och
        return r'\x%02.2x' % och
    return to_utf8(_js_escape_re.sub(_js_escape_char, to_unicode(s)))

_js_unescape_re = re.compile(ur'(?:\\[bfnrtv\'\"\\]|\\[0-7]{1,3}|\\x[0-9a-fA-F]{2,2}|\\u[0-9a-fA-F]{4,4})')

def js_unescape(s):
    '''
    Unescape a JavaScript or ECMAScript string literal. Note that this
    also decodes \\v, which is not part of the ECMAScript standard.
    '''
    def _js_unescape_char(match):
        return match.group(0).decode('unicode-escape')
    return to_unicode(fix_utf16(_js_unescape_re.sub(_js_unescape_char, to_unicode(s))))

def embed_text(text, xml_lang = None, xhtml_dir = 'ltr'):
    '''
    Prepare a span of plain text for embedding in arbitrary other
    plain text.  Each line of the span is wrapped in [RFC2482]
    language tags corresponding to xml_lang (if xml_lang is neither
    empty nor None) and a Unicode bidirectional embedding of the
    xhtml_dir direction (default is "ltr" for left-to-right; "rtl" for
    right-to-left is also allowed.)

    An empty string or None is simply returned.

    The result is returned as a UTF-8 string.

    References

    [RFC2482] Whistler, K. and Adams, G., "Language Tagging in Unicode
    Plain Text", RFC 2482, January 1999.
    '''
    if text is None:
        return None
    if not text:
        return to_utf8(text)
    text = to_unicode(text)
    def _tag_line(line):
        line = to_unicode(line)
        if line and xml_lang:
            tag = u''.join([ unichr(uniord(u'\N{TAG LATIN CAPITAL LETTER A}') - uniord(u'A') + uniord(ch)) for ch in to_unicode(_canon_lang(xml_lang)) ])
            line = u'\N{LANGUAGE TAG}' + tag + line + u'\N{LANGUAGE TAG}\N{CANCEL TAG}'
        return line
    def _splitlines(text):
        return u'\n'.join(u'\n'.join(text.split(u'\r\n')).split('\r')).split('\n')
    return '\r\n'.join(
        [
        (
        _tag_line(line)
        and
        to_utf8(u'%s%s\N{POP DIRECTIONAL FORMATTING}' % (
        { 'ltr': u'\N{LEFT-TO-RIGHT EMBEDDING}',
          'rtl': u'\N{RIGHT-TO-LEFT EMBEDDING}' }[xhtml_dir],
        _tag_line(line),
        ))
        or
        to_utf8(line)
        )
        for line in _splitlines(to_unicode(text))
        ]
        )

def embed_xhtml(xhtml, xml_lang = None, xhtml_dir = 'ltr'):
    '''
    Prepare a span of XHTML text for embedding in arbitrary other
    XHTML text.  Each line of the span is wrapped in language tags
    corresponding to xml_lang (if xml_lang is neither empty nor None)
    and a Unicode bidirectional embedding of the xhtml_dir direction
    (default is "ltr" for left-to-right; "rtl" for right-to-left is
    also allowed.)

    An empty string or None is simply returned.

    The result is returned as a UTF-8 string.
    '''
    if xhtml is None:
        return None
    if not xhtml:
        return to_utf8(xhtml)
    xhtml = to_utf8(xhtml)
    assert xhtml_dir in ('ltr', 'rtl')
    return to_utf8('<span dir="%s"%s>%s</span>' % (
        to_utf8(xhtml_dir),
        (xml_lang and (' xml:lang="%s"' % _canon_lang(xml_lang)) or ''),
        xhtml))

def smash(text):
    '''
    This function was created to turn a unicode string with bad URL
    characters into the same string, but replacing the bad URL
    characters with underscores.  It is NOT reversible, so it's only
    useful in places where you really just want to end up with
    SOMETHING safe and aren't worried about being destructive
    '''

    if text is None: return None

    chars_to_trans = ' \'/&?=@%#":,()'

    if isinstance(text, unicode):
        # replace non-ASCII unicode chars with '?', which becomes '_' below
        text = text.encode('ascii', 'replace')

    trans = string.maketrans(chars_to_trans, '_'*len(chars_to_trans))
    return text.translate(trans)

def test():
    '''
    Tiny smoke test to make sure the funcitons in this library work.
    '''
    for i, o in (
        ('', ''),
        ('Hello, world!', 'Hello, world!'),
        (u'Hello, world!', 'Hello, world!'),
        (u'\N{DOLLAR SIGN}\N{POUND SIGN}\N{EURO SIGN}\N{YEN SIGN}',
         u'\N{DOLLAR SIGN}\N{POUND SIGN}\N{EURO SIGN}\N{YEN SIGN}'.encode('utf-8')),
        ('\x00', to_utf8(u'\ufffd')),
        ('\x1f', to_utf8(u'\ufffd')),
        ('\x7f', to_utf8(u'\ufffd')),
        ('\x80', to_utf8(u'\ufffd')),
        ('\x84', to_utf8(u'\ufffd')),
        ('\x86', to_utf8(u'\ufffd')),
        ('\x9f', to_utf8(u'\ufffd')),
        ('\xa0', to_utf8(u'\ufffd')),
        (u'\x80', ''.join([ to_utf8(u'\ufffd') for x in to_utf8(u'\x80') ])),
        (u'\x84', ''.join([ to_utf8(u'\ufffd') for x in to_utf8(u'\x84') ])),
        (u'\x85', ''.join([ to_utf8(u'\ufffd') for x in to_utf8(u'\x85') ])),
        (u'\x86', ''.join([ to_utf8(u'\ufffd') for x in to_utf8(u'\x86') ])),
        (u'\x8f', ''.join([ to_utf8(u'\ufffd') for x in to_utf8(u'\x8f') ])),
        (u'\xa0', to_utf8(u'\xa0')),
        (u'\xa1', to_utf8(u'\xa1')),
        (u'\u3000', to_utf8(u'\u3000')),
        (u'\ud800', ''.join([ to_utf8(u'\ufffd') for x in to_utf8(u'\ud800') ])),
        (u'\udbff', ''.join([ to_utf8(u'\ufffd') for x in to_utf8(u'\udbff') ])),
        (u'\udc00', ''.join([ to_utf8(u'\ufffd') for x in to_utf8(u'\udc00') ])),
        (u'\udfff', ''.join([ to_utf8(u'\ufffd') for x in to_utf8(u'\udfff') ])),
        (u'\uff21', to_utf8(u'\uff21')),
        (u'\ufffd', to_utf8(u'\ufffd')),
        (u'\uffff', ''.join([ to_utf8(u'\ufffd') for x in to_utf8(u'\uffff') ])),
        (u'\U00010000', to_utf8(u'\U00010000')),
        (u'\U0001ffff', ''.join([ to_utf8(u'\ufffd') for x in to_utf8(u'\U0001ffff') ])),
        (u'\U0010fffd', to_utf8(u'\U0010fffd')),
        (u'\U0010ffff', ''.join([ to_utf8(u'\ufffd') for x in to_utf8(u'\U0010ffff') ])),
        ('<\"\'>&;/! \0\a\b\n\r\t\v\f',
         to_utf8(u'<\"\'>&;/! \ufffd\ufffd\ufffd\n\r\t\ufffd\ufffd')),
        (u'\t\n\r\r ~\xa0\ud7ff\ue000\ufffd\U00010000\U0001fffd\U00020000\U0002fffd\U00030000\U0003fffd\U00040000\U0004fffd\U00050000\U0005fffd\U00060000\U0006fffd\U00070000\U0007fffd\U00080000\U0008fffd\U00090000\U0009fffd\U000a0000\U000afffd\U000b0000\U000bfffd\U000c0000\U000cfffd\U000d0000\U000dfffd\U000e0000\U000efffd\U000f0000\U000ffffd\U00100000\U0010fffd',
         u'\t\n\r\r ~\xa0\ud7ff\ue000\ufffd\U00010000\U0001fffd\U00020000\U0002fffd\U00030000\U0003fffd\U00040000\U0004fffd\U00050000\U0005fffd\U00060000\U0006fffd\U00070000\U0007fffd\U00080000\U0008fffd\U00090000\U0009fffd\U000a0000\U000afffd\U000b0000\U000bfffd\U000c0000\U000cfffd\U000d0000\U000dfffd\U000e0000\U000efffd\U000f0000\U000ffffd\U00100000\U0010fffd'.encode('utf-8')),
        (u'\x00\x01\x02\x03\x04\x05\x06\x07\x08\x0b\x0c\x0e\x0f\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f\x7f\x80\x81\x82\x83\x84\x85\x86\x87\x88\x89\x8a\x8b\x8c\x8d\x8e\x8f\x90\x91\x92\x93\x94\x95\x96\x97\x98\x99\x9a\x9b\x9c\x9d\x9e\x9f\udc00\udfff\ud800\udbff\ufffe\uffff\U0001fffe\U0001ffff\U0002fffe\U0002ffff\U0003fffe\U0003ffff\U0004fffe\U0004ffff\U0005fffe\U0005ffff\U0006fffe\U0006ffff\U0007fffe\U0007ffff\U0008fffe\U0008ffff\U0009fffe\U0009ffff\U000afffe\U000affff\U000bfffe\U000bffff\U000cfffe\U000cffff\U000dfffe\U000dffff\U000efffe\U000effff\U000ffffe\U000fffff\U0010fffe',
         u''.join([ u'\ufffd' for ch in u'\x00\x01\x02\x03\x04\x05\x06\x07\x08\x0b\x0c\x0e\x0f\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f\x7f\x80\x81\x82\x83\x84\x85\x86\x87\x88\x89\x8a\x8b\x8c\x8d\x8e\x8f\x90\x91\x92\x93\x94\x95\x96\x97\x98\x99\x9a\x9b\x9c\x9d\x9e\x9f\udc00\udfff\ud800\udbff\ufffe\uffff\U0001fffe\U0001ffff\U0002fffe\U0002ffff\U0003fffe\U0003ffff\U0004fffe\U0004ffff\U0005fffe\U0005ffff\U0006fffe\U0006ffff\U0007fffe\U0007ffff\U0008fffe\U0008ffff\U0009fffe\U0009ffff\U000afffe\U000affff\U000bfffe\U000bffff\U000cfffe\U000cffff\U000dfffe\U000dffff\U000efffe\U000effff\U000ffffe\U000fffff\U0010fffe'.encode('utf-8') ]).encode('utf-8')),
        ):
        assert fix_xmlutf8(i) == o
    for i, o in (
        ('', ''),
        ('Hello, world!', 'Hello,&#32;world!'),
        (u'Hello, world!', 'Hello,&#32;world!'),
        (u'\N{DOLLAR SIGN}\N{POUND SIGN}\N{EURO SIGN}\N{YEN SIGN}',
         u'\N{DOLLAR SIGN}\N{POUND SIGN}\N{EURO SIGN}\N{YEN SIGN}'.encode('utf-8')),
        ('<', '&lt;'),
        ('>', '&gt;'),
        ('&', '&amp;'),
        ('\"', '&quot;'),
        ('\'', '&#39;'),
        (' ', '&#32;'),
        ('\n', '&#10;'),
        ('\r', '&#13;'),
        ('\t', '&#9;'),
        ('\x00', to_utf8(u'\ufffd')),
        ('\x1f', to_utf8(u'\ufffd')),
        ('\x7f', to_utf8(u'\ufffd')),
        ('\x80', to_utf8(u'\ufffd')),
        ('\x84', to_utf8(u'\ufffd')),
        ('\x86', to_utf8(u'\ufffd')),
        ('\x9f', to_utf8(u'\ufffd')),
        ('\xa0', to_utf8(u'\ufffd')),
        (u'\x80', ''.join([ to_utf8(u'\ufffd') for x in to_utf8(u'\x80') ])),
        (u'\x84', ''.join([ to_utf8(u'\ufffd') for x in to_utf8(u'\x84') ])),
        (u'\x85', ''.join([ to_utf8(u'\ufffd') for x in to_utf8(u'\x85') ])),
        (u'\x86', ''.join([ to_utf8(u'\ufffd') for x in to_utf8(u'\x86') ])),
        (u'\x8f', ''.join([ to_utf8(u'\ufffd') for x in to_utf8(u'\x8f') ])),
        (u'\xa0', '&#160;'),
        (u'\xa1', to_utf8(u'\xa1')),
        (u'\u3000', '&#12288;'),
        (u'\ud800', ''.join([ to_utf8(u'\ufffd') for x in to_utf8(u'\ud800') ])),
        (u'\udbff', ''.join([ to_utf8(u'\ufffd') for x in to_utf8(u'\udbff') ])),
        (u'\udc00', ''.join([ to_utf8(u'\ufffd') for x in to_utf8(u'\udc00') ])),
        (u'\udfff', ''.join([ to_utf8(u'\ufffd') for x in to_utf8(u'\udfff') ])),
        (u'\uff21', to_utf8(u'\uff21')),
        (u'\ufffd', to_utf8(u'\ufffd')),
        (u'\uffff', ''.join([ to_utf8(u'\ufffd') for x in to_utf8(u'\uffff') ])),
        (u'\U00010000', to_utf8(u'\U00010000')),
        (u'\U0001ffff', ''.join([ to_utf8(u'\ufffd') for x in to_utf8(u'\U0001ffff') ])),
        (u'\U0010fffd', to_utf8(u'\U0010fffd')),
        (u'\U0010ffff', ''.join([ to_utf8(u'\ufffd') for x in to_utf8(u'\U0010ffff') ])),
        ('<\"\'>&;/! \0\a\b\n\r\t\v\f',
         to_utf8(u'&lt;&quot;&#39;&gt;&amp;;/!&#32;\ufffd\ufffd\ufffd&#10;&#13;&#9;\ufffd\ufffd')),
        (u'\t\n\r\r ~\xa0\ud7ff\ue000\ufffd\U00010000\U0001fffd\U00020000\U0002fffd\U00030000\U0003fffd\U00040000\U0004fffd\U00050000\U0005fffd\U00060000\U0006fffd\U00070000\U0007fffd\U00080000\U0008fffd\U00090000\U0009fffd\U000a0000\U000afffd\U000b0000\U000bfffd\U000c0000\U000cfffd\U000d0000\U000dfffd\U000e0000\U000efffd\U000f0000\U000ffffd\U00100000\U0010fffd',
         u'&#9;&#10;&#13;&#13;&#32;~&#160;\ud7ff\ue000\ufffd\U00010000\U0001fffd\U00020000\U0002fffd\U00030000\U0003fffd\U00040000\U0004fffd\U00050000\U0005fffd\U00060000\U0006fffd\U00070000\U0007fffd\U00080000\U0008fffd\U00090000\U0009fffd\U000a0000\U000afffd\U000b0000\U000bfffd\U000c0000\U000cfffd\U000d0000\U000dfffd\U000e0000\U000efffd\U000f0000\U000ffffd\U00100000\U0010fffd'.encode('utf-8')),
        (u'\x00\x01\x02\x03\x04\x05\x06\x07\x08\x0b\x0c\x0e\x0f\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f\x7f\x80\x81\x82\x83\x84\x85\x86\x87\x88\x89\x8a\x8b\x8c\x8d\x8e\x8f\x90\x91\x92\x93\x94\x95\x96\x97\x98\x99\x9a\x9b\x9c\x9d\x9e\x9f\udc00\udfff\ud800\udbff\ufffe\uffff\U0001fffe\U0001ffff\U0002fffe\U0002ffff\U0003fffe\U0003ffff\U0004fffe\U0004ffff\U0005fffe\U0005ffff\U0006fffe\U0006ffff\U0007fffe\U0007ffff\U0008fffe\U0008ffff\U0009fffe\U0009ffff\U000afffe\U000affff\U000bfffe\U000bffff\U000cfffe\U000cffff\U000dfffe\U000dffff\U000efffe\U000effff\U000ffffe\U000fffff\U0010fffe',
         u''.join([ u'\ufffd' for ch in u'\x00\x01\x02\x03\x04\x05\x06\x07\x08\x0b\x0c\x0e\x0f\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f\x7f\x80\x81\x82\x83\x84\x85\x86\x87\x88\x89\x8a\x8b\x8c\x8d\x8e\x8f\x90\x91\x92\x93\x94\x95\x96\x97\x98\x99\x9a\x9b\x9c\x9d\x9e\x9f\udc00\udfff\ud800\udbff\ufffe\uffff\U0001fffe\U0001ffff\U0002fffe\U0002ffff\U0003fffe\U0003ffff\U0004fffe\U0004ffff\U0005fffe\U0005ffff\U0006fffe\U0006ffff\U0007fffe\U0007ffff\U0008fffe\U0008ffff\U0009fffe\U0009ffff\U000afffe\U000affff\U000bfffe\U000bffff\U000cfffe\U000cffff\U000dfffe\U000dffff\U000efffe\U000effff\U000ffffe\U000fffff\U0010fffe'.encode('utf-8') ]).encode('utf-8')),
        ):
        assert xml_escape(i) == o
    for i, o in (
        ('hello, world!', 'hello%2C%20world%21'),
        (':/@[.]?=;&#', '%3A%2F%40%5B.%5D%3F%3D%3B%26%23'),
        ('\x00\x1f\x20\x7f\x80\xff', '%00%1F%20%7F%80%FF'),
        (u'\x00\x1f\x20\x7f\x80\xff\u0100\ufffd\U00010000\U0010fffd',
         '%00%1F%20%7F%C2%80%C3%BF%C4%80%EF%BF%BD%F0%90%80%80%F4%8F%BF%BD'),
        (u'\N{DOLLAR SIGN}\N{POUND SIGN}\N{EURO SIGN}\N{YEN SIGN}',
         '%24%C2%A3%E2%82%AC%C2%A5'),
        ):
        assert uri_escape(i) == o
    for i, o2, o in (
        ('\n', r'\12', r'\n'),
        ('\r', r'\15', r'\r'),
        ('\t', r'\11', r'\t'),
        ('\"', r'\42', r'\"'),
        ('\'', r'\47', r'\''),
        ('\\', r'\134', r'\\'),
        ('A', r'\101', 'A'),
        (u'A', r'\101', 'A'),
        ('Hello, world!', '\110\145\154\154\157\54\40\167\157\162\154\144\41', 'Hello, world!'),
        (u'\0\a\b\n\r\t\v\f\"\\\"\'\\\'\x7f\x80\x81\xff\u0100\ufffd\U00010000\U0010fffd',
         ur'\0\x07\b\n\r\t\v\f\"\\\"\'\\\'\x7f\x80\x81\xff\u0100\ufffd\ud800\udc00\udbff\udffd',
         r'\x00\x07\x08\n\r\t\x0b\x0c\"\\\"\'\\\'\x7f\x80\x81\xff\u0100\ufffd\ud800\udc00\udbff\udffd'),
        (u'\N{DOLLAR SIGN}\N{POUND SIGN}\N{EURO SIGN}\N{YEN SIGN}',
         ur'\u0024\u00a3\u20ac\u00a5',
         r'$\xa3\u20ac\xa5'),
        (u'<\"\'>&;/! \0\a\b\n\r\t\v\f',
         ur'<\"\'>&;/! \0\7\b\n\r\t\v\f',
         r'<\"\'>\x26;/! \x00\x07\x08\n\r\t\x0b\x0c'),
        (u"// This <hack /> shouldn't close the </script> tag! < / > Nor should this close a <![CDATA[ CDATA section ]]>",
         ur"// This <hack /> shouldn't close the </script> tag! < / > Nor should this close a <![CDATA[ CDATA section ]]>",
         r"// This <hack \x2f> shouldn\'t close the <\x2fscript> tag! < / > Nor should this close a <![CDATA[ CDATA section \x5d]>"),
        ):
        assert js_unescape(js_escape(i)) == i
        assert js_escape(i) == o
        assert js_unescape(o) == i
        assert js_unescape(o2) == i
    for i, o_xhtml, o_text in (
        ((None, ), None, None),
        (('', ), '', ''),
        (('x', ), '<span dir="ltr">x</span>', to_utf8(u'\N{LEFT-TO-RIGHT EMBEDDING}x\N{POP DIRECTIONAL FORMATTING}')),
        (('&lt;&gt;&amp;<img />', ), '<span dir="ltr">&lt;&gt;&amp;<img /></span>', to_utf8(u'\N{LEFT-TO-RIGHT EMBEDDING}&lt;&gt;&amp;<img />\N{POP DIRECTIONAL FORMATTING}')),
        (('a\nb', ), '<span dir="ltr">a\nb</span>', to_utf8(u'\N{LEFT-TO-RIGHT EMBEDDING}a\N{POP DIRECTIONAL FORMATTING}\r\n\N{LEFT-TO-RIGHT EMBEDDING}b\N{POP DIRECTIONAL FORMATTING}')),
        (('a\nb\n', ), '<span dir="ltr">a\nb\n</span>', to_utf8(u'\N{LEFT-TO-RIGHT EMBEDDING}a\N{POP DIRECTIONAL FORMATTING}\r\n\N{LEFT-TO-RIGHT EMBEDDING}b\N{POP DIRECTIONAL FORMATTING}\r\n')),
        ((None, 'EN-US', ), None, None),
        (('', 'EN-US', ), '', ''),
        (('x', 'EN-US', ), '<span dir="ltr" xml:lang="en-US">x</span>', to_utf8(u'\N{LEFT-TO-RIGHT EMBEDDING}\N{LANGUAGE TAG}\N{TAG LATIN SMALL LETTER E}\N{TAG LATIN SMALL LETTER N}\N{TAG HYPHEN-MINUS}\N{TAG LATIN CAPITAL LETTER U}\N{TAG LATIN CAPITAL LETTER S}x\N{LANGUAGE TAG}\N{CANCEL TAG}\N{POP DIRECTIONAL FORMATTING}')),
        (('&lt;&gt;&amp;<img />', 'EN-US', ), '<span dir="ltr" xml:lang="en-US">&lt;&gt;&amp;<img /></span>', to_utf8(u'\N{LEFT-TO-RIGHT EMBEDDING}\N{LANGUAGE TAG}\N{TAG LATIN SMALL LETTER E}\N{TAG LATIN SMALL LETTER N}\N{TAG HYPHEN-MINUS}\N{TAG LATIN CAPITAL LETTER U}\N{TAG LATIN CAPITAL LETTER S}&lt;&gt;&amp;<img />\N{LANGUAGE TAG}\N{CANCEL TAG}\N{POP DIRECTIONAL FORMATTING}')),
        (('a\nb', 'EN-US', ), '<span dir="ltr" xml:lang="en-US">a\nb</span>', to_utf8(u'\N{LEFT-TO-RIGHT EMBEDDING}\N{LANGUAGE TAG}\N{TAG LATIN SMALL LETTER E}\N{TAG LATIN SMALL LETTER N}\N{TAG HYPHEN-MINUS}\N{TAG LATIN CAPITAL LETTER U}\N{TAG LATIN CAPITAL LETTER S}a\N{LANGUAGE TAG}\N{CANCEL TAG}\N{POP DIRECTIONAL FORMATTING}\r\n\N{LEFT-TO-RIGHT EMBEDDING}\N{LANGUAGE TAG}\N{TAG LATIN SMALL LETTER E}\N{TAG LATIN SMALL LETTER N}\N{TAG HYPHEN-MINUS}\N{TAG LATIN CAPITAL LETTER U}\N{TAG LATIN CAPITAL LETTER S}b\N{LANGUAGE TAG}\N{CANCEL TAG}\N{POP DIRECTIONAL FORMATTING}')),
        (('a\nb\n', 'EN-US', ), '<span dir="ltr" xml:lang="en-US">a\nb\n</span>', to_utf8(u'\N{LEFT-TO-RIGHT EMBEDDING}\N{LANGUAGE TAG}\N{TAG LATIN SMALL LETTER E}\N{TAG LATIN SMALL LETTER N}\N{TAG HYPHEN-MINUS}\N{TAG LATIN CAPITAL LETTER U}\N{TAG LATIN CAPITAL LETTER S}a\N{LANGUAGE TAG}\N{CANCEL TAG}\N{POP DIRECTIONAL FORMATTING}\r\n\N{LEFT-TO-RIGHT EMBEDDING}\N{LANGUAGE TAG}\N{TAG LATIN SMALL LETTER E}\N{TAG LATIN SMALL LETTER N}\N{TAG HYPHEN-MINUS}\N{TAG LATIN CAPITAL LETTER U}\N{TAG LATIN CAPITAL LETTER S}b\N{LANGUAGE TAG}\N{CANCEL TAG}\N{POP DIRECTIONAL FORMATTING}\r\n')),
        ((None, None, 'ltr', ), None, None),
        (('', None, 'ltr', ), '', ''),
        (('x', None, 'ltr', ), '<span dir="ltr">x</span>', to_utf8(u'\N{LEFT-TO-RIGHT EMBEDDING}x\N{POP DIRECTIONAL FORMATTING}')),
        (('&lt;&gt;&amp;<img />', None, 'ltr', ), '<span dir="ltr">&lt;&gt;&amp;<img /></span>', to_utf8(u'\N{LEFT-TO-RIGHT EMBEDDING}&lt;&gt;&amp;<img />\N{POP DIRECTIONAL FORMATTING}')),
        (('a\nb', None, 'ltr', ), '<span dir="ltr">a\nb</span>', to_utf8(u'\N{LEFT-TO-RIGHT EMBEDDING}a\N{POP DIRECTIONAL FORMATTING}\r\n\N{LEFT-TO-RIGHT EMBEDDING}b\N{POP DIRECTIONAL FORMATTING}')),
        (('a\nb\n', None, 'ltr', ), '<span dir="ltr">a\nb\n</span>', to_utf8(u'\N{LEFT-TO-RIGHT EMBEDDING}a\N{POP DIRECTIONAL FORMATTING}\r\n\N{LEFT-TO-RIGHT EMBEDDING}b\N{POP DIRECTIONAL FORMATTING}\r\n')),
        ((None, 'EN-US', 'ltr', ), None, None),
        (('', 'EN-US', 'ltr', ), '', ''),
        (('x', 'EN-US', 'ltr', ), '<span dir="ltr" xml:lang="en-US">x</span>', to_utf8(u'\N{LEFT-TO-RIGHT EMBEDDING}\N{LANGUAGE TAG}\N{TAG LATIN SMALL LETTER E}\N{TAG LATIN SMALL LETTER N}\N{TAG HYPHEN-MINUS}\N{TAG LATIN CAPITAL LETTER U}\N{TAG LATIN CAPITAL LETTER S}x\N{LANGUAGE TAG}\N{CANCEL TAG}\N{POP DIRECTIONAL FORMATTING}')),
        (('&lt;&gt;&amp;<img />', 'EN-US', 'ltr', ), '<span dir="ltr" xml:lang="en-US">&lt;&gt;&amp;<img /></span>', to_utf8(u'\N{LEFT-TO-RIGHT EMBEDDING}\N{LANGUAGE TAG}\N{TAG LATIN SMALL LETTER E}\N{TAG LATIN SMALL LETTER N}\N{TAG HYPHEN-MINUS}\N{TAG LATIN CAPITAL LETTER U}\N{TAG LATIN CAPITAL LETTER S}&lt;&gt;&amp;<img />\N{LANGUAGE TAG}\N{CANCEL TAG}\N{POP DIRECTIONAL FORMATTING}')),
        (('a\nb', 'EN-US', 'ltr', ), '<span dir="ltr" xml:lang="en-US">a\nb</span>', to_utf8(u'\N{LEFT-TO-RIGHT EMBEDDING}\N{LANGUAGE TAG}\N{TAG LATIN SMALL LETTER E}\N{TAG LATIN SMALL LETTER N}\N{TAG HYPHEN-MINUS}\N{TAG LATIN CAPITAL LETTER U}\N{TAG LATIN CAPITAL LETTER S}a\N{LANGUAGE TAG}\N{CANCEL TAG}\N{POP DIRECTIONAL FORMATTING}\r\n\N{LEFT-TO-RIGHT EMBEDDING}\N{LANGUAGE TAG}\N{TAG LATIN SMALL LETTER E}\N{TAG LATIN SMALL LETTER N}\N{TAG HYPHEN-MINUS}\N{TAG LATIN CAPITAL LETTER U}\N{TAG LATIN CAPITAL LETTER S}b\N{LANGUAGE TAG}\N{CANCEL TAG}\N{POP DIRECTIONAL FORMATTING}')),
        (('a\nb\n', 'EN-US', 'ltr', ), '<span dir="ltr" xml:lang="en-US">a\nb\n</span>', to_utf8(u'\N{LEFT-TO-RIGHT EMBEDDING}\N{LANGUAGE TAG}\N{TAG LATIN SMALL LETTER E}\N{TAG LATIN SMALL LETTER N}\N{TAG HYPHEN-MINUS}\N{TAG LATIN CAPITAL LETTER U}\N{TAG LATIN CAPITAL LETTER S}a\N{LANGUAGE TAG}\N{CANCEL TAG}\N{POP DIRECTIONAL FORMATTING}\r\n\N{LEFT-TO-RIGHT EMBEDDING}\N{LANGUAGE TAG}\N{TAG LATIN SMALL LETTER E}\N{TAG LATIN SMALL LETTER N}\N{TAG HYPHEN-MINUS}\N{TAG LATIN CAPITAL LETTER U}\N{TAG LATIN CAPITAL LETTER S}b\N{LANGUAGE TAG}\N{CANCEL TAG}\N{POP DIRECTIONAL FORMATTING}\r\n')),
        ((None, None, 'rtl', ), None, None),
        (('', None, 'rtl', ), '', ''),
        (('x', None, 'rtl', ), '<span dir="rtl">x</span>', to_utf8(u'\N{RIGHT-TO-LEFT EMBEDDING}x\N{POP DIRECTIONAL FORMATTING}')),
        (('&lt;&gt;&amp;<img />', None, 'rtl', ), '<span dir="rtl">&lt;&gt;&amp;<img /></span>', to_utf8(u'\N{RIGHT-TO-LEFT EMBEDDING}&lt;&gt;&amp;<img />\N{POP DIRECTIONAL FORMATTING}')),
        (('a\nb', None, 'rtl', ), '<span dir="rtl">a\nb</span>', to_utf8(u'\N{RIGHT-TO-LEFT EMBEDDING}a\N{POP DIRECTIONAL FORMATTING}\r\n\N{RIGHT-TO-LEFT EMBEDDING}b\N{POP DIRECTIONAL FORMATTING}')),
        (('a\nb\n', None, 'rtl', ), '<span dir="rtl">a\nb\n</span>', to_utf8(u'\N{RIGHT-TO-LEFT EMBEDDING}a\N{POP DIRECTIONAL FORMATTING}\r\n\N{RIGHT-TO-LEFT EMBEDDING}b\N{POP DIRECTIONAL FORMATTING}\r\n')),
        ((None, 'EN-US', 'rtl', ), None, None),
        (('', 'EN-US', 'rtl', ), '', ''),
        (('x', 'EN-US', 'rtl', ), '<span dir="rtl" xml:lang="en-US">x</span>', to_utf8(u'\N{RIGHT-TO-LEFT EMBEDDING}\N{LANGUAGE TAG}\N{TAG LATIN SMALL LETTER E}\N{TAG LATIN SMALL LETTER N}\N{TAG HYPHEN-MINUS}\N{TAG LATIN CAPITAL LETTER U}\N{TAG LATIN CAPITAL LETTER S}x\N{LANGUAGE TAG}\N{CANCEL TAG}\N{POP DIRECTIONAL FORMATTING}')),
        (('&lt;&gt;&amp;<img />', 'EN-US', 'rtl', ), '<span dir="rtl" xml:lang="en-US">&lt;&gt;&amp;<img /></span>', to_utf8(u'\N{RIGHT-TO-LEFT EMBEDDING}\N{LANGUAGE TAG}\N{TAG LATIN SMALL LETTER E}\N{TAG LATIN SMALL LETTER N}\N{TAG HYPHEN-MINUS}\N{TAG LATIN CAPITAL LETTER U}\N{TAG LATIN CAPITAL LETTER S}&lt;&gt;&amp;<img />\N{LANGUAGE TAG}\N{CANCEL TAG}\N{POP DIRECTIONAL FORMATTING}')),
        (('a\nb', 'EN-US', 'rtl', ), '<span dir="rtl" xml:lang="en-US">a\nb</span>', to_utf8(u'\N{RIGHT-TO-LEFT EMBEDDING}\N{LANGUAGE TAG}\N{TAG LATIN SMALL LETTER E}\N{TAG LATIN SMALL LETTER N}\N{TAG HYPHEN-MINUS}\N{TAG LATIN CAPITAL LETTER U}\N{TAG LATIN CAPITAL LETTER S}a\N{LANGUAGE TAG}\N{CANCEL TAG}\N{POP DIRECTIONAL FORMATTING}\r\n\N{RIGHT-TO-LEFT EMBEDDING}\N{LANGUAGE TAG}\N{TAG LATIN SMALL LETTER E}\N{TAG LATIN SMALL LETTER N}\N{TAG HYPHEN-MINUS}\N{TAG LATIN CAPITAL LETTER U}\N{TAG LATIN CAPITAL LETTER S}b\N{LANGUAGE TAG}\N{CANCEL TAG}\N{POP DIRECTIONAL FORMATTING}')),
        (('a\nb\n', 'EN-US', 'rtl', ), '<span dir="rtl" xml:lang="en-US">a\nb\n</span>', to_utf8(u'\N{RIGHT-TO-LEFT EMBEDDING}\N{LANGUAGE TAG}\N{TAG LATIN SMALL LETTER E}\N{TAG LATIN SMALL LETTER N}\N{TAG HYPHEN-MINUS}\N{TAG LATIN CAPITAL LETTER U}\N{TAG LATIN CAPITAL LETTER S}a\N{LANGUAGE TAG}\N{CANCEL TAG}\N{POP DIRECTIONAL FORMATTING}\r\n\N{RIGHT-TO-LEFT EMBEDDING}\N{LANGUAGE TAG}\N{TAG LATIN SMALL LETTER E}\N{TAG LATIN SMALL LETTER N}\N{TAG HYPHEN-MINUS}\N{TAG LATIN CAPITAL LETTER U}\N{TAG LATIN CAPITAL LETTER S}b\N{LANGUAGE TAG}\N{CANCEL TAG}\N{POP DIRECTIONAL FORMATTING}\r\n')),
        ):
        assert embed_xhtml(*i) == o_xhtml
        assert embed_text(*i) == o_text
    pass

test()
