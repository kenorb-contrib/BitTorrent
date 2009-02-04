#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
This is a Python module for handling International Standard Musical
Work Codes (ISWCs) and includes structural verification (has to look
like an ISWC) and check digit verification.

The check digit uses a bizarre variation on ISO 7064
(checkPositionModuloReverseBiased).
'''

import re
import sys
import string

def checkPositionModuloReverseBiased(base, digits, bias):
    '''
    Return the position-scaled modulo-BASE check digit integer for the
    given integer sequence ("digits") where each digit is multiplied
    by its position plus one, and the check-digit is the complement of
    the modulo-BASE sum. The sum is initialized using the parameter
    bias.

    Note that leftmost digit in the sequence is multiplied by one,
    the next to the right by two, etc.
    '''
    isum = bias
    for x in xrange(0, len(digits)):
        isum = (isum + ((x + 1) * digits[x])) % base
        pass
    return (base - isum) % base

class ISWC(object):
    '''

    International Standard Musical Work Code (ISWC)
    ISO 15707
    http://www.iswc.org/

    Examples of valid ISWCs:

     ISWC T-034524680-1
     ISWC T-034.524.680-1
     T-034524680-1
     T-071.464.731-0
     T-041.630.263-0
     T-041.470.427-0
     T-041.497.267-0
     T-003.977.931-1
     T-001.858.212-1
     T-003.999.022-1
     T-800.233.132-1
     T-041.436.204-1
     T-071.251.804-1
     T-001.869.946-1
     T-071.593.329-1
     T-004.277.839-1
     T-041.239.759-1
     T-800.237.810-2
     T-071.821.820-2
     T-004.300.803-2
     T-070.535.484-2
     T-070.225.194-2
     T-003.143.216-2
     T-037.031.637-2
     T-070.446.148-2
     T-041.089.180-3
     T-004.308.991-3
     T-001.857.852-3
     T-041.095.872-3
     T-071.377.945-3
     T-070.364.355-3
     T-070.223.127-3
     T-041.397.038-3
     T-800.449.248-3
     T-004.302.441-4
     T-003.140.692-4
     T-071.076.736-4
     T-800.043.386-4
     T-001.870.437-4
     T-041.424.048-4
     T-070.223.479-4
     T-070.224.840-5
     T-001.876.280-5
     T-041.220.615-5
     T-070.224.735-5
     T-041.414.175-5
     T-001.884.495-5
     T-041.191.507-5
     T-003.145.148-5
     T-800.195.689-5
     T-003.140.050-6
     T-001.880.060-6
     T-001.863.911-6
     T-070.846.342-6
     T-070.500.742-6
     T-070.230.004-6
     T-001.881.244-6
     T-041.471.754-6
     T-800.541.019-6
     T-041.520.504-7
     T-800.301.127-7
     T-070.224.397-7
     T-800.322.580-8
     T-070.225.124-8
     T-041.028.286-8
     T-800.512.096-8
     T-042.020.444-9
     T-072.324.747-9
     T-001.872.939-9
     | |         | |
     | |         |  \_ Check digit
     |  \________|
     |            \___ Work identifier (nine digits)
     |
     |
      \_______________ Prefix (always the letter "T" for the initial
                       phase)

    Structure: one-character prefix (required to be "T" for now)
    followed by a nine-digit work identifier, followed by a check
    digit.

    The check digit is calculated according to a bizarre modification
    of an ISO 7064 scheme where the digits are weighted in ascending
    order from the left, and the sum is incremented by a bias (bias =
    1 for ISWC); the check digit is the modulo-10 complement of the
    sum.
    '''
    # FIXME: we permit lower case and an optional colon after the
    # initial ISWC, even though this is non-standard; the result
    # returned by str() will be in canonical form however.
    iswc_re = re.compile(
        r'''
        \A
        (?:ISWC:?[ ])?
        (?P<prefix>T)
        -?
        (?P<iswc>[0-9]{3,3}[.]?[0-9]{3,3}[.]?[0-9]{3,3})
        -?
        (?P<iswccheck>[0-9])
        \Z
        ''',
        re.VERBOSE | re.IGNORECASE | re.UNICODE)
    def __init__(self, s, autocorrect = False):
        '''
        Initialize an ISWC from a string ("s"); set the optional flag
        autocorrect = True to replace the supplied check digit with
        the correct one rather than raising an exception when the
        check digit is not valid.

        Canonical form (input and output); ISWC prefix is optional on
        input:

        ISWC T-nnn.nnn.nnn-c

        Short forms (input only):
        ISWC T-nnnnnnnnn-c
        ISWC Tnnnnnnnnnc

        Where n is a decimal digit and c is a decimal check
        digit. Case is ignored on input, and hyphens and dots are
        optional. A colon may optionally appear after the initial
        ISWC. On output (using str()) all letters are upper case.
        '''
        match = self.iswc_re.match(str(s))
        if not match: raise ValueError('invalid literal for %s.%s(): %r' % (self.__class__.__module__, self.__class__.__name__, s))
        for part in ('prefix', 'iswc', 'iswccheck'):
            setattr(self, part, ''.join(match.group(part).upper().split('.')))
            pass
        self.check(autocorrect = autocorrect)
        return
    def __cmp__(self, iswc):
        '''
        Compare this ISWC with another object, returning -1 if the
        other is greater than this one, 0 if the other is equal to
        this one, or 1 if the other is less than this one.
        '''
        if not isinstance(iswc, ISWC):
            raise TypeError('%s.%s.__cmp__(self, iswc) requires iswc to be a %s.%s, not a %s.%s' % (ISWC.__module__, ISWC.__name__, ISWC.__module__, ISWC.__name__, type(iswc).__module__, type(iswc).__name__))
        return cmp(str(self), str(iswc))
    def check(self, autocorrect = False):
        '''
        Verify the ISWC check digit. If it does not match, this raises
        a ValueError. The optional parameter autocorrect = True
        instead silently fixes the check digit.
        '''
        checkdigit = checkPositionModuloReverseBiased(10, [ int(ch, 16) for ch in self.iswc ], 1)
        if autocorrect: self.iswccheck = str(checkdigit)
        if int(self.iswccheck) != checkdigit:
            raise ValueError('invalid check digit for %s: %s' % (self, self.iswccheck))
        return
    def __repr__(self): return '%s.%s(%r)' % (self.__class__.__module__, self.__class__.__name__, str(self))
    def __str__(self, short = False):
        '''
        Stringify an ISWC; the optional flag short = True omits the ISWC prefix and punctuation
        '''
        o = []
        if not short: o.append('ISWC ')
        o.append(self.prefix)
        if not short: o.append('-')
        o.append(self.iswc[:3])
        if not short: o.append('.')
        o.append(self.iswc[3:6])
        if not short: o.append('.')
        o.append(self.iswc[6:])
        if not short: o.append('-')
        o.append(self.iswccheck)
        return ''.join(o)
    pass

def test():
    '''
    Self-tests for the ISWC module
    '''
    # test the check digit calculator (positive tests)
    for base, digits, bias, ck in (
        (10, '0345246801', 1, 1),
        ):
        try: assert checkPositionModuloReverseBiased(base, [ int(digit, 36) for digit in digits ], bias) == ck
        except:
            print 'checkPositionModuloReverseBiased failed for:'
            print ' base =', base
            print ' digits =', digits
            print ' bias =', bias
            print ' ck =', ck
            raise
        pass
    # test the check digit calculator (negative tests)
    for base, digits, bias, ck in (
        (10, '0345246801', 1, 2),
        ):
        try: assert checkPositionModuloReverseBiased(base, [ int(digit, 36) for digit in digits ], bias) != ck
        except:
            print 'checkPositionModuloReverseBiased failed for:'
            print ' base =', base
            print ' digits =', digits
            print ' bias =', bias
            print ' ck =', ck
            raise
        pass
    # test the ISWC constructor (positive tests)
    for s in (
        '''
        T-000000001-0
        T0345246801
        ISWC T-034524680-1
        ISWC T-034.524.680-1
        iswc t-034.524.680-1
        t-034.524.680-1
        t0345246801
        T-034524680-1
        T-071.464.731-0
        T-041.630.263-0
        T-041.470.427-0
        T-041.497.267-0
        T-003.977.931-1
        T-001.858.212-1
        T-003.999.022-1
        T-800.233.132-1
        T-041.436.204-1
        T-071.251.804-1
        T-001.869.946-1
        T-071.593.329-1
        T-004.277.839-1
        T-041.239.759-1
        T-800.237.810-2
        T-071.821.820-2
        T-004.300.803-2
        T-070.535.484-2
        T-070.225.194-2
        T-003.143.216-2
        T-037.031.637-2
        T-070.446.148-2
        T-041.089.180-3
        T-004.308.991-3
        T-001.857.852-3
        T-041.095.872-3
        T-071.377.945-3
        T-070.364.355-3
        T-070.223.127-3
        T-041.397.038-3
        T-800.449.248-3
        T-004.302.441-4
        T-003.140.692-4
        T-071.076.736-4
        T-800.043.386-4
        T-001.870.437-4
        T-041.424.048-4
        T-070.223.479-4
        T-070.224.840-5
        T-001.876.280-5
        T-041.220.615-5
        T-070.224.735-5
        T-041.414.175-5
        T-001.884.495-5
        T-041.191.507-5
        T-003.145.148-5
        T-800.195.689-5
        T-003.140.050-6
        T-001.880.060-6
        T-001.863.911-6
        T-070.846.342-6
        T-070.500.742-6
        T-070.230.004-6
        T-001.881.244-6
        T-041.471.754-6
        T-800.541.019-6
        T-041.520.504-7
        T-800.301.127-7
        T-070.224.397-7
        T-800.322.580-8
        T-070.225.124-8
        T-041.028.286-8
        T-800.512.096-8
        T-042.020.444-9
        T-072.324.747-9
        T-001.872.939-9
        '''.splitlines()
        ):
        s = s.strip()
        if s:
            try:
                ISWC(s)
            except:
                print 'ISWC failed for s =', s
                raise
            pass
        pass
    # test the ISWC constructor (negative tests)
    for s in (
        '''
        T0345246800
        ISWC T-034524680-2
        ISWC T-034.524.680-3
        T-034524680-4
        T-071.464.731-1
        T-041.630.263-2
        T-041.470.427-3
        T-041.497.267-4
        T-003.977.931-5
        T-001.858.212-6
        T-003.999.022-7
        T-800.233.132-8
        T-041.436.204-9
        T-071.251.804-0
        T-001.869.946-2
        T-071.593.329-3
        T-004.277.839-4
        T-041.239.759-5
        T-800.237.810-0
        T-071.821.820-1
        T-004.300.803-3
        T-070.535.484-4
        T-070.225.194-5
        T-003.143.216-6
        T-037.031.637-7
        T-070.446.148-8
        T-041.089.180-0
        T-004.308.991-1
        T-001.857.852-2
        T-041.095.872-4
        T-071.377.945-5
        T-070.364.355-6
        T-070.223.127-7
        T-041.397.038-8
        T-800.449.248-9
        T-004.302.441-0
        T-003.140.692-1
        T-071.076.736-2
        T-800.043.386-3
        T-001.870.437-5
        T-041.424.048-6
        T-070.223.479-9
        T-070.224.840-0
        T-001.876.280-1
        T-041.220.615-2
        T-070.224.735-3
        T-041.414.175-4
        T-001.884.495-6
        T-041.191.507-7
        T-003.145.148-8
        T-800.195.689-9
        T-003.140.050-0
        T-001.880.060-1
        T-001.863.911-2
        T-070.846.342-3
        T-070.500.742-4
        T-070.230.004-5
        T-001.881.244-7
        T-041.471.754-8
        T-800.541.019-9
        T-041.520.504-0
        T-800.301.127-6
        T-070.224.397-9
        T-800.322.580-6
        T-070.225.124-7
        T-041.028.286-9
        T-800.512.096-0
        T-042.020.444-0
        T-072.324.747-1
        T-001.872.939-8
        ISWC 0000-0000-3ABD-0000-Z
        ISWC 006A-15FA-002B-C95F-A
        ISWC 1881-66C7-3420-0000-7
        ISWC 0000-1234-1234-1234-X-0000-0000-Y
        ISWC 1881-66C7-3420-0000-7-9F3A-0245-U
        ISWC 1881-66C7-3420-0000-3-FF3A-0245-N
        ISWC: 0000-0000-3ABD-0000-Z
        ISWC: 006A-15FA-002B-C95F-A
        ISWC: 1881-66C7-3420-0000-7
        ISWC: 0000-1234-1234-1234-X-0000-0000-Y
        ISWC: 1881-66C7-3420-0000-7-9F3A-0245-U
        ISWC: 1881-66C7-3420-0000-3-FF3A-0245-N
        000000003ABD0000Z
        006A15FA002BC95FA
        188166C7342000007
        0000123412341234X00000000Y
        188166C73420000079F3A0245U
        188166C7342000003FF3A0245N
        iswc 0000-0000-3abd-0000-z
        iswc 006a-15fa-002b-c95f-a
        iswc 1881-66c7-3420-0000-7
        iswc 0000-1234-1234-1234-x-0000-0000-y
        iswc 1881-66c7-3420-0000-7-9f3a-0245-u
        iswc 1881-66c7-3420-0000-3-ff3a-0245-n
        iswc: 0000-0000-3abd-0000-z
        iswc: 006a-15fa-002b-c95f-a
        iswc: 1881-66c7-3420-0000-7
        iswc: 0000-1234-1234-1234-x-0000-0000-y
        iswc: 1881-66c7-3420-0000-7-9f3a-0245-u
        iswc: 1881-66c7-3420-0000-3-ff3a-0245-n
        000000003abd0000z
        006a15fa002bc95fa
        188166c7342000007
        0000123412341234x00000000y
        188166c73420000079f3a0245u
        188166c7342000003ff3a0245n
        '''.splitlines()
        ):
        s = s.strip()
        if s:
            try: ISWC(s)
            except ValueError, v: pass
            else:
                print 'ISWC should have failed for s =', s
                assert False
                pass
            pass
        pass
    # test the ISWC constructor and the ISWC str() implementation
    assert str(ISWC('ISWC T-001.872.939-9')) == 'ISWC T-001.872.939-9'
    assert str(ISWC('t0018729399')) == 'ISWC T-001.872.939-9'
    assert ISWC('ISWC T-001.872.939-9').__str__(short = True) == 'T0018729399'
    assert ISWC('t0018729399').__str__(short = True) == 'T0018729399'
    # test the ISWC comparison implementation
    assert ISWC('t0018729399') == ISWC('ISWC T-001.872.939-9')
    assert ISWC('ISWC T-001.872.939-8', autocorrect = True) == ISWC('ISWC T-001.872.939-9')
    assert ISWC('ISWC T-001.872.939-9') > ISWC('ISWC T-001.858.212-1')
    assert ISWC('ISWC T-001.858.212-1') < ISWC('ISWC T-001.872.939-9')
    assert ISWC('ISWC T-001.858.212-1') != ISWC('ISWC T-001.872.939-9')
    assert ISWC('ISWC T-001.858.212-1') == ISWC('ISWC T-001.858.212-1')
    # test the ISWC check character autocorrection feature, stringification, and comparison
    for r, s in (
        ('ISWC T-034.524.680-1',             'ISWC T-034.524.680-2'),
        ('ISWC T-071.464.731-0',             'ISWC T-071.464.731-0'),
        ('ISWC T-034.524.680-1',             'T-034524680-0'),
        ('ISWC T-072.324.747-9',             'T-072.324.747-0'),
        ):
        assert ISWC(r) == ISWC(s, autocorrect = True)
        assert str(ISWC(r)) == str(ISWC(s, autocorrect = True))
        assert ISWC(r).__str__(short = True) == ISWC(s, autocorrect = True).__str__(short = True)
        pass
    # make sure comparisons between ISWCs and non-ISWCs raise a TypeError
    try: 
        tmp = ISWC('ISWC T-001.858.212-1') != 'ISWC T-001.858.212-1'
        assert tmp;
    except TypeError, t: pass
    else: raise RuntimeError('comparison between ISWC and string should not work')
    try: 
        tmp = 'ISWC T-001.858.212-1' != ISWC('ISWC T-001.858.212-1')
        assert tmp;
    except TypeError, t: pass
    else: raise RuntimeError('comparison between ISWC and string should not work')
    # test accessors
    i = ISWC('ISWC T-001.858.212-1')
    assert i.prefix == 'T'
    assert i.iswc == '001858212'
    assert i.iswccheck == '1'
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
                i = ISWC(line)
                print `i`
                print ' printed form =', str(i)
                print ' short form =', i.__str__(short = True)
                print ' prefix =', i.prefix
                print ' iswc =', i.iswc
                print ' iswc check character =', i.iswccheck
                pass
            pass
        except Exception, e:
            errors += 1
            print e
            if line:
                try:
                    print 'Perhaps you meant %s?' % ISWC(line, autocorrect = True)
                    pass
                except: pass
                pass
            pass
        pass
    return errors and 1 or 0

test()

if __name__ == '__main__': sys.exit(main(*(sys.argv)))
