#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
This is a Python module for handling Global Release Identifiers
(GRids) and includes check character verification and structural
verification (has to look like a GRid.)
'''

import re
import sys
import string
from isan import checkMOD

class GRid(object):
    '''
    Global Release Identifier (GRid)
    http://www.mi3p-standard.org/

    Examples of invalid GRids (all have incorrect check characters):

    Examples of valid GRids:

     MI3P:A1-2425G-ABC1234002-M
           |   |        |     |
           |   |        |      \_ Check Character
           |   |        |
           |   |         \_ Release Number
           |   |
           |    \_ Issuer Code
           | 
            \_ Identifier Scheme (always A1 for GRid)

    Structure: 18 alphanumeric characters with an optional "MI3P:"
    prefix: Identifier Scheme element (2 characters); Issuer Code
    element (5 characters); Release Number element (10 characters);
    and Check Character element (1 character).

    The check character is calculated according to ISO 7064 MOD
    37,36.
    '''
    grid_re = re.compile(
        r'''
        \A
        (?:
        (?# Canonical form )
        (?:MI3P:)?
        (?P<scheme>A1)
        -
        (?P<issuer>[0-9A-Z]{5,5})
        -
        (?P<release>[0-9A-Z]{10,10})
        -
        (?P<gridcheck>[0-9A-Z])
        |
        (?# Short form )
        (?P<shortscheme>A1)
        (?P<shortissuer>[0-9A-Z]{5,5})
        (?P<shortrelease>[0-9A-Z]{10,10})
        (?P<shortgridcheck>[0-9A-Z])
        )
        \Z
        ''',
        re.VERBOSE | re.IGNORECASE | re.UNICODE)
    grid_alphabet = string.digits + string.uppercase
    def __init__(self, s, autocorrect = False):
        '''
        Initialize a GRid from a string ("s"). Set the optional flag
        autocorrect = True to replace the supplied check character
        with the correct one rather than raising an exception when the
        check character is not valid.

        Canonical form (input and outputn without short = True); MI3P:
        prefix is optional on input:

        MI3P:A1-iiiii-rrrrrrrrrr-y

        Short form (input and output with short = True):
        A1iiiiirrrrrrrrrry

        Where i or r is an alphanumeric character and y is an
        alphanumeric check character. Case is ignored on input. On
        output (using str()) all letters are upper case.
        '''
        match = self.grid_re.match(str(s))
        if not match: raise ValueError('invalid literal for %s.%s(): %r' % (GRid.__module__, GRid.__name__, s))
        for part in ('scheme', 'issuer', 'release', 'gridcheck'):
            setattr(self, part, (match.group(part) or match.group('short' + part) or '').upper())
            pass
        self.check(autocorrect = autocorrect)
        return
    def __cmp__(self, grid):
        '''
        Compare this GRid with another object, returning -1 if the
        other is greater than this one, 0 if the other is equal to
        this one, or 1 if the other is less than this one.
        '''
        if not isinstance(grid, GRid):
            raise TypeError('%s.%s.__cmp__(self, grid) requires grid to be a %s.%s, not a %s.%s' % (GRid.__module__, GRid.__name__, GRid.__module__, GRid.__name__, type(grid).__module__, type(grid).__name__))
        return cmp(str(self), str(grid))
    def check(self, autocorrect = False):
        '''
        Verify the GRid check character. If it does not match, this raises a
        ValueError. The optional parameter autocorrect = True instead
        silently fixes the check character.
        '''
        digits = ''.join(self.scheme + self.issuer + self.release)
        checkdigit = checkMOD(37, 36, [ int(ch, 36) for ch in digits ])
        if autocorrect: self.gridcheck = self.grid_alphabet[checkdigit]
        if int(self.gridcheck, 36) != checkdigit:
            raise ValueError('invalid check character for %s: %s' % (self, self.gridcheck))
        pass
    def __repr__(self): return '%s.%s(%r)' % (__name__, self.__class__.__name__, str(self))
    def __str__(self, short = False):
        '''
        Stringify a GRid
        '''
        o = []
        if not short: o.append('MI3P:')
        o.append(self.scheme)
        if not short: o.append('-')
        o.append(self.issuer)
        if not short: o.append('-')
        o.append(self.release)
        if not short: o.append('-')
        o.append(self.gridcheck)
        return ''.join(o)
    pass

def test():
    '''
    Self-tests for the GRid module
    '''
    # test the GRid constructor (positive tests)
    for s in (
        'MI3P:A1-2425G-ABC1234002-M',
        'A1-2425G-ABC1234002-M',
        'A12425GABC1234002M',
        'mi3p:a1-2425g-abc1234002-m',
        'a1-2425g-abc1234002-m',
        'a12425gabc1234002m',
        ):
        try: GRid(s)
        except:
            print 'GRid failed for s =', s
            raise
        pass
    # test the GRid constructor (negative tests)
    for s in (
        'MI3P:A1-2425G-ABC1234002-L',
        'A1-2425G-ABC1234002-L',
        'A12425GABC1234002L',
        'mi3p:a1-2425g-abc1234002-l',
        'a1-2425g-abc1234002-l',
        'a12425gabc1234002l',
        'MI3P:A2-2425G-ABC1234002-M',
        'A2-2425G-ABC1234002-M',
        'A22425GABC1234002M',
        'mi3p:a2-2425g-abc1234002-m',
        'a2-2425g-abc1234002-m',
        'a22425gabc1234002m',
        'GRID:A1-2425G-ABC1234002-M',
        'grid:a1-2425g-abc1234002-m',
        ):
        try: GRid(s)
        except ValueError, v: pass
        else:
            print 'GRid should have failed for s =', s
            assert False
            pass
        pass
    # test the GRid constructor and the GRid str() implementation
    assert str(GRid('MI3P:A1-2425G-ABC1234002-M')) == 'MI3P:A1-2425G-ABC1234002-M'
    assert str(GRid('A1-2425G-ABC1234002-M')) == 'MI3P:A1-2425G-ABC1234002-M'
    assert str(GRid('A12425GABC1234002M')) == 'MI3P:A1-2425G-ABC1234002-M'
    assert str(GRid('mi3p:a1-2425g-abc1234002-m')) == 'MI3P:A1-2425G-ABC1234002-M'
    assert str(GRid('a1-2425g-abc1234002-m')) == 'MI3P:A1-2425G-ABC1234002-M'
    assert str(GRid('a12425gabc1234002m')) == 'MI3P:A1-2425G-ABC1234002-M'
    assert GRid('MI3P:A1-2425G-ABC1234002-M').__str__(short = True) == 'A12425GABC1234002M'
    assert GRid('A1-2425G-ABC1234002-M').__str__(short = True) == 'A12425GABC1234002M'
    assert GRid('A12425GABC1234002M').__str__(short = True) == 'A12425GABC1234002M'
    assert GRid('mi3p:a1-2425g-abc1234002-m').__str__(short = True) == 'A12425GABC1234002M'
    assert GRid('a1-2425g-abc1234002-m').__str__(short = True) == 'A12425GABC1234002M'
    assert GRid('a12425gabc1234002m').__str__(short = True) == 'A12425GABC1234002M'
    # test the GRid comparison implementation
    assert GRid('MI3P:A1-2425G-ABC1234002-M') == GRid('MI3P:A1-2425G-ABC1234002-M')
    assert GRid('a12425gabc1234002m') == GRid('MI3P:A1-2425G-ABC1234002-M')
    assert GRid('MI3P:A1-2425G-ABC1234002-L', autocorrect = True) == GRid('MI3P:A1-2425G-ABC1234002-M')
    assert GRid('MI3P:A1-2425G-ABC1234002-M') > GRid('MI3P:A1-2425G-ABC1234001-O')
    assert GRid('MI3P:A1-2425G-ABC1234001-O') < GRid('MI3P:A1-2425G-ABC1234002-M')
    assert GRid('MI3P:A1-2425G-ABC1234002-M') != GRid('MI3P:A1-2425G-ABC1234001-O')
    # test the GRid check character autocorrection feature, stringification, and comparison
    for r, s in (
        ('MI3P:A1-2425G-ABC1234002-M',             'MI3P:A1-2425G-ABC1234002-L'),
        ):
        assert GRid(r) == GRid(s, autocorrect = True)
        assert str(GRid(r)) == str(GRid(s, autocorrect = True))
        assert GRid(r).__str__(short = True) == GRid(s, autocorrect = True).__str__(short = True)
        pass
    # make sure comparisons between GRids and non-GRids raise a TypeError
    try: 
        tmp = GRid('MI3P:A1-2425G-ABC1234002-M') != 'MI3P:A1-2425G-ABC1234002-M'
        assert tmp
    except TypeError, t: pass
    else: raise RuntimeError('comparison between GRid and string should not work')
    try: 
        tmp = 'MI3P:A1-2425G-ABC1234002-M' != GRid('MI3P:A1-2425G-ABC1234002-M')
        assert tmp
    except TypeError, t: pass
    else: raise RuntimeError('comparison between GRid and string should not work')
    # test accessors
    i = GRid('MI3P:A1-2425G-ABC1234002-M')
    assert i.scheme == 'A1'
    assert i.issuer == '2425G'
    assert i.release == 'ABC1234002'
    assert i.gridcheck == 'M'
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
                i = GRid(line)
                print `i`
                print ' printed form =', str(i)
                print ' short form =', i.__str__(short = True)
                print ' scheme =', i.scheme
                print ' issuer =', i.issuer
                print ' release =', i.release
                print ' grid check character =', i.gridcheck
                pass
            pass
        except Exception, e:
            errors += 1
            print e
            if line:
                try:
                    print 'Perhaps you meant %s?' % GRid(line, autocorrect = True)
                    pass
                except: pass
                pass
            pass
        pass
    return errors and 1 or 0

test()

if __name__ == '__main__': sys.exit(main(*(sys.argv)))
