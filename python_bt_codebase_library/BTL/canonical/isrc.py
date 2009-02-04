#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
This is a Python module for handling International Standard Recording
Codes (ISRCs) and includes country code verification, year
verification (years before 1940 or more than one day in the future are
not permitted unless the optional flag old_recording_hack = True is
used) and structural verification (has to look like an ISRC.)

NOTE: ISRCs have a serious Y2K-like problem in the year 2040, which is
not distinguished from 1940 (both use "40") in the two-digit year
field of the ISRC. This implementation assumes that years >= 2040 will
be represented using all (four) digits, and those earlier than 1940
using two. The output uses that recipe for canonicalization.

FIXME: THIS BEHAVIOR IS NOT STANDARD AND IS NOT LIKELY TO BE
COMPATIBLE WITH OTHER IMPLEMENTATIONS, AT LEAST IN THE NEAR FUTURE.
'''
import re
import sys
import string
import time
import iso_3166_1_alpha_2

# Year of earliest known sound recording capable of being played back,
# used as a sanity check when we get four-digit years in ISRCs
EARLIEST_RECORDING_YEAR = 1877

class ISRC(object):
    '''

    International Standard Recording Code (ISRC)
    ISO 3901
    http://www.ifpi.org/isrc/

    Examples of valid ISRCs:

     ISRC GB-EMI-03-00013
     ISRC BR-BMG-03-00729
     ISRC US-PR3-73-00012
     ISRC FR-Z03-98-00212
     ISRC FR-Z03-91-01231
     ISRC FR-Z03-91-01232
     ISRC FR-Z03-91-01233
     ISRC FR-Z03-91-01240
     ISRC FR-Z03-90-02345
     ISRC FR-Z03-89-03456
     ISRC FR-Z03-88-06789
          |  |   |   |
          |  |   |    \_ designation code, five remaining digits
          |  |   |
          |  |    \_ the last two digits of the year of registration;
          |  |       officially the earliest year represented should be 1940
          |  |       but in practice some earlier years were used
          |  |
          |   \_ a three character alphanumeric registrant code, uniquely
          |      identifying the organization which registered the code
          |
           \_ country code (ISO 3166-1 alpha-2)

    '''
    # FIXME: we permit lower case and an optional colon after the
    # optional initial ISRC, even though this is non-standard; the
    # result returned by str() will be in canonical form however.
    isrc_re = re.compile(
        r'''
        \A
        (?:
        (?:ISRC:?[ ])?
        (?P<country>[A-Z]{2,2})
        -
        (?P<registrant>[A-Z0-9]{3,3})
        -
        (?P<year>(?:[0-9]{2,})?[0-9]{2,2})
        -
        (?P<designation>[0-9]{5,5})
        |
        (?P<shortcountry>[A-Z]{2,2})
        (?P<shortregistrant>[A-Z0-9]{3,3})
        (?P<shortyear>(?:[0-9]{2,})?[0-9]{2,2})
        (?P<shortdesignation>[0-9]{5,5})
        )
        \Z
        ''',
        re.VERBOSE | re.IGNORECASE | re.UNICODE)
    new_countries = dict([ line.split(' ', 1) for line in iso_3166_1_alpha_2.current.splitlines() if line ])
    old_countries = dict([ line.split(' ', 1) for line in iso_3166_1_alpha_2.withdrawn.splitlines() if line ])
    non_countries = dict([ line.split(' ', 1) for line in (iso_3166_1_alpha_2.private + '\n' + iso_3166_1_alpha_2.reserved).splitlines() if line ])
    def __init__(self, s, old_recording_hack = False):
        '''
        Initialize an ISRC from a string ("s"); set the optional flag
        old_recording_hack = True if this ISRC is one of the few
        issued with retroactive year codes from before 1940.

        Long form (input and output without short = True):

        ISRC cc-rrr-yyyy-ddddd
        ISRC cc-rrr-yy-ddddd

        Short form (input and output with short = True):

        ccrrryyyyddddd
        ccrrryyddddd

        Where cc    is an ISO 3166-1 alpha-2 country code;
              rrr   is a three character alphanumeric registrant code;
              yy    is the last two digits on the year of registration;
              yyyy  is the full year of registration (for years before
                    1940 and years after 2039);
          and ddddd is a five-digit designation code.

        Case is ignored on input, and spaces may be used instead of
        hyphens. A colon may optionally appear after the initial
        ISRC. On output (using str()) all letters are upper case.
        '''
        match = self.isrc_re.match(str(s))
        if not match: raise ValueError('invalid literal for %s.%s(): %r' % (__name__, self.__class__.__name__, s))
        for part in ('country', 'registrant', 'year', 'designation'):
            setattr(self, part, (match.group(part) or match.group('short' + part)).upper())
            pass
        self.countryname = self.new_countries.get(self.country, self.old_countries.get(self.country, None))
        self.yearnum = int(self.year)
        if len(self.year) == 2:
            if self.yearnum < 40 and not old_recording_hack: self.yearnum += 2000
            else: self.yearnum += 1900
            pass
        if self.yearnum >= 1940 and self.yearnum < 2040: self.year = str(self.yearnum % 100).zfill(2)
        else: self.year = str(self.yearnum).zfill(4)
        self.check(old_recording_hack = old_recording_hack)
        return
    def __cmp__(self, isrc):
        '''
        Compare this ISRC with another object, returning -1 if the
        other is greater than this one, 0 if the other is equal to
        this one, or 1 if the other is less than this one.
        '''
        if not isinstance(isrc, ISRC):
            raise TypeError('%s.%s.__cmp__(self, isrc) requires isrc to be a %s.%s, not a %s.%s' % (ISRC.__module__, ISRC.__name__, ISRC.__module__, ISRC.__name__, type(isrc).__module__, type(isrc).__name__))
        return cmp(str(self), str(isrc))
    def check(self, old_recording_hack = False):
        '''
        Verify the ISRC country code and year; the optional flag
        old_recording_hack = True disables year validation, otherwise
        future years (codes for the year after tomorrow but before
        1940) are disallowed, as are years during which the obsolete
        country code in use was already withdrawn [only applies when
        used with obsolete country codes].
        '''
        if self.yearnum < EARLIEST_RECORDING_YEAR:
            if not old_recording_hack:
                raise ValueError('invalid year for %r: %s (pre-%s)' % (self, self.yearnum, EARLIEST_RECORDING_YEAR))
            pass
        if (time.gmtime(time.time() + 1 + 24 * 60 * 60)[0]) < self.yearnum:
            raise ValueError('invalid year for %r: %s (future)' % (self, self.yearnum))
        if self.non_countries.has_key(self.country) and self.countryname is None:
            raise ValueError('invalid reserved country code for %r: %r' % (self, self.country))
        if self.countryname is not None:
            if self.old_countries.get(self.country, None) == self.countryname:
                year_withdrawn = int(self.countryname.split(';')[0].split()[-1])
                if self.yearnum > year_withdrawn:
                    raise ValueError('invalid use of withdrawn country code for %r in year %s: %s' % (self, self.yearnum, self.countryname))
                pass
            pass
        pass
    def __repr__(self): return '%s.%s(%r)' % (__name__, self.__class__.__name__, str(self))
    def __str__(self, short = False):
        '''
        Stringify an ISRC; the optional short = True omits the ISRC
        prefix and hyphens.
        '''
        o = []
        if not short: o.append('ISRC ')
        o.append(self.country)
        if not short: o.append('-')
        o.append(self.registrant)
        if not short: o.append('-')
        o.append(self.year)
        if not short: o.append('-')
        o.append(self.designation)
        return ''.join(o)
    pass

def test():
    '''
    Self-tests for the ISRC module
    '''
    # test the ISRC constructor (positive tests)
    for s in (
        '''
        ISRC GB-EMI-03-00013
        ISRC BR-BMG-03-00729
        ISRC US-PR3-73-00012
        ISRC FR-Z03-98-00212
        ISRC FR-Z03-91-01231
        ISRC FR-Z03-91-01232
        ISRC FR-Z03-91-01233
        ISRC FR-Z03-91-01240
        ISRC FR-Z03-90-02345
        ISRC FR-Z03-89-03456
        ISRC FR-Z03-88-06789
        ISRC YU-Z03-91-01232
        ISRC SU-Z03-92-01233
        ISRC FX-Z03-88-06789
        ISRC US-Z03-40-06789
        ISRC GB-EMI-1903-00013
        ISRC BR-BMG-1903-00729
        ISRC US-PR3-1973-00012
        ISRC FR-Z03-1998-00212
        ISRC FR-Z03-1991-01231
        ISRC FR-Z03-1991-01232
        ISRC FR-Z03-1991-01233
        ISRC FR-Z03-1991-01240
        ISRC FR-Z03-1990-02345
        ISRC FR-Z03-1989-03456
        ISRC FR-Z03-1988-06789
        ISRC YU-Z03-1991-01232
        ISRC SU-Z03-1992-01233
        ISRC FX-Z03-1988-06789
        ISRC US-Z03-1940-06789
        ISRC US-XXX-1877-00000
        ISRC GB-EMI-2003-00013
        ISRC BR-BMG-2003-00729
        GBEMI0300013
        BRBMG0300729
        USPR37300012
        FRZ039800212
        FRZ039101231
        FRZ039101232
        FRZ039101233
        FRZ039101240
        FRZ039002345
        FRZ038903456
        FRZ038806789
        YUZ039101232
        SUZ039201233
        FXZ038806789
        USZ034006789
        GBEMI190300013
        BRBMG190300729
        USPR3197300012
        FRZ03199800212
        FRZ03199101231
        FRZ03199101232
        FRZ03199101233
        FRZ03199101240
        FRZ03199002345
        FRZ03198903456
        FRZ03198806789
        YUZ03199101232
        SUZ03199201233
        FXZ03198806789
        USZ03194006789
        USXXX187700000
        GBEMI200300013
        BRBMG200300729
        '''
        ).splitlines():
        s = s.strip()
        if s:
            try: ISRC(s)
            except:
                print 'ISRC failed for s =', s
                raise
            pass
        pass
    # test the ISRC constructor (negative tests)
    for s in (
        '''
        ISRC UK-EMI-03-00013
        ISRC EU-BMG-03-00729
        ISRC XX-PR3-73-00012
        ISRC ZZ-Z03-98-00212
        ISRC BU-Z03-91-01231
        ISRC YU-Z03-04-01232
        ISRC SU-Z03-93-01233
        ISRC FX-Z03-98-06789
        ISRC US-Z03-100-06789
        ISRC US-XXX-1876-00000
        UKEMI0300013
        EUBMG0300729
        XXPR37300012
        ZZZ039800212
        BUZ039101231
        YUZ030401232
        SUZ039301233
        FXZ039806789
        USZ0310006789
        USXXX187600000
        '''
        +
        # this part of the test would otherwise stop working at the end of 2038
        ((time.gmtime()[0] < 2038) and
         '''
         ISRC US-Z03-39-06789
         ISRC US-Z03-2039-06789
         ISRC US-PR3-2073-00012
         ISRC FR-Z03-2098-00212
         ISRC FR-Z03-2091-01231
         ISRC FR-Z03-2091-01232
         ISRC FR-Z03-2091-01233
         ISRC FR-Z03-2091-01240
         ISRC FR-Z03-2090-02345
         ISRC FR-Z03-2089-03456
         ISRC FR-Z03-2088-06789
         ISRC YU-Z03-2091-01232
         ISRC SU-Z03-2092-01233
         ISRC FX-Z03-2088-06789
         ISRC US-Z03-2040-06789
         USZ033906789
         USZ03203906789
         USPR3207300012
         FRZ03209800212
         FRZ03209101231
         FRZ03209101232
         FRZ03209101233
         FRZ03209101240
         FRZ03209002345
         FRZ03208903456
         FRZ03208806789
         YUZ03209101232
         SUZ03209201233
         FXZ03208806789
         USZ03204006789
         '''
         or
         ''
         )
        ).splitlines():
        s = s.strip()
        if s:
            try: ISRC(s)
            except ValueError, v: pass
            else:
                print 'ISRC should have failed for s =', s
                assert False
                pass
            pass
        pass
    # test the ISRC constructor and the ISRC str() implementation
    assert str(ISRC('ISRC GB-EMI-03-00013')) == 'ISRC GB-EMI-03-00013'
    assert str(ISRC('ISRC: GB-EMI-03-00013')) == 'ISRC GB-EMI-03-00013'
    assert str(ISRC('GBEMI0300013')) == 'ISRC GB-EMI-03-00013'
    assert str(ISRC('isrc gb-emi-03-00013')) == 'ISRC GB-EMI-03-00013'
    assert str(ISRC('isrc: gb-emi-03-00013')) == 'ISRC GB-EMI-03-00013'
    assert str(ISRC('gbemi0300013')) == 'ISRC GB-EMI-03-00013'
    assert ISRC('ISRC GB-EMI-03-00013').__str__(short = True) == 'GBEMI0300013'
    assert ISRC('ISRC: GB-EMI-03-00013').__str__(short = True) == 'GBEMI0300013'
    assert ISRC('GBEMI0300013').__str__(short = True) == 'GBEMI0300013'
    assert ISRC('isrc gb-emi-03-00013').__str__(short = True) == 'GBEMI0300013'
    assert ISRC('isrc: gb-emi-03-00013').__str__(short = True) == 'GBEMI0300013'
    assert ISRC('gbemi0300013').__str__(short = True) == 'GBEMI0300013'
    # test the ISRC comparison implementation
    assert ISRC('ISRC GB-EMI-03-00013') == ISRC('ISRC GB-EMI-03-00013')
    assert ISRC('ISRC GB-EMI-03-00013') == ISRC('GBEMI0300013')
    assert ISRC('ISRC GB-EMI-2003-00013') == ISRC('GBEMI0300013')
    assert ISRC('ISRC GB-EMI-00000000002003-00013') == ISRC('GBEMI0300013')
    assert ISRC('ISRC GB-EMI-03-00013') < ISRC('ISRC GB-EMI-04-00013')
    assert ISRC('ISRC GB-EMI-04-00013') > ISRC('ISRC GB-EMI-03-00013')
    assert ISRC('ISRC GB-EMI-03-00013') != ISRC('ISRC GB-EMI-04-00013')
    # make sure comparisons between ISRCs and non-ISRCs raise a TypeError
    try: 
        tmp = ISRC('ISRC GB-EMI-03-00013') != 'GBEMI0300013'
        assert tmp
    except TypeError, t: pass
    else: raise RuntimeError('comparison between ISRC and string should not work')
    try: 
        tmp = 'GBEMI0300013' != ISRC('ISRC GB-EMI-03-00013')
        assert tmp
    except TypeError, t: pass
    else: raise RuntimeError('comparison between ISRC and string should not work')
    # test accessors
    i = ISRC('ISRC GB-EMI-03-00013')
    assert i.country == 'GB'
    assert i.registrant == 'EMI'
    assert i.year == '03'
    assert i.yearnum == 2003
    assert i.designation == '00013'
    i = ISRC('ISRC GB-EMI-2003-00013')
    assert i.country == 'GB'
    assert i.registrant == 'EMI'
    assert i.year == '03'
    assert i.yearnum == 2003
    assert i.designation == '00013'
    i = ISRC('ISRC GB-EMI-40-00013')
    assert i.country == 'GB'
    assert i.registrant == 'EMI'
    assert i.year == '40'
    assert i.yearnum == 1940
    assert i.designation == '00013'
    i = ISRC('ISRC GB-EMI-1940-00013')
    assert i.country == 'GB'
    assert i.registrant == 'EMI'
    assert i.year == '40'
    assert i.yearnum == 1940
    assert i.designation == '00013'
    i = ISRC('ISRC GB-EMI-1938-00013')
    assert i.country == 'GB'
    assert i.registrant == 'EMI'
    assert i.year == '1938'
    assert i.yearnum == 1938
    assert i.designation == '00013'
    i = ISRC('ISRC GB-EMI-38-00013', old_recording_hack = True)
    assert i.country == 'GB'
    assert i.registrant == 'EMI'
    assert i.year == '1938'
    assert i.yearnum == 1938
    assert i.designation == '00013'
    assert i == ISRC('ISRC GB-EMI-1938-00013')
    i = ISRC('ISRC US-XXX-1877-00000')
    assert i.country == 'US'
    assert i.registrant == 'XXX'
    assert i.year == '1877'
    assert i.yearnum == 1877
    assert i.designation == '00000'
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
                i = ISRC(line)
                print `i`
                print ' printed form =', str(i)
                print ' short form =', i.__str__(short = True)
                print ' country =', i.country, `i.countryname`
                print ' registrant =', i.registrant
                print ' year =', i.year, '(%s)' % i.yearnum
                print ' designation =', i.designation
                pass
            pass
        except Exception, e:
            errors += 1
            print e
        pass
    return errors and 1 or 0

test()

if __name__ == '__main__': sys.exit(main(*(sys.argv)))
