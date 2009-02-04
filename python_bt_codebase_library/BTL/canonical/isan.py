#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
This is a Python module for handling International Standard
Audiovisual Numbers (ISANs) and includes check character verification
(through a generic implementation of ISO 7064 MOD a,b), structural
verification (has to look like an ISAN) and a few other checks
(verifies that non-public versions are not used in public contexts).
'''

import re
import sys
import string

def checkMOD(a, b, digits):
    '''
    Return the ISO 7064 MOD a,b check digit integer for the given
    integer sequence ("digits").
    '''
    isum = b
    for digit in digits: isum = (2 * (((isum + digit) % b) or b)) % a
    return (a - isum) % b

class ISAN(object):
    '''

    International Standard Audiovisual Number (ISAN)
    ISO 15706
    http://www.isan.org/

    Examples of invalid ISANs (all have incorrect check characters):

     ISAN 0000-0000-3ABD-0000-Z
     ISAN 006A-15FA-002B-C95F-A
     ISAN 1881-66C7-3420-0000-7
     ISAN 0000-1234-1234-1234-X-0000-0000-Y
     ISAN 1881-66C7-3420-0000-7-9F3A-0245-U

    Examples of valid ISANs:

     ISAN B159-D8FA-0124-0000-K
     ISAN 0000-3BAB-9352-0000-G
     ISAN 1881-66C7-3420-0000-3
     ISAN 0000-3BAB-9352-0000-G-0000-0000-Q
          |____________| |__|   |_______|
                R         E         V
                O         P         E
                O         I         R
                T         S         S
                          O         I
                          D         O
                          E         N

    Structure: 16 hex digits (root + episode) with an alphanumeric check
    character; optionally followed by 8 upper-case hex digits (version)
    followed by an alphanumeric check character.

    The check characters are calculated according to ISO 7064 MOD
    37,36. The first check character takes the root and episode as its
    input; the second takes the root, episode and version (and is only
    present in ISANs with versions).

    Episode: 0000 for non-serial works, never 0000 for serial works.

    Version: Fxxx-xxxx (initial nybble high) is reserved for internal
    versions; invalid outside of the version registrant\'s system. A
    version of 0000-0000 shall not be assigned when no version exists.
    '''
    # FIXME: we permit lower case and an optional colon after the
    # initial ISAN, even though this is non-standard; the result
    # returned by str() will be in canonical form however.
    isan_re = re.compile(
        r'''
        \A
        (?:
        (?# Canonical form )
        (?:ISAN:?[ ])?
        (?P<isan>(?P<root>[0-9A-F]{4,4}[- ][0-9A-F]{4,4}[- ][0-9A-F]{4,4})[- ](?P<episode>[0-9A-F]{4,4}))
        [- ]?
        (?P<isancheck>[0-9A-Z])
        (?:
        [- ]?
        (?P<version>[0-9A-F]{4,4}[- ][0-9A-F]{4,4})
        [- ]?
        (?P<versioncheck>[0-9A-Z])
        )?
        |
        (?# Short form )
        (?P<shortisan>(?P<shortroot>[0-9A-F]{12,12})(?P<shortepisode>[0-9A-F]{4,4}))
        (?P<shortisancheck>[0-9A-Z])
        (?:
        (?P<shortversion>[0-9A-F]{8,8})
        (?P<shortversioncheck>[0-9A-Z])
        )?
        )
        \Z
        ''',
        re.VERBOSE | re.IGNORECASE | re.UNICODE)
    isan_alphabet = string.digits + string.uppercase
    def __init__(self, s, public = True, autocorrect = False):
        '''
        Initialize an ISAN from a string ("s"); set the optional flag
        public = False if this ISAN is being used in an internal
        context where private versions are allowed. Set the optional
        flag autocorrect = True to replace the supplied check
        character(s) with the correct one(s) rather than raising an
        exception when the check character is not valid.

        Canonical forms (input and output without short = True); ISAN
        prefix is optional on input:

        ISAN xxxx-xxxx-xxxx-xxxx-y
        ISAN xxxx-xxxx-xxxx-xxxx-y-xxxx-xxxx-y

        Short forms (input and output with short = True):
        xxxxxxxxxxxxxxxxy
        xxxxxxxxxxxxxxxxyxxxxxxxxy

        Where x is a hexadecimal digit and y is an alphanumeric check
        character. Case is ignored on input, and spaces may be used
        instead of hyphens. A colon may optionally appear after the
        initial ISAN. On output (using str()) all letters are upper
        case.
        '''
        self.public = public
        match = self.isan_re.match(str(s))
        if not match: raise ValueError('invalid literal for %s.%s(): %r' % (ISAN.__module__, ISAN.__name__, s))
        def canonpart(s):
            o = []
            s = ''.join(''.join(s.upper().split('-')).split(' '))
            while s:
                o.append(s[:4])
                s = s[4:]
                pass
            return '-'.join(o) or None
        for part in ('isan', 'isancheck', 'root', 'episode', 'version', 'versioncheck'):
            setattr(self, part, canonpart(match.group(part) or match.group('short' + part) or ''))
            pass
        self.check(autocorrect = autocorrect)
        return
    def __cmp__(self, isan):
        '''
        Compare this ISAN with another object, returning -1 if the
        other is greater than this one, 0 if the other is equal to
        this one, or 1 if the other is less than this one.
        '''
        if not isinstance(isan, ISAN):
            raise TypeError('%s.%s.__cmp__(self, isan) requires isan to be a %s.%s, not a %s.%s' % (ISAN.__module__, ISAN.__name__, ISAN.__module__, ISAN.__name__, type(isan).__module__, type(isan).__name__))
        return cmp(str(self), str(isan))
    def check(self, autocorrect = False):
        '''
        Verify the ISAN check character and (if present) the version
        check character. If they do not match, this raises a
        ValueError. The optional parameter autocorrect = True instead
        silently fixes the check characters.

        Also verifies that a non-public ISAN is not used in a public context.
        '''
        digits = ''.join(self.isan.split('-'))
        checkdigit = checkMOD(37, 36, [ int(ch, 16) for ch in digits ])
        if autocorrect: self.isancheck = self.isan_alphabet[checkdigit]
        if int(self.isancheck, 36) != checkdigit:
            raise ValueError('invalid check character for %s: %s' % (self, self.isancheck))
        if self.version is not None:
            digits += ''.join(self.version.split('-'))
            versioncheckdigit = checkMOD(37, 36, [ int(ch, 16) for ch in digits ])
            if autocorrect: self.versioncheck = self.isan_alphabet[versioncheckdigit]
            if int(self.versioncheck, 36) != versioncheckdigit:
                raise ValueError('invalid version check character for %s: %s' % (self, self.versioncheck))
            if (int(self.version[0], 16) == 0xF) and self.public:
                raise ValueError('non-public version in a public context for %s: %s' % (self, self.version))
            pass
        pass
    def __repr__(self): return '%s.%s(%r%s)' % (self.__class__.__module__, self.__class__.__name__, str(self), (not self.public) and ', public = False' or '')
    def __str__(self, short = False):
        '''
        Stringify an ISAN; with the optional flag short = True, omit the ISAN prefix and hyphens.
        '''
        o = []
        if not short: o.append('ISAN ')
        o.append(self.isan)
        o.append('-')
        o.append(self.isancheck)
        if self.version is not None:
            o.append('-')
            o.append(self.version)
            o.append('-')
            o.append(self.versioncheck)
            pass
        o = ''.join(o)
        if short: o = ''.join(o.split('-'))
        return o
    pass

def test():
    '''
    Self-tests for the ISAN module
    '''
    # test the MOD a,b check digit calculator (positive tests)
    for a, b, digits, ck in (
        (11, 10, '0', 2),
        (11, 10, '1', 9),
        (11, 10, '6', 0),
        (11, 10, '9', 4),
        (11, 10, '0823', 5),
        (11, 10, '276616973212561', 5),
        (37, 36, 'B159-D8FA-0124-0000- ', int('K', 36)),
        (37, 36, '0000-3BAB-9352-0000- ', int('G', 36)),
        (37, 36, '0000-3BAB-9352-0000- -0000-0000- ', int('Q', 36)),
        (37, 36, '1881-66C7-3420-0000- ', int('3', 36)),
        ):
        try: assert checkMOD(a, b, [ int(digit, 36) for digit in ''.join(''.join(digits.split()).split('-')) ]) == ck
        except:
            print 'checkMOD failed for:'
            print ' a =', a
            print ' b =', b
            print ' digits =', digits
            print ' ck =', ck
            raise
        pass
    # test the MOD a,b check digit calculator (negative tests)
    for a, b, digits, ck in (
        (11, 10, '0', 1),
        (11, 10, '1', 1),
        (11, 10, '6', 1),
        (11, 10, '9', 1),
        (11, 10, '0823', 1),
        (11, 10, '276616973212561', 1),
        (37, 36, '0000-0000-3ABD-0000- ', int('Z', 36)),
        (37, 36, '006A-15FA-002B-C95F- ', int('A', 36)),
        (37, 36, '1881-66C7-3420-0000- ', int('7', 36)),
        (37, 36, '0000-1234-1234-1234- -0000-0000- ', int('Y', 36)),
        (37, 36, '1881-66C7-3420-0000- -9F3A-0245- ', int('U', 36)),
        ):
        try: assert checkMOD(a, b, [ int(digit, 36) for digit in ''.join(''.join(digits.split()).split('-')) ]) != ck
        except:
            print 'checkMOD failed for:'
            print ' a =', a
            print ' b =', b
            print ' digits =', digits
            print ' ck =', ck
            raise
        pass
    # test the ISAN constructor (positive tests)
    for s in (
        'ISAN B159-D8FA-0124-0000-K',
        'ISAN 0000-3BAB-9352-0000-G',
        'ISAN 1881-66C7-3420-0000-3',
        'ISAN 0000-3BAB-9352-0000-G-0000-0000-Q',
        'ISAN 1881-66C7-3420-0000-3-9F3A-0245-Q',
        'ISAN 1234-5678-90AB-CDEF-J',
        'ISAN 0123-4567-89AB-CDEF-5-0123-4567-9',
        'ISAN: B159-D8FA-0124-0000-K',
        'ISAN: 0000-3BAB-9352-0000-G',
        'ISAN: 1881-66C7-3420-0000-3',
        'ISAN: 0000-3BAB-9352-0000-G-0000-0000-Q',
        'ISAN: 1881-66C7-3420-0000-3-9F3A-0245-Q',
        'ISAN: 1234-5678-90AB-CDEF-J',
        'ISAN: 0123-4567-89AB-CDEF-5-0123-4567-9',
        'B159D8FA01240000K',
        '00003BAB93520000G',
        '188166C7342000003',
        '00003BAB93520000G00000000Q',
        '188166C73420000039F3A0245Q',
        '1234567890ABCDEFJ',
        '0123456789ABCDEF5012345679',
        'isan b159-d8fa-0124-0000-k',
        'isan 0000-3bab-9352-0000-g',
        'isan 1881-66c7-3420-0000-3',
        'isan 0000-3bab-9352-0000-g-0000-0000-q',
        'isan 1881-66c7-3420-0000-3-9f3a-0245-q',
        'isan 1234-5678-90ab-cdef-j',
        'isan 0123-4567-89ab-cdef-5-0123-4567-9',
        'isan: b159-d8fa-0124-0000-k',
        'isan: 0000-3bab-9352-0000-g',
        'isan: 1881-66c7-3420-0000-3',
        'isan: 0000-3bab-9352-0000-g-0000-0000-q',
        'isan: 1881-66c7-3420-0000-3-9f3a-0245-q',
        'isan: 1234-5678-90ab-cdef-j',
        'isan: 0123-4567-89ab-cdef-5-0123-4567-9',
        'b159d8fa01240000k',
        '00003bab93520000g',
        '188166c7342000003',
        '00003bab93520000g00000000q',
        '188166c73420000039f3a0245q',
        '1234567890abcdefj',
        '0123456789abcdef5012345679',
        ):
        try: ISAN(s)
        except:
            print 'ISAN failed for s =', s
            raise
        pass
    # test the ISAN constructor (negative tests)
    for s in (
        'ISAN 0000-0000-3ABD-0000-Z',
        'ISAN 006A-15FA-002B-C95F-A',
        'ISAN 1881-66C7-3420-0000-7',
        'ISAN 0000-1234-1234-1234-X-0000-0000-Y',
        'ISAN 1881-66C7-3420-0000-7-9F3A-0245-U',
        'ISAN 1881-66C7-3420-0000-3-FF3A-0245-N',
        'ISAN: 0000-0000-3ABD-0000-Z',
        'ISAN: 006A-15FA-002B-C95F-A',
        'ISAN: 1881-66C7-3420-0000-7',
        'ISAN: 0000-1234-1234-1234-X-0000-0000-Y',
        'ISAN: 1881-66C7-3420-0000-7-9F3A-0245-U',
        'ISAN: 1881-66C7-3420-0000-3-FF3A-0245-N',
        '000000003ABD0000Z',
        '006A15FA002BC95FA',
        '188166C7342000007',
        '0000123412341234X00000000Y',
        '188166C73420000079F3A0245U',
        '188166C7342000003FF3A0245N',
        'isan 0000-0000-3abd-0000-z',
        'isan 006a-15fa-002b-c95f-a',
        'isan 1881-66c7-3420-0000-7',
        'isan 0000-1234-1234-1234-x-0000-0000-y',
        'isan 1881-66c7-3420-0000-7-9f3a-0245-u',
        'isan 1881-66c7-3420-0000-3-ff3a-0245-n',
        'isan: 0000-0000-3abd-0000-z',
        'isan: 006a-15fa-002b-c95f-a',
        'isan: 1881-66c7-3420-0000-7',
        'isan: 0000-1234-1234-1234-x-0000-0000-y',
        'isan: 1881-66c7-3420-0000-7-9f3a-0245-u',
        'isan: 1881-66c7-3420-0000-3-ff3a-0245-n',
        '000000003abd0000z',
        '006a15fa002bc95fa',
        '188166c7342000007',
        '0000123412341234x00000000y',
        '188166c73420000079f3a0245u',
        '188166c7342000003ff3a0245n',
        ):
        try: ISAN(s)
        except ValueError, v: pass
        else:
            print 'ISAN should have failed for s =', s
            assert False
            pass
        pass
    # test the ISAN constructor and the ISAN str() implementation
    assert str(ISAN('ISAN 0000-0000-3ABD-0000-S')) == 'ISAN 0000-0000-3ABD-0000-S'
    assert ISAN('ISAN 0000-0000-3ABD-0000-S').__str__(short = True) == '000000003ABD0000S'
    assert str(ISAN('ISAN 0123-4567-89AB-CDEF-5-0123-4567-9')) == 'ISAN 0123-4567-89AB-CDEF-5-0123-4567-9'
    assert ISAN('ISAN 0123-4567-89AB-CDEF-5-0123-4567-9').__str__(short = True) == '0123456789ABCDEF5012345679'
    assert str(ISAN('000000003abd0000s')) == 'ISAN 0000-0000-3ABD-0000-S'
    assert ISAN('000000003abd0000s').__str__(short = True) == '000000003ABD0000S'
    assert str(ISAN('0123456789abcdef5012345679')) == 'ISAN 0123-4567-89AB-CDEF-5-0123-4567-9'
    assert ISAN('0123456789abcdef5012345679').__str__(short = True) == '0123456789ABCDEF5012345679'
    # test the ISAN constructor and the ISAN str() implementation in a non-public context (including a private version)
    assert str(ISAN('ISAN 0000-0000-3ABD-0000-S', public = False)) == 'ISAN 0000-0000-3ABD-0000-S'
    assert ISAN('ISAN 0000-0000-3ABD-0000-S', public = False).__str__(short = True) == '000000003ABD0000S'
    assert str(ISAN('ISAN 0123-4567-89AB-CDEF-5-0123-4567-9', public = False)) == 'ISAN 0123-4567-89AB-CDEF-5-0123-4567-9'
    assert ISAN('ISAN 0123-4567-89AB-CDEF-5-0123-4567-9', public = False).__str__(short = True) == '0123456789ABCDEF5012345679'
    assert str(ISAN('ISAN 1881-66C7-3420-0000-3-FF3A-0245-N', public = False)) == 'ISAN 1881-66C7-3420-0000-3-FF3A-0245-N'
    assert ISAN('ISAN 1881-66C7-3420-0000-3-FF3A-0245-N', public = False).__str__(short = True) == '188166C7342000003FF3A0245N'
    assert str(ISAN('000000003abd0000s', public = False)) == 'ISAN 0000-0000-3ABD-0000-S'
    assert ISAN('000000003abd0000s', public = False).__str__(short = True) == '000000003ABD0000S'
    assert str(ISAN('0123456789abcdef5012345679', public = False)) == 'ISAN 0123-4567-89AB-CDEF-5-0123-4567-9'
    assert ISAN('0123456789abcdef5012345679', public = False).__str__(short = True) == '0123456789ABCDEF5012345679'
    assert str(ISAN('188166c7342000003ff3a0245n', public = False)) == 'ISAN 1881-66C7-3420-0000-3-FF3A-0245-N'
    assert ISAN('188166c7342000003ff3a0245n', public = False).__str__(short = True) == '188166C7342000003FF3A0245N'
    # test the ISAN comparison implementation
    assert ISAN('000000003abd0000s') == ISAN('ISAN 0000-0000-3ABD-0000-S')
    assert ISAN('0123456789abcdef5012345679') == ISAN('ISAN 0123-4567-89AB-CDEF-5-0123-4567-9')
    assert ISAN('ISAN 0000-0000-3ABD-0000-Z', autocorrect = True) == ISAN('ISAN 0000-0000-3ABD-0000-S')
    assert ISAN('ISAN B159-D8FA-0124-0000-K') > ISAN('ISAN 0000-3BAB-9352-0000-G')
    assert ISAN('ISAN 0000-3BAB-9352-0000-G') < ISAN('ISAN B159-D8FA-0124-0000-K')
    assert ISAN('ISAN 0000-3BAB-9352-0000-G') < ISAN('ISAN 0000-3BAB-9352-0000-G-0000-0000-Q')
    assert ISAN('ISAN B159-D8FA-0124-0000-K') != ISAN('ISAN 0000-3BAB-9352-0000-G')
    assert ISAN('ISAN 0000-3BAB-9352-0000-G') != ISAN('ISAN B159-D8FA-0124-0000-K')
    assert ISAN('ISAN 0000-3BAB-9352-0000-G') != ISAN('ISAN 0000-3BAB-9352-0000-G-0000-0000-Q')
    assert ISAN('ISAN 0000-3BAB-9352-0000-G') == ISAN('ISAN 0000-3BAB-9352-0000-G')
    assert ISAN('ISAN 0000-3BAB-9352-0000-G-0000-0000-Q') == ISAN('ISAN 0000-3BAB-9352-0000-G-0000-0000-Q')
    # test the ISAN check character autocorrection feature, stringification, and comparison
    for r, s in (
        ('ISAN 0000-0000-3ABD-0000-S',             'ISAN 0000-0000-3ABD-0000-Z'),
        ('ISAN 006A-15FA-002B-C95F-W',             'ISAN 006A-15FA-002B-C95F-A'),
        ('ISAN 1881-66C7-3420-0000-3',             'ISAN 1881-66C7-3420-0000-7'),
        ('ISAN 0000-1234-1234-1234-H-0000-0000-N', 'ISAN 0000-1234-1234-1234-X-0000-0000-Y'),
        ('ISAN 1881-66C7-3420-0000-3-9F3A-0245-Q', 'ISAN 1881-66C7-3420-0000-7-9F3A-0245-U'),
        ):
        assert ISAN(r) == ISAN(s, autocorrect = True)
        assert str(ISAN(r)) == str(ISAN(s, autocorrect = True))
        assert ISAN(r).__str__(short = True) == ISAN(s, autocorrect = True).__str__(short = True)
        pass
    # make sure comparisons between ISANs and non-ISANs raise a TypeError
    try:
        tmp = ISAN('ISAN 0000-0000-3ABD-0000-S') != 'ISAN 0000-0000-3ABD-0000-S'
        assert tmp
    except TypeError, t: pass
    else: raise RuntimeError('comparison between ISAN and string should not work')
    try: 
        tmp = 'ISAN 0000-0000-3ABD-0000-S' != ISAN('ISAN 0000-0000-3ABD-0000-S')
        assert tmp;
    except TypeError, t: pass
    else: raise RuntimeError('comparison between ISAN and string should not work')
    # test accessors
    i = ISAN('ISAN 0000-0000-3ABD-0000-S')
    assert i.public == True
    assert i.isan == '0000-0000-3ABD-0000'
    assert i.root == '0000-0000-3ABD'
    assert i.episode == '0000'
    assert i.isancheck == 'S'
    assert i.version == None
    assert i.versioncheck == None
    i = ISAN('ISAN 0000-0000-3ABD-0000-S', public = False)
    assert i.public == False
    assert i.isan == '0000-0000-3ABD-0000'
    assert i.root == '0000-0000-3ABD'
    assert i.episode == '0000'
    assert i.isancheck == 'S'
    assert i.version == None
    assert i.versioncheck == None
    i = ISAN('ISAN 0000-3BAB-9352-0000-G-0000-0000-Q')
    assert i.public == True
    assert i.isan == '0000-3BAB-9352-0000'
    assert i.root == '0000-3BAB-9352'
    assert i.episode == '0000'
    assert i.isancheck == 'G'
    assert i.version == '0000-0000'
    assert i.versioncheck == 'Q'
    pass

def main(progname, infile = '-'):
    infile = (infile == '-') and sys.stdin or (type(infile) in (type(''), type(u'')) and file(infile) or infile)
    errors = 0
    while True:
        line = infile.readline()
        if not line: break
        line = line.strip()
        try:
            if line:
                i = ISAN(line)
                print `i`
                print ' printed form =', str(i)
                print ' short form =', i.__str__(short = True)
                print ' public =', i.public
                print ' isan =', i.isan
                print '    root =', i.root
                print '    episode =', i.episode
                print ' isan check character =', i.isancheck
                print ' version =', i.version
                print ' isan + version check character =', i.versioncheck
                pass
            pass
        except Exception, e:
            errors += 1
            print e
            if line:
                try:
                    print 'Perhaps you meant %s?' % ISAN(line, autocorrect = True)
                    pass
                except: pass
                pass
            pass
        pass
    return errors and 1 or 0

test()

if __name__ == '__main__': sys.exit(main(*(sys.argv)))
