#!/usr/bin/env python

import urllib
import unicodedata
import re

from BTL.canonical.unicode import to_utf8

_replace_re = re.compile(ur'(?:^[.])|[\x00-\x1f\x7f-\x9f\"/\\\[\]:;|=,*?]|(?:[.]$)',
re.UNICODE)
_prefix_re = re.compile(ur'^(?:\d|con|aux|(?:com|lpt)[1-4]|prn|nul|(?:rsrc)$|(?:$))',
re.UNICODE | re.IGNORECASE)

def canonical_filename(filename):
    """
    returns a canonicalized copy of filename which should be safe on
    most filesystems; generates a single path segment; the canonical
    filename is returned as a Unicode string; non-Unicode input is
    stringified and decoded as UTF-8

    NOTE: this operation should be idempotent
    """
    if type(filename) is not type(u''):
        filename = str(filename).decode('utf-8')
    filename = unicodedata.normalize('NFC', filename)
    filename = filename.strip()
    filename = _replace_re.sub(u'_', filename)
    if _prefix_re.match(unicodedata.normalize('NFKC', filename)):
        filename = '_' + filename
    if len(filename) > 255:
        filename = filename[:127] + u'\N{horizontal ellipsis}' + filename[-127:]
    return filename

def urlify_filename(filename):
    return urllib.quote(to_utf8(canonical_filename(filename)))

def _test():
    for input, expected_output in (
        (u'coo\N{combining diaeresis}perative', u'co\N{latin small letter o with diaeresis}perative'),
        (u'COM1', u'_COM1'),
        (u'CON', u'_CON'),
        (u'rsrc', u'_rsrc'),
        (u'COM1:', u'_COM1_'),
        (u'lpt3.txt', u'_lpt3.txt'),
        (u'\N{fullwidth latin small letter a}\N{fullwidth latin small letter u}\N{fullwidth latin small letter x}',
         u'_\N{fullwidth latin small letter a}\N{fullwidth latin small letter u}\N{fullwidth latin small letter x}'),
        (u'', u'_'),
        (u'_', u'_'),
        (u'/etc/passwd', u'_etc_passwd'),
        (u'.', u'_'),
        (u'\N{TRADE MARK SIGN}', u'\N{TRADE MARK SIGN}'),
        (u'\t\n\x0b\x0c\r\x1c\x1d\x1e\x1f \x85\xa0\u1680\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a\u200b\u2028\u2029\u202f\u205f\u3000 strip whitespace \t\n\x0b\x0c\r\x1c\x1d\x1e\x1f \x85\xa0\u1680\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a\u200b\u2028\u2029\u202f\u205f\u3000',
         u'strip whitespace'),
        (u''.join([ unichr(x) for x in xrange(0x00, 0x1c) ]),
         u''.join([ '_' for x in xrange(0x00, 0x1c) ])),
        (u''.join([ unichr(x) for x in xrange(0x7f, 0xa0) ]),
         u''.join([ '_' for x in xrange(0x7f, 0xa0) ])),
         ):
        try:
            output = canonical_filename(input)
            assert expected_output == output
            input = input.encode('utf-8')
            output = canonical_filename(input)
            assert expected_output == output
        except:
            import sys
            sys.stderr.write('canonical_filename(%r) should yield %r but yielded %r\n' % (input, expected_output, output))
            raise
    pass

_test()

if __name__ == '__main__':
    import sys
    filenames = sys.argv[1:]
    if not filenames:
        filenames = sys.stdin
    for filename in filenames:
        print canonical_filename(filename).encode('utf-8')
