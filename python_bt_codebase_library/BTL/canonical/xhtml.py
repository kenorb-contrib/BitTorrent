#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
Functions to convert between XHTML fragments and plain text,
canonicalize XHTML fragments and plain text, and verify that XHTML
fragments and plain text are in canonical form.
'''

from BTL.canonical.unicode import to_utf8, to_unicode
from BTL.canonical.user import demoronize, normalize_uri_escapes, valid_uri_re, safe_uri_re, canon_uri
from BTL.canonical.escapes import fix_xmlutf8, xml_escape, uri_escape

import xml.dom.minidom
import re
import urlparse

def canon_xhtml(value):
    '''
    Canonicalizes an XHTML fragment.

    FIXME: This should perform XML canonicalization.

    FIXME: This should preserve explicitly encoded whitespace.
    '''
    if value is not None:
        xdoc = '<?xml version="1.0" encoding="utf-8"?>\n<div xmlns="http://www.w3.org/1999/xhtml">%s</div>' % to_utf8(value)
        dom = xml.dom.minidom.parseString(xdoc)
        dom.normalize()
        value = to_unicode(''.join([ elt.toxml(encoding = 'utf-8') for elt in dom.documentElement.childNodes ]))
    return value

def verify_xhtml(value):
    '''
    Raise an exception if XHTML is not in canonical form.
    '''
    if value != canon_xhtml(value):
        raise ValueError("XHTML is not in canonical form")
    return value

def text_to_xhtml(value):
    '''
    Converts plain text to an XHTML fragment.

    Converts C1 control characters as if they were Windows-1252 or
    MacRoman codepoints rather than ISO-8859-1 codepoints.

    Converts characters not allowed in XHTML to the Unicode replacement character.
    '''
    if value is not None:
        value = to_unicode(xml_escape(demoronize(value)))
    return canon_xhtml(value)

def xhtml_to_text(value):
    '''
    Converts an XHTML fragment to plain text.

    FIXME: This should support special XHTML rules for <br />, <img alt="..." />, etc.
    '''

    def _innerText(node):
        '''
        Returns the concatenated plain text from a DOM node.
        '''
        if node.nodeType in (node.CDATA_SECTION_NODE, node.TEXT_NODE):
            return node.nodeValue
        if node.nodeType in (node.ELEMENT_NODE, node.DOCUMENT_NODE, node.DOCUMENT_FRAGMENT_NODE):
            return u''.join([ _innerText(child) for child in node.childNodes ])

    if value is None:
        return value

    xdoc = '<?xml version="1.0" encoding="utf-8"?>\n<div xmlns="http://www.w3.org/1999/xhtml">%s</div>' % to_utf8(value)
    dom = xml.dom.minidom.parseString(xdoc)
    return _innerText(dom.documentElement)

def canon_text(value):
    '''
    Canonicalizes plain text.
    '''
    return xhtml_to_text(text_to_xhtml(value))

def verify_text(value):
    '''
    Raises an exception if plain text is not in canonical form.
    '''
    if value is not None:
        value = to_unicode(value)
    if value != canon_text(value):
        raise ValueError("plain text is not in canonical form")
    return value

_hyperlink_types = (
    {
    '*': 'Game',
    '#': 'Show',
    '^': 'Album',
    '=': 'DVD',
    '&': 'Music',
    '+': 'Show',
    '@': 'Company',
    '$': 'Name',
    '%': 'Unlisted Name',
    '~': 'Place',
    '!': 'Medium',
    '-': 'Book',
    '/': 'Web',
    '\\': 'Term',
    '|': 'VHS',
    })

hyperlink_re = re.compile(r'[{](?P<Code>[-\\/|*#^=&+@$%~!])(?P<Text>[^{}#]+)[}]')

uri_prefix = 'tag:bittorrent.com,2006-01-01:'

def _hyperlink_type_text_uri(hyperlink_type, text):
    return (
        '''
        %(uri_prefix)s%(hyperlink_type)s/%(text)s
        '''.strip()
        %
        {
        'uri_prefix': uri_prefix,
        'hyperlink_type': hyperlink_type and uri_escape(hyperlink_type) or '',
        'text': uri_escape(text),
        }
        )

def _hyperlink_to_uri(code, text):
    if code == '/':
        uri = text
        if urlparse.urlparse(uri)[0] == '': uri = 'http://' + uri
        uri = normalize_uri_escapes(uri)
        uri = urlparse.urlunparse(urlparse.urlparse(uri))
        # NOTE: this works around a bug in the urlparse cache w.r.t. unicode strings
        uri = ''.join([ chr(ord(ch)) for ch in uri ])
        if safe_uri_re.match(uri) and valid_uri_re.match(uri) and uri == uri.decode('us-ascii', 'replace').encode('us-ascii', 'replace'):
            return canon_uri(uri)
        pass
    hyperlink_type = _hyperlink_types[code]
    return _hyperlink_type_text_uri(hyperlink_type, text)

def _hyperlinks_to_xhtml(dinotext):
    xhtml = []
    offset = 0
    while offset < len(dinotext):
        match = hyperlink_re.search(dinotext[offset:])
        if match:
            xhtml.append(text_to_xhtml(dinotext[offset:][:match.start()]))
            offset += match.start() + len(match.group(0))
            hyperlink_type = _hyperlink_types[match.group('Code')]
            xhtml.append(
                '''
                <a href="%(URI)s">%(Text)s</a>
                '''.strip()
                %
                {
                'URI': xml_escape(_hyperlink_to_uri(match.group('Code'), xhtml_to_text(_re_italicize(text_to_xhtml(match.group('Text')))))),
                'Text': text_to_xhtml(match.group('Text')),
                }
                )
            pass
        else:
            xhtml.append(text_to_xhtml(dinotext[offset:]))
            offset = len(dinotext)
        pass
    return ''.join(xhtml)

_italics_re = re.compile(r'&lt;[iI]&gt;(?P<Text>(?:[^<>"&]|(?:&(?:gt|amp|quot);)+|&lt;[^iI<>"&])*)&lt;/[iI]&gt;')

def _re_italicize(xhtml):
    xhtmlout = []
    offset = 0
    while offset < len(xhtml):
        match = _italics_re.search(xhtml[offset:])
        if match:
            xhtmlout.append(xhtml[offset:][:match.start()])
            offset += match.start() + len(match.group(0))
            xhtmlout.append(
                '''
                <em>%(Text)s</em>
                '''.strip()
                %
                {
                'Text': match.group('Text'),
                }
                )
            pass
        else:
            xhtmlout.append(xhtml[offset:])
            offset = len(xhtml)
        pass
    return ''.join(xhtmlout)

def dinotext_to_xhtml(dinotext):
    '''
    Convert text in dinosaur hypertext format to XHTML with special
    RFC 4151 "tag" URIs for the links; these URIs start with
    BTL.canonical.xhtml.uri_prefix and should be converted to URLs
    before being sent to clients.
    '''
    return canon_xhtml(_re_italicize(_hyperlinks_to_xhtml(dinotext)))

def test():
    '''
    Tiny smoke test to make sure this module works.
    '''
    for i, o in (
        (None, None),
        ('', u''),
        (u'', u''),
        ('Hello, world!', u'Hello, world!'),
        (u'Hello, world!', u'Hello, world!'),
        (u' ', u' '),
        (u'   foo   ', u'   foo   '),
        (u'&lt;', u'&lt;'),
        (u'&gt;', u'&gt;'),
        (u'&amp;', u'&amp;'),
        (u'>', u'&gt;'),
        (u'\"', u'&quot;'),
        (u'\'', u'\''),
        (u' ', u' '),
        (u'&#10;', u'\n'),
        (u'&#13;', u'\r'),
        (u'\t', u'\t'),
        (u'\n', u'\n'),
        (u'\r\n', u'\n'),
        (u'\r', u'\n'),
        (u'&#xa;', u'\n'),
        (u'&#x0a;', u'\n'),
        (u'&#13;', u'\r'),
        (u'&#x0d;', u'\r'),
        (u'line 1\nline 2\nline 3\nline 4',
         u'line 1\nline 2\nline 3\nline 4'),
        (u'line 1\rline 2\rline 3\rline 4',
         u'line 1\nline 2\nline 3\nline 4'),
        (u'line 1\r\nline 2\r\nline 3\r\nline 4',
         u'line 1\nline 2\nline 3\nline 4'),
        (u'line 1\n\rline 2\n\rline 3\n\rline 4',
         u'line 1\n\nline 2\n\nline 3\n\nline 4'),
        (u'line 1\nline 2\r\nline 3\rline 4',
         u'line 1\nline 2\nline 3\nline 4'),
        (u'line 1\nline 2&#13;\nline 3&#13;line 4',
         u'line 1\nline 2\r\nline 3\rline 4'),
        (u'<![CDATA[]]>', u''),
        (u'<![CDATA[Hello, world!]]>',
         u'<![CDATA[Hello, world!]]>'),
        (u'<![CDATA[<\"\'>&;/! \n\r\t]]>',
         u'<![CDATA[<\"\'>&;/! \n\n\t]]>'),
        (u'<![CDATA[<]]>\"\'><![CDATA[&]]>;/! \n\r\t',
         u'<![CDATA[<]]>&quot;\'&gt;<![CDATA[&]]>;/! \n\n\t'),
        (u'\ufffd', u'\ufffd'),
        (u'\x85', u'\x85'),
        (u'\x80', u'\x80'),
        (u'\x7f', u'\x7f'),
        (u'\x9f', u'\x9f'),
        (u'\xa0', u'\xa0'),
        (u'\t\n\r\r ~\xa0\ud7ff\ue000\ufffd\U00010000\U0001fffd\U00020000\U0002fffd\U00030000\U0003fffd\U00040000\U0004fffd\U00050000\U0005fffd\U00060000\U0006fffd\U00070000\U0007fffd\U00080000\U0008fffd\U00090000\U0009fffd\U000a0000\U000afffd\U000b0000\U000bfffd\U000c0000\U000cfffd\U000d0000\U000dfffd\U000e0000\U000efffd\U000f0000\U000ffffd\U00100000\U0010fffd',
         u'\t\n\n\n ~\xa0\ud7ff\ue000\ufffd\U00010000\U0001fffd\U00020000\U0002fffd\U00030000\U0003fffd\U00040000\U0004fffd\U00050000\U0005fffd\U00060000\U0006fffd\U00070000\U0007fffd\U00080000\U0008fffd\U00090000\U0009fffd\U000a0000\U000afffd\U000b0000\U000bfffd\U000c0000\U000cfffd\U000d0000\U000dfffd\U000e0000\U000efffd\U000f0000\U000ffffd\U00100000\U0010fffd'),
        ):
        assert canon_xhtml(i) == o
        if i == o:
            assert verify_xhtml(i) == o
        else:
            try:
                verify_xhtml(i)
                assert "XHTML fragment verification should have failed." [:0]
            except:
                pass
    for i, o in (
        (None, None),
        ('', u''),
        (u'', u''),
        ('Hello, world!', u'Hello, world!'),
        (u'Hello, world!', u'Hello, world!'),
        (u' ', u' '),
        (u'   foo   ', u'   foo   '),
        (u'&lt;', u'&lt;'),
        (u'&gt;', u'&gt;'),
        (u'&amp;', u'&amp;'),
        (u'>', u'>'),
        (u'\"', u'\"'),
        (u'\'', u'\''),
        (u' ', u' '),
        (u'\n', u'\n'),
        (u'\r', u'\n'),
        (u'\t', u'\t'),
        (u'\n', u'\n'),
        (u'\r\n', u'\n'),
        (u'line 1\nline 2\nline 3\nline 4',
         u'line 1\nline 2\nline 3\nline 4'),
        (u'line 1\rline 2\rline 3\rline 4',
         u'line 1\nline 2\nline 3\nline 4'),
        (u'line 1\r\nline 2\r\nline 3\r\nline 4',
         u'line 1\nline 2\nline 3\nline 4'),
        (u'line 1\n\rline 2\n\rline 3\n\rline 4',
         u'line 1\n\nline 2\n\nline 3\n\nline 4'),
        (u'line 1\nline 2\r\nline 3\rline 4',
         u'line 1\nline 2\nline 3\nline 4'),
        (u'<\"\'>&;/! \n\r\t',
         u'<\"\'>&;/! \n\n\t'),
        (u'\ufffd', u'\ufffd'),
        (u'\x85', u'\u2026'),
        (u'\x80', u'\u20ac'),
        (u'\x7f', u'\ufffd'),
        (u'\x9f', u'\u0178'),
        (u'\xa0', u'\xa0'),
        (u'\t\n\r\r ~\xa0\ud7ff\ue000\ufffd\U00010000\U0001fffd\U00020000\U0002fffd\U00030000\U0003fffd\U00040000\U0004fffd\U00050000\U0005fffd\U00060000\U0006fffd\U00070000\U0007fffd\U00080000\U0008fffd\U00090000\U0009fffd\U000a0000\U000afffd\U000b0000\U000bfffd\U000c0000\U000cfffd\U000d0000\U000dfffd\U000e0000\U000efffd\U000f0000\U000ffffd\U00100000\U0010fffd',
         u'\t\n\n\n ~\xa0\ud7ff\ue000\ufffd\U00010000\U0001fffd\U00020000\U0002fffd\U00030000\U0003fffd\U00040000\U0004fffd\U00050000\U0005fffd\U00060000\U0006fffd\U00070000\U0007fffd\U00080000\U0008fffd\U00090000\U0009fffd\U000a0000\U000afffd\U000b0000\U000bfffd\U000c0000\U000cfffd\U000d0000\U000dfffd\U000e0000\U000efffd\U000f0000\U000ffffd\U00100000\U0010fffd'),
        (u'\N{DOLLAR SIGN}\N{POUND SIGN}\N{EURO SIGN}\N{YEN SIGN}',
         u'\N{DOLLAR SIGN}\N{POUND SIGN}\N{EURO SIGN}\N{YEN SIGN}'),
        ('\x00', u'\ufffd'),
        ('\x1f', u'\ufffd'),
        ('\x7f', u'\ufffd'),
        ('\x80', u'\ufffd'),
        ('\x84', u'\ufffd'),
        ('\x86', u'\ufffd'),
        ('\x9f', u'\ufffd'),
        ('\xa0', u'\ufffd'),
        (u'\x80', u'\u20ac'),
        (u'\x84', u'\u201e'),
        (u'\x85', u'\u2026'),
        (u'\x86', u'\u2020'),
        (u'\x8f', u'\xe8'),
        (u'\xa0', u'\xa0'),
        (u'\xa1', u'\xa1'),
        (u'\u3000', u'\u3000'),
        (u'\ud800', u''.join([ u'\ufffd' for x in to_utf8(u'\ud800') ])),
        (u'\udbff', u''.join([ u'\ufffd' for x in to_utf8(u'\udbff') ])),
        (u'\udc00', u''.join([ u'\ufffd' for x in to_utf8(u'\udc00') ])),
        (u'\udfff', u''.join([ u'\ufffd' for x in to_utf8(u'\udfff') ])),
        (u'\uff21', u'\uff21'),
        (u'\ufffd', u'\ufffd'),
        (u'\uffff', u''.join([ u'\ufffd' for x in to_utf8(u'\uffff') ])),
        (u'\U00010000', u'\U00010000'),
        (u'\U0001ffff', u''.join([ u'\ufffd' for x in to_utf8(u'\U0001ffff') ])),
        (u'\U0010fffd', u'\U0010fffd'),
        (u'\U0010ffff', u''.join([ u'\ufffd' for x in to_utf8(u'\U0010ffff') ])),
        ('<\"\'>&;/! \0\a\b\n\r\t\v\f',
         u'<\"\'>&;/! \ufffd\ufffd\ufffd\n\n\t\ufffd\ufffd'),
        (u'\t\n\r\r ~\xa0\ud7ff\ue000\ufffd\U00010000\U0001fffd\U00020000\U0002fffd\U00030000\U0003fffd\U00040000\U0004fffd\U00050000\U0005fffd\U00060000\U0006fffd\U00070000\U0007fffd\U00080000\U0008fffd\U00090000\U0009fffd\U000a0000\U000afffd\U000b0000\U000bfffd\U000c0000\U000cfffd\U000d0000\U000dfffd\U000e0000\U000efffd\U000f0000\U000ffffd\U00100000\U0010fffd',
         u'\t\n\n\n ~\xa0\ud7ff\ue000\ufffd\U00010000\U0001fffd\U00020000\U0002fffd\U00030000\U0003fffd\U00040000\U0004fffd\U00050000\U0005fffd\U00060000\U0006fffd\U00070000\U0007fffd\U00080000\U0008fffd\U00090000\U0009fffd\U000a0000\U000afffd\U000b0000\U000bfffd\U000c0000\U000cfffd\U000d0000\U000dfffd\U000e0000\U000efffd\U000f0000\U000ffffd\U00100000\U0010fffd'),
        (u'\x80\x81\x82\x83\x84\x85\x86\x87\x88\x89\x8a\x8b\x8c\x8d\x8e\x8f\x90\x91\x92\x93\x94\x95\x96\x97\x98\x99\x9a\x9b\x9c\x9d\x9e\x9f',
         u'\u20ac\xc5\u201a\u0192\u201e\u2026\u2020\u2021\u02c6\u2030\u0160\u2039\u0152\xe7\u017d\xe8\xea\u2018\u2019\u201c\u201d\u2022\u2013\u2014\u02dc\u2122\u0161\u203a\u0153\xf9\u017e\u0178'),
        (u'\x00\x01\x02\x03\x04\x05\x06\x07\x08\x0b\x0c\x0e\x0f\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f\x7f\udc00\udfff\ud800\udbff\ufffe\uffff\U0001fffe\U0001ffff\U0002fffe\U0002ffff\U0003fffe\U0003ffff\U0004fffe\U0004ffff\U0005fffe\U0005ffff\U0006fffe\U0006ffff\U0007fffe\U0007ffff\U0008fffe\U0008ffff\U0009fffe\U0009ffff\U000afffe\U000affff\U000bfffe\U000bffff\U000cfffe\U000cffff\U000dfffe\U000dffff\U000efffe\U000effff\U000ffffe\U000fffff\U0010fffe',
         u''.join([ u'\ufffd' for ch in u'\x00\x01\x02\x03\x04\x05\x06\x07\x08\x0b\x0c\x0e\x0f\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f\x7f\udc00\udfff\ud800\udbff\ufffe\uffff\U0001fffe\U0001ffff\U0002fffe\U0002ffff\U0003fffe\U0003ffff\U0004fffe\U0004ffff\U0005fffe\U0005ffff\U0006fffe\U0006ffff\U0007fffe\U0007ffff\U0008fffe\U0008ffff\U0009fffe\U0009ffff\U000afffe\U000affff\U000bfffe\U000bffff\U000cfffe\U000cffff\U000dfffe\U000dffff\U000efffe\U000effff\U000ffffe\U000fffff\U0010fffe'.encode('utf-8') ])),
        ):
        assert canon_text(i) == o
        if to_utf8(i) == to_utf8(o):
            assert verify_text(i) == o
        else:
            try:
                verify_text(i)
                assert "plain text verification should have failed." [:0]
            except:
                pass
    for i, o in (
        ('', ''),
        ('Hello, world!', 'Hello, world!'),
        (u'Hello, world!', 'Hello, world!'),
        (u'\N{DOLLAR SIGN}\N{POUND SIGN}\N{EURO SIGN}\N{YEN SIGN}',
         u'\N{DOLLAR SIGN}\N{POUND SIGN}\N{EURO SIGN}\N{YEN SIGN}'),
        ('<', '&lt;'),
        ('>', '&gt;'),
        ('&', '&amp;'),
        ('\"', '&quot;'),
        ('\'', '\''),
        (' ', ' '),
        ('\n', '\n'),
        ('\r', '\r'),
        ('\t', '\t'),
        ('\x00', u'\ufffd'),
        ('\x1f', u'\ufffd'),
        ('\x7f', u'\ufffd'),
        ('\x80', u'\ufffd'),
        ('\x84', u'\ufffd'),
        ('\x86', u'\ufffd'),
        ('\x9f', u'\ufffd'),
        ('\xa0', u'\ufffd'),
        (u'\x80\x81\x82\x83\x84\x85\x86\x87\x88\x89\x8a\x8b\x8c\x8d\x8e\x8f\x90\x91\x92\x93\x94\x95\x96\x97\x98\x99\x9a\x9b\x9c\x9d\x9e\x9f',
         u'\u20ac\xc5\u201a\u0192\u201e\u2026\u2020\u2021\u02c6\u2030\u0160\u2039\u0152\xe7\u017d\xe8\xea\u2018\u2019\u201c\u201d\u2022\u2013\u2014\u02dc\u2122\u0161\u203a\u0153\xf9\u017e\u0178'),
        (u'\xa0', u'\xa0'),
        (u'\xa1', u'\xa1'),
        (u'\u3000', u'\u3000'),
        (u'\ud800', u''.join([ u'\ufffd' for x in to_utf8(u'\ud800') ])),
        (u'\udbff', u''.join([ u'\ufffd' for x in to_utf8(u'\udbff') ])),
        (u'\udc00', u''.join([ u'\ufffd' for x in to_utf8(u'\udc00') ])),
        (u'\udfff', u''.join([ u'\ufffd' for x in to_utf8(u'\udfff') ])),
        (u'\uff21', u'\uff21'),
        (u'\ufffd', u'\ufffd'),
        (u'\uffff', u''.join([ u'\ufffd' for x in to_utf8(u'\uffff') ])),
        (u'\U00010000', u'\U00010000'),
        (u'\U0001ffff', u''.join([ u'\ufffd' for x in to_utf8(u'\U0001ffff') ])),
        (u'\U0010fffd', u'\U0010fffd'),
        (u'\U0010ffff', u''.join([ u'\ufffd' for x in to_utf8(u'\U0010ffff') ])),
        ('<\"\'>&;/! \0\a\b\n\r\t\v\f',
         u'&lt;&quot;\'&gt;&amp;;/! \ufffd\ufffd\ufffd\n\r\t\ufffd\ufffd'),
        (u'\t\n\r\r ~\xa0\ud7ff\ue000\ufffd\U00010000\U0001fffd\U00020000\U0002fffd\U00030000\U0003fffd\U00040000\U0004fffd\U00050000\U0005fffd\U00060000\U0006fffd\U00070000\U0007fffd\U00080000\U0008fffd\U00090000\U0009fffd\U000a0000\U000afffd\U000b0000\U000bfffd\U000c0000\U000cfffd\U000d0000\U000dfffd\U000e0000\U000efffd\U000f0000\U000ffffd\U00100000\U0010fffd',
         u'\t\n\r\r ~\xa0\ud7ff\ue000\ufffd\U00010000\U0001fffd\U00020000\U0002fffd\U00030000\U0003fffd\U00040000\U0004fffd\U00050000\U0005fffd\U00060000\U0006fffd\U00070000\U0007fffd\U00080000\U0008fffd\U00090000\U0009fffd\U000a0000\U000afffd\U000b0000\U000bfffd\U000c0000\U000cfffd\U000d0000\U000dfffd\U000e0000\U000efffd\U000f0000\U000ffffd\U00100000\U0010fffd'),
        (u'\x00\x01\x02\x03\x04\x05\x06\x07\x08\x0b\x0c\x0e\x0f\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f\x7f\udc00\udfff\ud800\udbff\ufffe\uffff\U0001fffe\U0001ffff\U0002fffe\U0002ffff\U0003fffe\U0003ffff\U0004fffe\U0004ffff\U0005fffe\U0005ffff\U0006fffe\U0006ffff\U0007fffe\U0007ffff\U0008fffe\U0008ffff\U0009fffe\U0009ffff\U000afffe\U000affff\U000bfffe\U000bffff\U000cfffe\U000cffff\U000dfffe\U000dffff\U000efffe\U000effff\U000ffffe\U000fffff\U0010fffe',
         u''.join([ u'\ufffd' for ch in u'\x00\x01\x02\x03\x04\x05\x06\x07\x08\x0b\x0c\x0e\x0f\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f\x7f\udc00\udfff\ud800\udbff\ufffe\uffff\U0001fffe\U0001ffff\U0002fffe\U0002ffff\U0003fffe\U0003ffff\U0004fffe\U0004ffff\U0005fffe\U0005ffff\U0006fffe\U0006ffff\U0007fffe\U0007ffff\U0008fffe\U0008ffff\U0009fffe\U0009ffff\U000afffe\U000affff\U000bfffe\U000bffff\U000cfffe\U000cffff\U000dfffe\U000dffff\U000efffe\U000effff\U000ffffe\U000fffff\U0010fffe'.encode('utf-8') ])),
        ):
        assert text_to_xhtml(i) == o
        assert xhtml_to_text(o) == canon_text(i)
    for i, o in (
        ('', ''),
        ('Hello, world!', 'Hello, world!'),
        (u'Hello, world!', 'Hello, world!'),
        (u'\N{DOLLAR SIGN}\N{POUND SIGN}\N{EURO SIGN}\N{YEN SIGN}',
         u'\N{DOLLAR SIGN}\N{POUND SIGN}\N{EURO SIGN}\N{YEN SIGN}'),
        ('<', '&lt;'),
        ('>', '&gt;'),
        ('&', '&amp;'),
        ('\"', '&quot;'),
        ('\'', '\''),
        (' ', ' '),
        ('\n', '\n'),
        ('\r', '\n'),
        ('\t', '\t'),
        ('\x00', u'\ufffd'),
        ('\x1f', u'\ufffd'),
        ('\x7f', u'\ufffd'),
        ('\x80', u'\ufffd'),
        ('\x84', u'\ufffd'),
        ('\x86', u'\ufffd'),
        ('\x9f', u'\ufffd'),
        ('\xa0', u'\ufffd'),
        (u'\x80\x81\x82\x83\x84\x85\x86\x87\x88\x89\x8a\x8b\x8c\x8d\x8e\x8f\x90\x91\x92\x93\x94\x95\x96\x97\x98\x99\x9a\x9b\x9c\x9d\x9e\x9f',
         u'\u20ac\xc5\u201a\u0192\u201e\u2026\u2020\u2021\u02c6\u2030\u0160\u2039\u0152\xe7\u017d\xe8\xea\u2018\u2019\u201c\u201d\u2022\u2013\u2014\u02dc\u2122\u0161\u203a\u0153\xf9\u017e\u0178'),
        (u'\xa0', u'\xa0'),
        (u'\xa1', u'\xa1'),
        (u'\u3000', u'\u3000'),
        (u'\ud800', u''.join([ u'\ufffd' for x in to_utf8(u'\ud800') ])),
        (u'\udbff', u''.join([ u'\ufffd' for x in to_utf8(u'\udbff') ])),
        (u'\udc00', u''.join([ u'\ufffd' for x in to_utf8(u'\udc00') ])),
        (u'\udfff', u''.join([ u'\ufffd' for x in to_utf8(u'\udfff') ])),
        (u'\uff21', u'\uff21'),
        (u'\ufffd', u'\ufffd'),
        (u'\uffff', u''.join([ u'\ufffd' for x in to_utf8(u'\uffff') ])),
        (u'\U00010000', u'\U00010000'),
        (u'\U0001ffff', u''.join([ u'\ufffd' for x in to_utf8(u'\U0001ffff') ])),
        (u'\U0010fffd', u'\U0010fffd'),
        (u'\U0010ffff', u''.join([ u'\ufffd' for x in to_utf8(u'\U0010ffff') ])),
        ('<\"\'>&;/! \0\a\b\n\r\t\v\f',
         u'&lt;&quot;\'&gt;&amp;;/! \ufffd\ufffd\ufffd\n\n\t\ufffd\ufffd'),
        (u'\t\n\r\r ~\xa0\ud7ff\ue000\ufffd\U00010000\U0001fffd\U00020000\U0002fffd\U00030000\U0003fffd\U00040000\U0004fffd\U00050000\U0005fffd\U00060000\U0006fffd\U00070000\U0007fffd\U00080000\U0008fffd\U00090000\U0009fffd\U000a0000\U000afffd\U000b0000\U000bfffd\U000c0000\U000cfffd\U000d0000\U000dfffd\U000e0000\U000efffd\U000f0000\U000ffffd\U00100000\U0010fffd',
         u'\t\n\n\n ~\xa0\ud7ff\ue000\ufffd\U00010000\U0001fffd\U00020000\U0002fffd\U00030000\U0003fffd\U00040000\U0004fffd\U00050000\U0005fffd\U00060000\U0006fffd\U00070000\U0007fffd\U00080000\U0008fffd\U00090000\U0009fffd\U000a0000\U000afffd\U000b0000\U000bfffd\U000c0000\U000cfffd\U000d0000\U000dfffd\U000e0000\U000efffd\U000f0000\U000ffffd\U00100000\U0010fffd'),
        (u'\x00\x01\x02\x03\x04\x05\x06\x07\x08\x0b\x0c\x0e\x0f\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f\x7f\udc00\udfff\ud800\udbff\ufffe\uffff\U0001fffe\U0001ffff\U0002fffe\U0002ffff\U0003fffe\U0003ffff\U0004fffe\U0004ffff\U0005fffe\U0005ffff\U0006fffe\U0006ffff\U0007fffe\U0007ffff\U0008fffe\U0008ffff\U0009fffe\U0009ffff\U000afffe\U000affff\U000bfffe\U000bffff\U000cfffe\U000cffff\U000dfffe\U000dffff\U000efffe\U000effff\U000ffffe\U000fffff\U0010fffe',
         u''.join([ u'\ufffd' for ch in u'\x00\x01\x02\x03\x04\x05\x06\x07\x08\x0b\x0c\x0e\x0f\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f\x7f\udc00\udfff\ud800\udbff\ufffe\uffff\U0001fffe\U0001ffff\U0002fffe\U0002ffff\U0003fffe\U0003ffff\U0004fffe\U0004ffff\U0005fffe\U0005ffff\U0006fffe\U0006ffff\U0007fffe\U0007ffff\U0008fffe\U0008ffff\U0009fffe\U0009ffff\U000afffe\U000affff\U000bfffe\U000bffff\U000cfffe\U000cffff\U000dfffe\U000dffff\U000efffe\U000effff\U000ffffe\U000fffff\U0010fffe'.encode('utf-8') ])),
        (u'<i>Italics</i> are permitted.',
         u'<em>Italics</em> are permitted.'),
        (u'<em>Emphasis</em> is not permitted.',
         u'&lt;em&gt;Emphasis&lt;/em&gt; is not permitted.'),
        (u'A bare set of curly braces works: {}',
         u'A bare set of curly braces works: {}'),
        (u'A bare set of curly braces with garbage inside works: {garbage}',
         u'A bare set of curly braces with garbage inside works: {garbage}'),
        (u'The game of {*Chess} is ancient and has many variations',
         u'The game of <a href="tag:bittorrent.com,2006-01-01:Game/Chess">Chess</a> is ancient and has many variations'),
        (u'The show {#Monkeyspit} does not exist, AFAIK.',
         u'The show <a href="tag:bittorrent.com,2006-01-01:Show/Monkeyspit">Monkeyspit</a> does not exist, AFAIK.'),
        (u'{//}',
         u'<a href="http:///">/</a>'),
        (u'{/www.bittorrent.com}',
         u'<a href="http://www.bittorrent.com">www.bittorrent.com</a>'),
        (u'{/http://www.bittorrent.com}',
         u'<a href="http://www.bittorrent.com">http://www.bittorrent.com</a>'),
        (u'{/https://www.bittorrent.com}',
         u'<a href="https://www.bittorrent.com">https://www.bittorrent.com</a>'),
        (u'{/ftp://ftp.ubuntu.com}',
         u'<a href="ftp://ftp.ubuntu.com">ftp://ftp.ubuntu.com</a>'),
        (u'{/<i>italics</i>}',
         u'<a href="http://italics"><em>italics</em></a>'),
        (u'<i>{/italics</i>}',
         u'&lt;i&gt;<a href="http://italics%3C/i%3E">italics&lt;/i&gt;</a>'),
        (u'<i>{/italics}</i>',
         u'&lt;i&gt;<a href="http://italics">italics</a>&lt;/i&gt;'),
        (u'The show <i>{#Monkeyspit}</i> does not exist, AFAIK.',
         u'The show &lt;i&gt;<a href="tag:bittorrent.com,2006-01-01:Show/Monkeyspit">Monkeyspit</a>&lt;/i&gt; does not exist, AFAIK.'),
        (u'The show {#<i>Monkeyspit</i>} does not exist, AFAIK.',
         u'The show <a href="tag:bittorrent.com,2006-01-01:Show/Monkeyspit"><em>Monkeyspit</em></a> does not exist, AFAIK.'),
        (u'<i>i</i>{* }{# }{^ }{= }{& }{+ }{@ }{$ }{% }{~ }{! }{- }{/ }{\\ }{| }',
         u'<em>i</em><a href="tag:bittorrent.com,2006-01-01:Game/%20"> </a><a href="tag:bittorrent.com,2006-01-01:Show/%20"> </a><a href="tag:bittorrent.com,2006-01-01:Album/%20"> </a><a href="tag:bittorrent.com,2006-01-01:DVD/%20"> </a><a href="tag:bittorrent.com,2006-01-01:Music/%20"> </a><a href="tag:bittorrent.com,2006-01-01:Show/%20"> </a><a href="tag:bittorrent.com,2006-01-01:Company/%20"> </a><a href="tag:bittorrent.com,2006-01-01:Name/%20"> </a><a href="tag:bittorrent.com,2006-01-01:Unlisted%20Name/%20"> </a><a href="tag:bittorrent.com,2006-01-01:Place/%20"> </a><a href="tag:bittorrent.com,2006-01-01:Medium/%20"> </a><a href="tag:bittorrent.com,2006-01-01:Book/%20"> </a><a href="http://%20"> </a><a href="tag:bittorrent.com,2006-01-01:Term/%20"> </a><a href="tag:bittorrent.com,2006-01-01:VHS/%20"> </a>'),
        ):
        assert dinotext_to_xhtml(i) == o
    pass

test()
