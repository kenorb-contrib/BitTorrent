#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This attempts to implement RFC 4013,
# a.k.a. SASLprep: Stringprep Profile for User Names and Passwords

import stringprep
import unicodedata
from BTL.canonical.unicode import unichars, unichr, uniord

def saslprep(s, allow_unassigned = False):
    '''
    Prepare Unicode string s according to SASLprep: Stringprep Profile for
    User Names and Passwords, a.k.a. RFC 4013

    If the optional parameter allow_unassigned is set to True,
    unassigned codepoints will be allowed. This is recommended for
    query terms and other non-storing situations only.

    The return value is a Unicode string appropriately prepared.

    Disallowed input leads to a ValueError.
    '''
    if type(s) != type(u''):
        raise TypeError("input must be a Unicode string")
    # phase 1: mapping
    s = u''.join([ stringprep.in_table_c12(ch) and u' ' or ch for ch in unichars(s) if not stringprep.in_table_b1(ch) ])
    # phase 2: normalization
    s = unicodedata.normalize('NFKC', s)
    # phase 3: prohibition
    for ch in unichars(s):
        if stringprep.in_table_c12(ch):
            raise ValueError("prohibited non-ASCII space character")
        if stringprep.in_table_c21(ch):
            raise ValueError("prohibited ASCII control character")
        if stringprep.in_table_c22(ch):
            raise ValueError("prohibited non-ASCII control character")
        if stringprep.in_table_c3(ch):
            raise ValueError("prohibited private use character")
        if stringprep.in_table_c4(ch):
            raise ValueError("prohibited non-character code point")
        if stringprep.in_table_c5(ch):
            raise ValueError("prohibited surrogate code point")
        if stringprep.in_table_c6(ch):
            raise ValueError("prohibited character inappropriate for plain text")
        if stringprep.in_table_c7(ch):
            raise ValueError("prohibited character inappropriate for canonical representation")
        if stringprep.in_table_c8(ch):
            raise ValueError("prohibited character changing display properties, or a deprecated character")
        if stringprep.in_table_c9(ch):
            raise ValueError("prohibited tagging character")
    # phase 4: bidi check
    bidi_map = ''.join([ stringprep.in_table_d1(ch) and 'r' or stringprep.in_table_d2(ch) and 'l' or 'x' for ch in unichars(s) ])
    if 'r' in bidi_map:
        if 'l' in bidi_map:
            raise ValueError("prohibited mixture of strong left-to-right and right-to-left text")
        if bidi_map[0] != 'r' or bidi_map[-1] != 'r':
            raise ValueError("string containing right-to-left text must start and end with right-to-left text")
    # phase 5: unassigned check
    if not allow_unassigned:
        for ch in unichars(s):
            if stringprep.in_table_a1(ch):
                raise ValueError("prohibited unassigned code point")
    return s

def test():
    for s, os in (
        (u'I\u00adX', u'IX'),
        (u'user', u'user'),
        (u'USER', u'USER'),
        (u'\u00aa', u'a'),
        (u'\u2168', u'IX'),
        ):
        assert 'saslprep(%r) == %r' % (s, os) and saslprep(s) == os
    for s in (
        u'\u0007',
        u'\u0627\u0031',
        ):
        try:
            saslprep(s)
            assert 'saslprep(%r) should have failed' % s and False
        except:
            continue
    pass

test()

def main():
    import sys
    import getopt
    allow_unassigned = False
    opts, args = getopt.getopt(sys.argv[1:], 'u', ['allow-unassigned'])
    assert len(args) == 0
    for opt in opts:
        if opt in ('-u', '--allow-unassigned'):
            allow_unassigned = True
    for line in sys.stdin.readlines():
        try:
            line = line.decode('utf-8')
            line = line.rstrip(u'\n')
            print saslprep(line, allow_unassigned = allow_unassigned).encode('utf-8')
        except:
            import traceback
            sys.stderr.write(traceback.format_exc())
            sys.stderr.flush()

if __name__ == '__main__':
    main()
