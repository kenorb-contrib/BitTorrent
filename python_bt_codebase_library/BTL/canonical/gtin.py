#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
This is a Python module for handling Global Trade Item Numbers (GTINs)
and includes check digit verification and structural verification (has
to look like a GTIN). GTIN is a superset of the older UPC/UCC-12
(12-digit), EAN/UCC-8 (8-digit) and EAN-13/UCC-13 (13-digit) codes,
and consists of fourteen digits, zero-filled on the left. The final
digit is a check digit. They are sometimes written out in full in
EAN/UCC/ITF-14 form, optionally with an auxiliary quantity code as a
second UPC-style code.

This module also handles UPC E/UPC-8 8-digit zero-suppressed
identifiers; use GTIN_from_UPC8 to decompress these and GTIN_to_UPC8
to produce them, or use the UPC8 class.

This module also handles 10- and 13-digit International Standard Book
Numbers (ISBN-10 and ISBN-13 respectively, collectively ISBNs) and the
older 9-digit Standard Book Numbers (SBNs); use GTIN_from_ISBN to
decode these and GTIN_to_ISBN to produce them, or use the ISBN class.

This module also handles 10- and 13-digit Internation Standard Music
Numbers (ISMNs); use GTIN_from_ISMN to decode these and GTIN_to_ISMN
to produce them, or use the ISMN class.

This module also handles 8-digit International Standard Serial Numbers
(ISSNs); use GTIN_from_ISSN to decode these and GTIN_to_ISSN to
produce them, or use the ISSN class.

This module does not calculate UPC/UCC-12 price check digits, nor does
it handle auxiliary bar codes for quantities, issue numbers (ISSN) or
other purposes.

The same check digit algorithm used for GTIN (checkStandardModulo) is
also used for 18-digit Serial Shipping Container Codes (SSCCs),
17-digit Shipment ID/Bill of Lading numbers (BoLs), 10-digit
International Standard Music Numbers (ISMNs), and 13-digit Global
Location Numbers (GLNs).

Tha same check character algorithm used for ISBN (checkPositionModulo)
is also used for 8-digit International Standard Serial Numbers
(ISSNs).

NOTE: EAN.UCC is now known as GS1

FIXME: The Serial Item and Contribution Identifier (SICI) code,
ANSI/NISO Z39.56, and corresponding SISAC barcode format are not yet
handled by this module; they embed ISSN data but also include the year
and month of publication, and the issue number.

FIXME: This module does not handle the more advanced UCC/EAN-128
structure which encodes one or more pieces of typed numeric or
alphanumeric information.

FIXME: This module does not handle Global Location Numbers (GLNs) or
the older EAN Location Numbers; these are however structurally
identical to GTIN and so the same code works for both (note that in
practice the same number means different things depending on whether
it is used in a GTIN context or in a GLN context, but these contexts
are clearly distinguished.)

FIXME: NOTE THAT THE THIRTEEN-DIGIT ISMN AND THE CORRESPONDING 979-0
"MUSICLAND" PREFIX MAY NOT YET BE STANDARDIZED AS OF THIS WRITING.
'''

import re
import sys
import string
import time

def checkStandardModulo(base, digits, scale = 3):
    '''
    Return the standard modulo-BASE check digit integer for the given
    integer sequence ("digits") where every other digit is multiplied
    by the scale factor (three by default) while summing, and the
    check digit is the complement of the modulo-BASE sum.
    '''
    isum = 0
    for x in xrange(1, len(digits) + 1):
        isum = (isum + ((x % 2) and scale or 1) * digits[-x]) % base
        pass
    return (base - isum) % base

def checkPositionModulo(base, digits):
    '''
    Return the position-scaled modulo-BASE check digit integer for the
    given integer sequence ("digits") where each digit is multiplied
    by its position plus one, and the check-digit is the complement of
    the modulo-BASE sum.

    Note that rightmost digit in the sequence is multiplied by two,
    the next to the left by three, etc.
    '''
    isum = 0
    for x in xrange(1, len(digits) + 1):
        isum += ((x + 1) * digits[-x]) % base
        pass
    return (base - isum) % base

class GTIN(object):
    '''

    Global Trade Item Numbers (GTIN)

    Structure: 14 decimal digits with the last digit serving as a
    check digit.

    Valid GTIN formats (leading zeroes may be omitted on input):

    UPC/UCC-12:
    00hhhhhhiiiiic
    00hhhhhhhiiiic
    00hhhhhhhhiiic
    00hhhhhhhhhiic

    EAN/UCC-13:
    0nnnnnnnnnnnnc

    EAN/UCC-14:
    pnnnnnnnnnnnnc

    EAN/UCC-8:
    000000nnnnnnnc

    Key: p - indicator digit (used e.g. in layered packaging)
         h - UCC company prefix
         i - item reference number
         n - EAN/UCC company prefix and reference number
         c - check digit

    NOTE: EAN/UCC-8 is for use only outside the US and Canada, and is
    not to be confused with 8-digit UPC E/UPC-8, which is a compressed
    representation for UPC/UCC-12.

    NOTE: 8-digit UPC E/UPC-8 codes should be converted to UPC/UCC-12
    (UPC A) format before zero-filling and use as GTINs.

    The check digits are calculated by the standard modulo algorithm
    where every other digit is tripled while summing.

    NOTE: GTINs in the invalid/unassigned Bookland (ISBN) range
          p9786nnnnnnnnc are disallowed by this code and raise
          a ValueError.
    '''
    # FIXME: we permit non-zero-filled forms.
    gtin_re = re.compile(
        r'''
        \A
        (?:
        (?:
        (?:
        (?:
        (?:EAN|UPC|U[.]P[.]C[.]|(?:EAN[-./]?)UCC)
        (?:[- ]?12)?
        |
        (?:UPC|U[.]P[.]C[.])[ ]?A
        )
        :?
        [ ]?
        )?
        (?P<upc>\d{11})
        )
        |
        (?:
        (?:
        (?:EAN|JAN|IAN|DUN|(?:EAN[-./]?)UCC)
        (?:[- ]?13)?
        :?
        [ ]?
        )?
        (?P<ean>\d{12})
        )
        |
        (?:
        (?:
        (?:EAN|ITF|(?:EAN[-./]?)UCC)
        (?:[- ]?14)?
        :?
        [ ]?
        )?
        (?P<gtin>\d{13})
        )
        |
        (?:
        (?:
        (?:EAN|(?:EAN[-./]?)UCC)
        (?:[- ]?8)?
        :?
        [ ]?
        )?
        (?P<ean8>\d{7})
        )
        )
        (?P<gtincheck>\d)
        \Z
        ''',
        re.VERBOSE | re.UNICODE | re.IGNORECASE)
    # longest match wins
    systemcodes = {
        ## FIXME: is this really always correct? Need to check UCC registration info...
        '00': 'USA & Canada',
        '00000': 'EAN/UCC-8',
        '000000': 'reserved for internal use',
        '000002': 'reserved for internal use',
        '0001': 'reserved for internal use',
        '0002': 'reserved for internal use',
        '0003': 'reserved for internal use',
        '0004': 'reserved for internal use',
        '0005': 'reserved for internal use',
        '0006': 'reserved for internal use',
        '0007': 'reserved for internal use',
        '01': 'USA & Canada (formerly reserved)',
        '02': 'reserved for local use (store/warehouse); typically used for random-weight items',
        '03': 'USA & Canada (pharmaceuticals)',
        '04': 'reserved for local use (store/warehouse); typically used by retailers for in-store marking',
        '05': 'Coupons',
        '06': 'USA & Canada',
        '07': 'USA & Canada',
        '08': 'USA & Canada (formerly reserved)',
        '09': 'USA & Canada (formerly reserved)',
        '10': 'USA & Canada',
        '11': 'USA & Canada',
        '12': 'USA & Canada',
        '13': 'USA & Canada',
        '14': 'reserved (?)',
        '15': 'reserved (?)',
        '16': 'reserved (?)',
        '17': 'reserved (?)',
        '18': 'reserved (?)',
        '19': 'reserved (?)',
        '2': 'reserved for local use (store/warehouse)',
        '30': 'France',
        '31': 'France',
        '32': 'France',
        '33': 'France',
        '34': 'France',
        '35': 'France',
        '36': 'France',
        '37': 'France',
        '380': 'Bulgaria',
        '383': 'Slovenija',
        '385': 'Croatia',
        '387': 'BIH (Bosnia-Herzegovina)',
        '40': 'Germany',
        '41': 'Germany',
        '42': 'Germany',
        '43': 'Germany',
        '440': 'Germany',
        '45': 'Japan',
        '46': 'Russian Federation',
        '470': 'Kyrgyzstan',
        '471': 'Taiwan',
        '474': 'Estonia',
        '475': 'Latvia',
        '476': 'Azerbaijan',
        '477': 'Lithuania',
        '478': 'Uzbekistan',
        '479': 'Sri Lanka',
        '480': 'Philippines',
        '481': 'Belarus',
        '482': 'Ukraine',
        '484': 'Moldova',
        '485': 'Armenia',
        '486': 'Georgia',
        '487': 'Kazakhstan',
        '489': 'Hong Kong',
        '49': 'Japan',
        '50': 'UK',
        '520': 'Greece',
        '528': 'Lebanon',
        '529': 'Cyprus',
        '531': 'Macedonia',
        '535': 'Malta',
        '539': 'Ireland',
        '54': 'Belgium & Luxembourg',
        '560': 'Portugal',
        '569': 'Iceland',
        '57': 'Denmark',
        '590': 'Poland',
        '594': 'Romania',
        '599': 'Hungary',
        '600': 'South Africa',
        '601': 'South Africa',
        '608': 'Bahrain',
        '609': 'Mauritius',
        '611': 'Morocco',
        '613': 'Algeria',
        '619': 'Tunisia',
        '621': 'Syria',
        '622': 'Egypt',
        '624': 'Libya',
        '625': 'Jordan',
        '626': 'Iran',
        '627': 'Kuwait',
        '628': 'Saudi Arabia',
        '629': 'Emirates',
        '64': 'Finland',
        '690': 'China',
        '691': 'China',
        '692': 'China',
        '693': 'China',
        '694': 'China',
        '695': 'China',
        '70': 'Norway',
        '729': 'Israel',
        '73': 'Sweden',
        '740': 'Guatemala',
        '741': 'El Salvador',
        '742': 'Honduras',
        '744': 'Costa Rica',
        '745': 'Panama',
        '746': 'Republica Dominicana',
        '750': 'Mexico',
        '754': 'Canada',
        '755': 'Canada',
        '759': 'Venezuela',
        '76': 'Schweiz, Suisse, Svizzera',
        '770': 'Colombia',
        '773': 'Uruguay',
        '775': 'Peru',
        '777': 'Bolivia',
        '779': 'Argentina',
        '780': 'Chile',
        '784': 'Paraguay',
        '786': 'Ecuador',
        '789': 'Brasil',
        '790': 'Brasil',
        '80': 'Italy',
        '81': 'Italy',
        '82': 'Italy',
        '83': 'Italy',
        '84': 'Spain',
        '850': 'Cuba',
        '858': 'Slovakia',
        '859': 'Czech',
        '860': 'YU (Serbia & Montenegro)',
        '865': 'Mongolia',
        '867': 'North Korea',
        '869': 'Turkey',
        '87': 'Netherlands',
        '880': 'South Korea',
        '884': 'Cambodia',
        '885': 'Thailand',
        '888': 'Singapore',
        '890': 'India',
        '893': 'Vietnam',
        '899': 'Indonesia',
        '90': 'Austria',
        '91': 'Austria',
        '93': 'Australia',
        '94': 'New Zealand',
        '950': 'Head Office',
        '955': 'Malaysia',
        '958': 'Macau',
        '970': 'reserved (?)',
        '971': 'reserved (?)',
        '972': 'reserved (?)',
        '973': 'reserved (?)',
        '974': 'reserved (?)',
        '975': 'reserved (?)',
        '976': 'reserved (?)',
        '977': 'Serial publications (ISSN)',
        '978': 'Bookland (ISBN)',
        '9780': 'Bookland (ISBN): English speaking area: Australia, Canada (E.), Gibraltar, Ireland, (Namibia), New Zealand, Puerto Rico, South Africa, Swaziland, UK, USA, Zimbabwe',
        '9781': 'Bookland (ISBN): English speaking area: Australia, Canada (E.), Gibraltar, Ireland, (Namibia), New Zealand, Puerto Rico, South Africa, Swaziland, UK, USA, Zimbabwe',
        '9782': 'Bookland (ISBN): French speaking area: France, Belgium (Fr. sp.), Canada (Fr. sp.), Luxembourg, Switzerland (Fr. sp.)',
        '9783': 'Bookland (ISBN): German speaking area: Austria, Germany, Switzerland (Germ. sp.)',
        '9784': 'Bookland (ISBN): Japan',
        '9785': 'Bookland (ISBN): Russian Federation (Azerbaijan, Tajikistan, Turkmenistan, Uzbekistan, Armenia, Belarus, Estonia, Georgia, Kazakhstan, Kyrgyzstan, Latvia, Lithuania, Moldova, Ukraine)',
        '9786': 'Bookland (ISBN): UNDEFINED/INVALID',
        '9787': 'Bookland (ISBN): China, People\'s Republic',
        '97880': 'Bookland (ISBN): Czech Republic; Slovakia',
        '97881': 'Bookland (ISBN): India',
        '97882': 'Bookland (ISBN): Norway',
        '97883': 'Bookland (ISBN): Poland',
        '97884': 'Bookland (ISBN): Spain',
        '97885': 'Bookland (ISBN): Brazil',
        '97886': 'Bookland (ISBN): Serbia and Montenegro: Bosnia and Herzegovina, Croatia, Macedonia, Slovenia',
        '97887': 'Bookland (ISBN): Denmark',
        '97888': 'Bookland (ISBN): Italian speaking area: Italy, Switzerland (It. sp.)',
        '97889': 'Bookland (ISBN): Korea',
        '97890': 'Bookland (ISBN): Netherlands: Netherlands, Belgium (Flemish)',
        '97891': 'Bookland (ISBN): Sweden',
        '97892': 'Bookland (ISBN): International Publishers (Unesco, EU); European Community Organizations',
        '97893': 'Bookland (ISBN): India',
        '978950': 'Bookland (ISBN): Argentina',
        '978951': 'Bookland (ISBN): Finland',
        '978952': 'Bookland (ISBN): Finland',
        '978953': 'Bookland (ISBN): Croatia',
        '978954': 'Bookland (ISBN): Bulgaria',
        '978955': 'Bookland (ISBN): Sri Lanka',
        '978956': 'Bookland (ISBN): Chile',
        '978957': 'Bookland (ISBN): Taiwan, China',
        '978958': 'Bookland (ISBN): Colombia',
        '978959': 'Bookland (ISBN): Cuba',
        '978960': 'Bookland (ISBN): Greece',
        '978961': 'Bookland (ISBN): Slovenia',
        '978962': 'Bookland (ISBN): Hong Kong',
        '978963': 'Bookland (ISBN): Hungary',
        '978964': 'Bookland (ISBN): Iran',
        '978965': 'Bookland (ISBN): Israel',
        '978966': 'Bookland (ISBN): Ukraine',
        '978967': 'Bookland (ISBN): Malaysia',
        '978968': 'Bookland (ISBN): Mexico',
        '978969': 'Bookland (ISBN): Pakistan',
        '978970': 'Bookland (ISBN): Mexico',
        '978971': 'Bookland (ISBN): Philippines',
        '978972': 'Bookland (ISBN): Portugal',
        '978973': 'Bookland (ISBN): Romania',
        '978974': 'Bookland (ISBN): Thailand',
        '978975': 'Bookland (ISBN): Turkey',
        '978976': 'Bookland (ISBN): Caribbean Community: Antigua [AG], Bahamas [BS], Barbados [BB], Belize [BZ], Cayman Islands [KY], Dominica [DM], Grenada [GD], Guyana [GY], Jamaica [JM], Montserrat [MS], St. Kitts-Nevis [KN], St. Lucia [LC], St. Vincent and the Grenadines [VC], Trinidad and Tobago [TT], Virgin Islands (Br) [VG]',
        '978977': 'Bookland (ISBN): Egypt',
        '978978': 'Bookland (ISBN): Nigeria',
        '978979': 'Bookland (ISBN): Indonesia',
        '978980': 'Bookland (ISBN): Venezuela',
        '978981': 'Bookland (ISBN): Singapore',
        '978982': 'Bookland (ISBN): South Pacific: Cook Islands [CK], Fiji [FJ], Kiribati [KI], Marshall Islands [MH], Micronesia (Federal States of) [FM], Nauru [NR], New Caledonia [NC], Niue [NU], Palau [PW], Solomon Islands [SB], Tokelau [TK], Tonga [TO], Tuvalu [TV], Vanuatu [VU], Western Samoa [WS]',
        '978983': 'Bookland (ISBN): Malaysia',
        '978984': 'Bookland (ISBN): Bangladesh',
        '978985': 'Bookland (ISBN): Belarus',
        '978986': 'Bookland (ISBN): Taiwan, China',
        '978987': 'Bookland (ISBN): Argentina',
        '978988': 'Bookland (ISBN): Hong Kong',
        '978989': 'Bookland (ISBN): Portugal',
        '9789944': 'Bookland (ISBN): Turkey',
        '9789945': 'Bookland (ISBN): Dominican Republic',
        '9789946': 'Bookland (ISBN): Korea, P.D.R.',
        '9789947': 'Bookland (ISBN): Algeria',
        '9789948': 'Bookland (ISBN): United Arab Emirates',
        '9789949': 'Bookland (ISBN): Estonia',
        '9789950': 'Bookland (ISBN): Palestine',
        '9789951': 'Bookland (ISBN): Kosova',
        '9789952': 'Bookland (ISBN): Azerbaijan',
        '9789953': 'Bookland (ISBN): Lebanon',
        '9789954': 'Bookland (ISBN): Morocco',
        '9789955': 'Bookland (ISBN): Lithuania',
        '9789956': 'Bookland (ISBN): Cameroon',
        '9789957': 'Bookland (ISBN): Jordan',
        '9789958': 'Bookland (ISBN): Bosnia and Herzegovina',
        '9789959': 'Bookland (ISBN): Libya',
        '9789960': 'Bookland (ISBN): Saudi Arabia',
        '9789961': 'Bookland (ISBN): Algeria',
        '9789962': 'Bookland (ISBN): Panama',
        '9789963': 'Bookland (ISBN): Cyprus',
        '9789964': 'Bookland (ISBN): Ghana',
        '9789965': 'Bookland (ISBN): Kazakhstan',
        '9789966': 'Bookland (ISBN): Kenya',
        '9789967': 'Bookland (ISBN): Kyrgyzstan',
        '9789968': 'Bookland (ISBN): Costa Rica',
        '9789970': 'Bookland (ISBN): Uganda',
        '9789971': 'Bookland (ISBN): Singapore',
        '9789972': 'Bookland (ISBN): Peru',
        '9789973': 'Bookland (ISBN): Tunisia',
        '9789974': 'Bookland (ISBN): Uruguay',
        '9789975': 'Bookland (ISBN): Moldova',
        '9789976': 'Bookland (ISBN): Tanzania',
        '9789977': 'Bookland (ISBN): Costa Rica',
        '9789978': 'Bookland (ISBN): Ecuador',
        '9789979': 'Bookland (ISBN): Iceland',
        '9789980': 'Bookland (ISBN): Papua New Guinea',
        '9789981': 'Bookland (ISBN): Morocco',
        '9789982': 'Bookland (ISBN): Zambia',
        '9789983': 'Bookland (ISBN): Gambia',
        '9789984': 'Bookland (ISBN): Latvia',
        '9789985': 'Bookland (ISBN): Estonia',
        '9789986': 'Bookland (ISBN): Lithuania',
        '9789987': 'Bookland (ISBN): Tanzania',
        '9789988': 'Bookland (ISBN): Ghana',
        '9789989': 'Bookland (ISBN): Macedonia',
        '97899901': 'Bookland (ISBN): Bahrain',
        '97899902': 'Bookland (ISBN): Gabon',
        '97899903': 'Bookland (ISBN): Mauritius',
        '97899904': 'Bookland (ISBN): Netherlands Antilles; Aruba, Neth. Ant.',
        '97899905': 'Bookland (ISBN): Bolivia',
        '97899906': 'Bookland (ISBN): Kuwait',
        '97899908': 'Bookland (ISBN): Malawi',
        '97899909': 'Bookland (ISBN): Malta',
        '97899910': 'Bookland (ISBN): Sierra Leone',
        '97899911': 'Bookland (ISBN): Lesotho',
        '97899912': 'Bookland (ISBN): Botswana',
        '97899913': 'Bookland (ISBN): Andorra',
        '97899914': 'Bookland (ISBN): Suriname',
        '97899915': 'Bookland (ISBN): Maldives',
        '97899916': 'Bookland (ISBN): Namibia',
        '97899917': 'Bookland (ISBN): Brunei Darussalam',
        '97899918': 'Bookland (ISBN): Faroe Islands',
        '97899919': 'Bookland (ISBN): Benin',
        '97899920': 'Bookland (ISBN): Andorra',
        '97899921': 'Bookland (ISBN): Qatar',
        '97899922': 'Bookland (ISBN): Guatemala',
        '97899923': 'Bookland (ISBN): El Salvador',
        '97899924': 'Bookland (ISBN): Nicaragua',
        '97899925': 'Bookland (ISBN): Paraguay',
        '97899926': 'Bookland (ISBN): Honduras',
        '97899927': 'Bookland (ISBN): Albania',
        '97899928': 'Bookland (ISBN): Georgia',
        '97899929': 'Bookland (ISBN): Mongolia',
        '97899930': 'Bookland (ISBN): Armenia',
        '97899931': 'Bookland (ISBN): Seychelles',
        '97899932': 'Bookland (ISBN): Malta',
        '97899933': 'Bookland (ISBN): Nepal',
        '97899934': 'Bookland (ISBN): Dominican Republic',
        '97899935': 'Bookland (ISBN): Haiti',
        '97899936': 'Bookland (ISBN): Bhutan',
        '97899937': 'Bookland (ISBN): Macau',
        '97899938': 'Bookland (ISBN): Srpska',
        '97899939': 'Bookland (ISBN): Guatemala',
        '97899940': 'Bookland (ISBN): Georgia',
        '97899941': 'Bookland (ISBN): Armenia',
        '97899942': 'Bookland (ISBN): Sudan',
        '97899943': 'Bookland (ISBN): Albania',
        '97899944': 'Bookland (ISBN): Ethiopia',
        '97899945': 'Bookland (ISBN): Namibia',
        '97899946': 'Bookland (ISBN): Nepal',
        '97899947': 'Bookland (ISBN): Tajikistan',
        '97899948': 'Bookland (ISBN): Eritrea',
        '97899949': 'Bookland (ISBN): Mauritius',
        '97899950': 'Bookland (ISBN): Cambodia',
        '97899951': 'Bookland (ISBN): Congo',
        '97899952': 'Bookland (ISBN): Mali',
        '97899953': 'Bookland (ISBN): Paraguay', 
        '979': 'Bookland (ISBN)',
        '9790': 'Musicland (ISMN)',
        '980': 'Refund receipts',
        '981': 'Common Currency Coupons',
        '982': 'Common Currency Coupons',
        '99': 'Coupons',
    }
    packcodes = {
        '0': None,
        '1': 'conventionally more than individual and less than inner pack (primary code)',
        '2': 'conventionally more than individual and less than inner pack (alternate code)',
        '3': 'conventionally an inner pack (primary code)',
        '4': 'conventionally an inner pack (alternate code)',
        '5': 'conventionally a shipping container or carton (primary code)',
        '6': 'conventionally a shipping container or carton (alternate code)',
        '7': 'conventionally a shipping pallet',
        '8': 'code reserved for future use',
        '9': 'variable quantity content',
    }

    def __init__(self, s, public = True, autocorrect = False):
        '''
        Initialize a GTIN from a string ("s"); set the optional flag
        public = False if this GTIN is being used in an internal
        context where local use codes are allowed.. Set the optional
        flag autocorrect = True to replace the supplied check digit
        with the correct one rather than raising an exception when the
        check digit is not valid.

        Canonical forms (input and output):

        xxxxxxxxxxxxxy

        Short forms (input only):
        xxxxxxxxxxxy
        xxxxxxxxxxxxy
        xxxxxxxy

        Where x is a decimal digit and y is a decimal check
        digit. Whitespace and hyphens are stripped on input.
        '''
        if isinstance(s, GTIN): s = GTIN.__str__(s, short = True)
        self.public = public
        match = self.gtin_re.match(''.join(''.join(str(s).split()).split('-')))
        if not match: raise ValueError('invalid literal for %s.%s(): %r' % (GTIN.__module__, GTIN.__name__, s))
        self.gtin = (match.group('gtin') or match.group('ean') or match.group('upc') or match.group('ean8')).zfill(13)
        self.gtincheck = match.group('gtincheck')
        self.check(autocorrect = autocorrect)
        self.info = None
        self.pack = self.packcodes[self.gtin[0]]
        if self.gtin[0] == '8':
            raise ValueError('invalid literal for %s.%s(): %r (%s)' % (GTIN.__module__, GTIN.__name__, s, self.pack))
        for i in xrange(1, len(self.gtin)):
            key = self.gtin[1:][:-i]
            if key == '9786':
                raise ValueError('invalid literal for %s.%s(): %r (Bookland/ISBN reserved range)' % (GTIN.__module__, GTIN.__name__, s))
            if self.systemcodes.has_key(key):
                self.info = self.systemcodes[key]
                break
            if key[:5] == '00000' and self.systemcodes.has_key(key[5:]):
                self.info = self.systemcodes[key[5:]]
                break
            pass
        return
    def __cmp__(self, gtin):
        '''
        Compare this GTIN with another object, returning -1 if the
        other is greater than this one, 0 if the other is equal to
        this one, or 1 if the other is less than this one.
        '''
        if not isinstance(gtin, GTIN):
            raise TypeError('%s.%s.__cmp__(self, gtin) requires gtin to be a %s.%s, not a %s.%s' % (GTIN.__module__, GTIN.__name__, GTIN.__module__, GTIN.__name__, type(gtin).__module__, type(gtin).__name__))
        return cmp(GTIN.__str__(self), GTIN.__str__(gtin))
    def check(self, autocorrect = False):
        '''
        Verify the GTIN check digit. If it does not match, this raises
        a ValueError. The optional parameter autocorrect = True
        instead silently fixes the check digit.

        Also verifies that a non-public GTIN is not used in a public context.
        '''
        digits = self.gtin
        checkdigit = checkStandardModulo(10, [ int(ch, 10) for ch in digits ])
        if autocorrect: self.gtincheck = str(checkdigit)
        if int(self.gtincheck, 10) != checkdigit:
            raise ValueError('invalid check digit for GTIN %s: %s' % (self, self.gtincheck))
        # private codes (both EAN-8 and regular variants): restricted
        # distribution, coupons, refund receipts, common currency
        # coupons, packs thereof, and reserved ranges
        if ((self.gtin[1:9] in ('00000970', '00000971', '00000972', '00000973', '00000974', '00000975', '00000976')
             or self.gtin[1:8] in ('0000098', '0000099')
             or self.gtin[1:7] in ('000000', '000002')
             or self.gtin[1:5] in ('0001', '0002', '0003', '0004', '0005', '0006', '0007')
             or self.gtin[1:4] in ('970', '971', '972', '973', '974', '975', '976')
             or self.gtin[1:3] in ('02', '04', '05', '98', '99')
             or self.gtin[1:2] in ('2',)
             )
            and self.public):
            raise ValueError('non-public code in a public context for %s' % self)
        pass
    def __repr__(self): return '%s.%s(%r%s)' % (self.__class__.__module__, self.__class__.__name__, str(self), (not self.public) and ', public = False' or '')
    def __str__(self, short = False):
        '''
        Stringify a GTIN; the optional flag short = True currently has no effect
        '''
        o = []
        o.append(self.gtin)
        o.append(self.gtincheck)
        return ''.join(o)
    pass

class EAN14(GTIN):
    '''
    Handle EAN/UCC-14 as a wrapper class around GTIN
    '''
    def __init__(self, s, **kw):
        if not isinstance(s, GTIN):
            match = self.gtin_re.match(''.join(''.join(str(s).split()).split('-')))
            if not match or not match.group('gtin'): raise ValueError('invalid literal for %s.%s(): %r' % (EAN14.__module__, EAN14.__name__, s))
            pass
        GTIN.__init__(self, s, **kw)
        pass
    def __str__(self, short = False):
        '''
        Stringify an EAN/UCC-14; the optional flag short = True omits the EAN prefix
        '''
        o = []
        if not short: o.append('EAN ')
        o.append(self.gtin)
        o.append(self.gtincheck)
        return ''.join(o)
    pass

class EAN13(GTIN):
    '''
    Handle EAN/JAN/IAN/DUN/EAN.UCC-13 as a wrapper class around GTIN
    '''
    def __init__(self, s, **kw):
        if not isinstance(s, GTIN):
            match = self.gtin_re.match(''.join(''.join(str(s).split()).split('-')))
            if not match or not match.group('ean'): raise ValueError('invalid literal for %s.%s(): %r' % (EAN13.__module__, EAN13.__name__, s))
            pass
        GTIN.__init__(self, s, **kw)
        if self.gtin[0] != '0':
            raise ValueError('invalid literal for %s.%s(): %s' % (EAN13.__module__, EAN13.__name__, s))
        pass
    def __str__(self, short = False):
        '''
        Stringify an EAN/JAN/IAN/DUN/EAN.UCC-13; the optional flag short = True omits the EAN prefix
        '''
        o = []
        if not short: o.append('EAN ')
        o.append(self.gtin[1:])
        o.append(self.gtincheck)
        return ''.join(o)
    pass

class UPC12(GTIN):
    '''
    Handle UPC A/EAN/UPC/EAN.UCC-12 as a wrapper class around GTIN

    Not handled yet: price decoding for variable-quantity goods, e.g.
    209060 301694
    tare 0.010lb
    net wt. 2.450lb
    price/lb. $0.69/lb
    total price $1.69
    '''
    def __init__(self, s, **kw):
        if not isinstance(s, GTIN):
            match = self.gtin_re.match(''.join(''.join(str(s).split()).split('-')))
            if not match or not match.group('upc'): raise ValueError('invalid literal for %s.%s(): %r' % (UPC12.__module__, UPC12.__name__, s))
            pass
        GTIN.__init__(self, s, **kw)
        if self.gtin[:2] != '00':
            raise ValueError('invalid literal for %s.%s(): %s' % (UPC12.__module__, UPC12.__name__, s))
        pass
    def __str__(self, short = False):
        '''
        Stringify a UPC A/EAN/UPC/EAN.UCC-12; the optional flag short = True omits the UPC prefix
        '''
        o = []
        if not short: o.append('UPC ')
        o.append(self.gtin[2:])
        o.append(self.gtincheck)
        return ''.join(o)
    pass

class EAN8(GTIN):
    '''
    Handle EAN-8 as a wrapper class around GTIN
    '''
    def __init__(self, s, **kw):
        if not isinstance(s, GTIN):
            match = self.gtin_re.match(''.join(''.join(str(s).split()).split('-')))
            if not match or not match.group('ean8'): raise ValueError('invalid literal for %s.%s(): %r' % (EAN8.__module__, EAN8.__name__, s))
            pass
        GTIN.__init__(self, s, **kw)
        if self.gtin[:6] != '000000':
            raise ValueError('invalid literal for %s.%s(): %s' % (EAN8.__module__, EAN8.__name__, s))
        pass
    def __str__(self, short = False):
        '''
        Strigify a EAN-8; the optional flag short = True omits the EAN prefix
        '''
        o = []
        if not short: o.append('EAN ')
        o.append(self.gtin[6:])
        o.append(self.gtincheck)
        return ''.join(o)
    pass

upc8_re = re.compile(
    r'''
    \A
    (?:
    (?:UPC|U[.]P[.]C[.])(?:[- ]?[8E])?:?
    [ ]?
    )?
    (?P<upc8>0\d{6,6})
    (?P<upc8check>\d)
    \Z
    ''',
    re.VERBOSE | re.UNICODE | re.IGNORECASE)

def GTIN_from_UPC8(s, **kw):
    '''
    Return a GTIN object based on a UPC E/UPC-8 string.

    Whitespace and hyphens are ignored on input.
    '''
    if isinstance(s, GTIN): s = GTIN_to_UPC8(s)
    match = upc8_re.match(''.join(''.join(str(s).split()).split('-')))
    if not match: raise ValueError('invalid literal for %s.%s(): %r' % (GTIN_from_UPC8.__module__, GTIN_from_UPC8.__name__, s))
    upc8, upccheck = match.group('upc8'), match.group('upc8check')
    if upc8[-1] in '012': upc = upc8[:3] + upc8[-1] + '0000' + upc8[3:6]
    elif upc8[-1] == '3': upc = upc8[:4] + '00000' + upc8[4:6]
    elif upc8[-1] == '4': upc = upc8[:5] + '00000' + upc8[5:6]
    else: upc = upc8[:6] + '0000' + upc8[6:]
    return GTIN(upc + upccheck, **kw)

def GTIN_to_UPC8(gtin, short = False, **kw):
    '''
    Return a UPC E/UPC-8 string based on a GTIN object; the optional flag short = True omits the UPC prefix
    '''
    if not isinstance(gtin, GTIN): gtin = GTIN(str(gtin), **kw)
    gtin = GTIN.__str__(gtin, short = True)
    if gtin[:3] != '000': raise ValueError('invalid literal for %s.%s(): %r (manufacturer number too large for zero suppression)' % (GTIN_to_UPC8.__module__, GTIN_to_UPC8.__name__, gtin))
    prefix = (not short) and 'UPC ' or ''
    if (gtin[5] in '012') and gtin[6:][:4] == '0000': return prefix + gtin[2:][:3] + gtin[-4:][:3] + gtin[5] + gtin[-1]
    elif gtin[6:][:5] == '00000': return prefix + gtin[2:][:4] + gtin[-4:][:2] + '3' + gtin[-1]
    elif gtin[7:][:5] == '00000': return prefix + gtin[2:][:5] + gtin[-4] + '4' + gtin[-1]
    elif (gtin[12] in '56789') and gtin[8:][:4] == '0000': return prefix + gtin[2:][:6] + gtin[-2:]
    raise ValueError('invalid literal for %s.%s(): %r (item number too large for zero suppression)' % (GTIN_to_UPC8.__module__, GTIN_to_UPC8.__name__, gtin))

class UPC8(GTIN):
    '''
    Handle UPC E/UPC-8 as a subset of GTIN.
    '''
    def __init__(self, s, **kw):
        GTIN.__init__(self, GTIN_from_UPC8(s, **kw), **kw)
        pass
    __str__ = GTIN_to_UPC8
    pass

isbn_re = re.compile(
    r'''
    \A
    (?:
    (?:ISBN|International[ ]?Standard[ ]?Book[ ]?Number)(?:-?13)?:?
    [ ]?
    )?
    (?P<isbn13>
    (?P<isbn13prefix0>978)[- ]?
    (?:
    (?P<isbn13group0>[02-7])[- ]?
    (?:
    (?P<isbn13publisher0>[01]\d)[- ]?(?P<isbn13item0>\d{6,6})
    |
    (?P<isbn13publisher2>[2-6]\d\d)[- ]?(?P<isbn13item2>\d{5,5})
    |
    (?P<isbn13publisher4>(?:7\d|8[0-4])\d\d)[- ]?(?P<isbn13item4>\d{4,4})
    |
    (?P<isbn13publisher6>8[5-9]\d\d\d)[- ]?(?P<isbn13item6>\d\d\d)
    |
    (?P<isbn13publisher8>9[0-4]\d{4,4})[- ]?(?P<isbn13item8>\d\d)
    |
    (?P<isbn13publisher10>9[5-9]\d{5,5})[- ]?(?P<isbn13item10>\d)
    )
    |
    (?P<isbn13group1>1)[- ]?
    (?:
    (?P<isbn13publisher1>0\d)[- ]?(?P<isbn13item1>\d{6,6})
    |
    (?P<isbn13publisher3>[123]\d\d)[- ]?(?P<isbn13item3>\d{5,5})
    |
    (?P<isbn13publisher5>(?:4\d|5[0-4])\d\d)[- ]?(?P<isbn13item5>\d{4,4})
    |
    (?P<isbn13publisher7>(?:5[5-9]\d\d|[67]\d\d\d|8[0-5]\d\d|86[0-8]\d|869[0-7])\d)[- ]?(?P<isbn13item7>\d\d\d)
    |
    (?P<isbn13publisher9>(?:869[89]|8[789]\d\d|9[0-8]\d\d|99[0-8]\d)\d\d)[- ]?(?P<isbn13item9>\d\d)
    |
    (?P<isbn13publisher11>999\d{4,4})[- ]?(?P<isbn13item11>\d)
    )
    |
    (?P<isbn13group12>(?:8\d|9[0-4]))[- ]?(?P<isbn13opaque12>\d{7,7})
    |
    (?P<isbn13group13>(?:95\d|9[6-8]\d|99[0-3]))[- ]?(?P<isbn13opaque13>\d{6,6})
    |
    (?P<isbn13group14>99[4-8]\d)[- ]?(?P<isbn13opaque14>\d{5,5})
    |
    (?P<isbn13group15>999\d\d)[- ]?(?P<isbn13opaque15>\d{4,4})
    )
    |
    (?P<isbn13prefix16>979)[- ]?
    (?:
    (?P<isbn13group16>0)[- ]?
    (?:
    (?P<isbn13publisher16>0\d\d)[- ]?(?P<isbn13item16>\d{5,5})
    |
    (?P<isbn13publisher17>[1-3]\d\d\d)[- ]?(?P<isbn13item17>\d{4,4})
    |
    (?P<isbn13publisher18>[4-6]\d{4,4})[- ]?(?P<isbn13item18>\d\d\d)
    |
    (?P<isbn13publisher19>[78]\d{5,5})[- ]?(?P<isbn13item19>\d\d)
    |
    (?P<isbn13publisher20>9\d{6,6})[- ]?(?P<isbn13item20>\d)
    )
    |
    (?P<isbn13opaque21>[1-9]\d{8,8})
    )
    )
    (?P<isbn13check>\d)
    |
    (?:
    (?:
    (?:ISBN|International[ ]?Standard[ ]?Book[ ]?Number)(?:-?10)?:?
    [ ]?
    )?
    (?P<isbn10>
    (?P<isbn10group0>[02-7])[- ]?
    (?:
    (?P<isbn10publisher0>[01]\d)[- ]?(?P<isbn10item0>\d{6,6})
    |
    (?P<isbn10publisher2>[2-6]\d\d)[- ]?(?P<isbn10item2>\d{5,5})
    |
    (?P<isbn10publisher4>(?:7\d|8[0-4])\d\d)[- ]?(?P<isbn10item4>\d{4,4})
    |
    (?P<isbn10publisher6>8[5-9]\d\d\d)[- ]?(?P<isbn10item6>\d\d\d)
    |
    (?P<isbn10publisher8>9[0-4]\d{4,4})[- ]?(?P<isbn10item8>\d\d)
    |
    (?P<isbn10publisher10>9[5-9]\d{5,5})[- ]?(?P<isbn10item10>\d)
    )
    |
    (?P<isbn10group1>1)[- ]?
    (?:
    (?P<isbn10publisher1>0\d)[- ]?(?P<isbn10item1>\d{6,6})
    |
    (?P<isbn10publisher3>[123]\d\d)[- ]?(?P<isbn10item3>\d{5,5})
    |
    (?P<isbn10publisher5>(?:4\d|5[0-4])\d\d)[- ]?(?P<isbn10item5>\d{4,4})
    |
    (?P<isbn10publisher7>(?:5[5-9]\d\d|[67]\d\d\d|8[0-5]\d\d|86[0-8]\d|869[0-7])\d)[- ]?(?P<isbn10item7>\d\d\d)
    |
    (?P<isbn10publisher9>(?:869[89]|8[789]\d\d|9[0-8]\d\d|99[0-8]\d)\d\d)[- ]?(?P<isbn10item9>\d\d)
    |
    (?P<isbn10publisher11>999\d{4,4})[- ]?(?P<isbn10item11>\d)
    )
    |
    (?P<isbn10group12>(?:8\d|9[0-4]))[- ]?(?P<isbn10opaque12>\d{7,7})
    |
    (?P<isbn10group13>(?:9[5-8]\d|99[0-3]))[- ]?(?P<isbn10opaque13>\d{6,6})
    |
    (?P<isbn10group14>99[4-8]\d)[- ]?(?P<isbn10opaque14>\d{5,5})
    |
    (?P<isbn10group15>999\d\d)[- ]?(?P<isbn10opaque15>\d{4,4})
    )
    |
    (?:
    (?:SBN|Standard[ ]?Book[ ]?Number):?
    [ ]?
    )?
    (?P<sbn>
    (?P<sbnpublisher0>[01]\d)[- ]?(?P<sbnitem0>\d{6,6})
    |
    (?P<sbnpublisher2>[2-6]\d\d)[- ]?(?P<sbnitem2>\d{5,5})
    |
    (?P<sbnpublisher4>(?:7\d|8[0-4])\d\d)[- ]?(?P<sbnitem4>\d{4,4})
    |
    (?P<sbnpublisher6>8[5-9]\d\d\d)[- ]?(?P<sbnitem6>\d\d\d)
    |
    (?P<sbnpublisher8>9[0-4]\d{4,4})[- ]?(?P<sbnitem8>\d\d)
    |
    (?P<sbnpublisher10>9[5-9]\d{5,5})[- ]?(?P<sbnitem10>\d)
    )
    )
    (?P<isbn10check>[0-9X])
    \Z
    ''',
    re.UNICODE | re.VERBOSE | re.IGNORECASE)

def GTIN_from_ISBN(s, **kw):
    '''
    Construct a GTIN from a ten-digit or thirteen-digit International
    Standard Book Number (ISBN), ISO 2108. Older nine-digit Standard
    Book Numbers (SBNs) are supported too. The ten-digit form is
    sometimes referred to as ISBN-10 and the thirteet-digit form as
    Bookland EAN/ISBN-13.

    The optional parameter autocorrect = True corrects incorrect check
    digits or check characters; if omitted, an incorrect check digit
    or check character will raise a ValueError.

    Allowed formats:
    ISBN-13: 978xxxxxxxxxc
    ISBN-13: 979xxxxxxxxxc
    ISBN-10: xxxxxxxxxy
    SBN: xxxxxxxxy
    978xxxxxxxxxc
    979xxxxxxxxxc
    xxxxxxxxxy
    xxxxxxxxy

    NOTE: ISBN-10 or ISBN-13 may be abbreviated ISBN.

    NOTE: (I)SBN may be spelled out in full as (International)
          Standard Book Number.

    NOTE: Case is not significant and whitespace and hyphens are ignored.

    NOTE: The colon is optional.

    NOTE: There is an unassigned/invalid range of ISBNs:
          ISBN 978-6-xxxxxxxx-c,
        a.k.a ISBN 6-xxxxxxxx-c-y,
    Attempting to decode an ISBN in this range will result in a ValueError.

    Where: x is a decimal digit,
           y is a check character (0-9 or X) [checkPositionModulo],
       and c is a decimal check digit [checkStandardModulo].
    '''
    if isinstance(s, GTIN): s = GTIN_to_ISBN(s, **kw)
    match = isbn_re.match(''.join(''.join(s.split()).upper().split('-')))
    if not match: raise ValueError('invalid literal for %s.%s(): %r' % (GTIN_from_ISBN.__module__, GTIN_from_ISBN.__name__, s))
    isbn = (match.group('isbn13') or match.group('isbn10') or match.group('sbn')).zfill(9)
    isbncheck = (match.group('isbn13check') or match.group('isbn10check') or match.group('sbncheck'))
    if len(isbn) == 9:
        check = 'X'.join(('%x' % checkPositionModulo(11, [ int(digit, 11) for digit in 'A'.join(isbn.split('X')) ])).upper().split('A'))
        if kw.has_key('autocorrect') and kw['autocorrect']: isbncheck = check
        if isbncheck != check:
            raise ValueError('invalid check character for %s: %s' % (s, isbncheck))
        ean = GTIN('978' + isbn + '0', autocorrect = True)
        pass
    else:
        ean = isbn + isbncheck
        pass
    return GTIN(ean, **kw)

# FIXME: isbn13_override should be handled through assignment of a
# class alias instead...

# only change this while testing
isbn13_override = None

def GTIN_to_ISBN(gtin, short = False, isbn13 = None, **kw):
    '''
    Construct an International Standard Book Number (ISBN) from a
    GTIN.  If the optional flag isbn13 = True is provided, the result
    is always in ISBN-13 format; if the optional flag isbn13 = False
    is provided, the result will be in ISBN-10 format if possible; if
    the optional flag isbn13 = None is provided, the system clock will
    be checked and the effect will be equivalent to isbn13 = False
    before 2007-01-01 and isbn13 = True from that day onward. The
    optional flag short = True omits the "ISBN" prefix and hyphens.

    NOTE: Hyphens are placed in the appropriate places between group,
    publisher, and item in cases where these are known, and omitted
    otherwise. The subset of ISBN-13 corresponding to Musicland (ISMN)
    is hyphenated according to ISMN conventions.

    Returned ISBN-10 formats when flag isbn13 is False:
    ISBN x-xx-xxxxxx-y for ISBN range: [02-7]-[01]x-xxxxxx-y, 1-0x-xxxxxx-y
    ISBN x-xxx-xxxxx-y for ISBN range: [02-7]-[2-6]xx-xxxxx-y, 1-[123]xx-xxxxx-y
    ISBN x-xxxx-xxxx-y for ISBN range: [02-7]-(7x|8[0-4])xx-xxxx-y, 1-(4x|5[0-4])xx-xxxx-y
    ISBN x-xxxxx-xxx-y for ISBN range: [02-7]-8[5-9]xxx-xxx-y, 1-(5[5-9]xx|[67]xxx|8[0-5]xx|86[0-8]x|869[0-7])x-xxx-y
    ISBN x-xxxxxx-xx-y for ISBN range: [02-7]-9[0-4]xxxx-xx-y, 1-(869[89]|8[789]xx|9[0-8]xx|99[0-8]x)xx-xx-y
    ISBN x-xxxxxxx-x-y for ISBN range: [02-7]-9[5-9]xxxxx-x-y, 1-999xxxx-x-y
    ISBN xx-xxxxxxx-y for ISBN range: (8\d|9[0-4])-xxxxxxx-y
    ISBN xxx-xxxxxx-y for ISBN range: (9[5-8]x|99[0-3])-xxxxxx-y
    ISBN xxxx-xxxxx-y for ISBN range: 99[4-8]x-xxxxx-y
    ISBN xxxxx-xxxx-y for ISBN range: 999xx-xxxx-y

    Returned ISBN-13 formats when flag isbn13 is True:
    ISBN 978-x-xx-xxxxxx-c for Bookland (ISBN) range: 978-[02-7]-[01]x-xxxxxx-c, 978-1-0x-xxxxxx-c
    ISBN 978-x-xxx-xxxxx-c for Bookland (ISBN) range: 978-[02-7]-[2-6]xx-xxxxx-c, 978-1-[1-3]xx-xxxxx-c
    ISBN 978-x-xxxx-xxxx-c for Bookland (ISBN) range: 978-[02-7]-(7x|8[0-4])xx-xxxx-c, 978-1-(4x|5[0-4])xx-xxxx-c
    ISBN 978-x-xxxxx-xxx-c for Bookland (ISBN) range: 978-[02-7]-8[5-9]xxx-xxx-c, 978-1-(5[5-9]xx|[67]xxx|8[0-5]xx|86[0-8]x|869[0-7])x-xxx-c
    ISBN 978-x-xxxxxx-xx-c for Bookland (ISBN) range: 978-[02-7]-9[0-4]xxxx-xx-c, 978-1-(869[89]|8[7-9]xx|9[0-8]xx|99[0-8]x)xx-xx-c
    ISBN 978-x-xxxxxxx-x-c for Bookland (ISBN) range: 978-[02-7]-9[5-9]xxxxx-x-c, 978-1-999xxxx-x-c
    ISBN 978-xx-xxxxxxx-c for Bookland (ISBN) range: 978-(8\d|9[0-4])-xxxxxxx-c
    ISBN 978-xxx-xxxxxx-c for Bookland (ISBN) range: 978-(9[5-8]x|99[0-3])-xxxxxx-c
    ISBN 978-xxxx-xxxxx-c for Bookland (ISBN) range: 978-99[4-8]x-xxxxx-c
    ISBN 978-xxxxx-xxxx-c for Bookland (ISBN) range: 978-999xx-xxxx-c

    Returned ISBN-13 formats:
    ISBN 979-0-xxx-xxxxx-c for Musicland (ISMN) range 979-0-0xx-xxxxx-c
    ISBN 979-0-xxxx-xxxx-c for Musicland (ISMN) range 979-0-[123]xxx-xxxx-c
    ISBN 979-0-xxxxx-xxx-c for Musicland (ISMN) range 979-0-[456]xxxx-xxx-c
    ISBN 979-0-xxxxxx-xx-c for Musicland (ISMN) range 979-0-[78]xxxxx-xx-c
    ISBN 979-0-xxxxxxx-x-c for Musicland (ISMN) range 979-0-9xxxxxx-x-c
    ISBN 979-xxxxxxxxx-c for Bookland (ISBN) range: 979-[1-9]xxxxxxxx-c

    Where: x is a decimal digit,
           y is a check character (0-9 or X) [checkPositionModulo],
       and c is a decimal check digit [checkStandardModulo].
    '''
    if isbn13 is None: isbn13 = isbn13_override
    if isbn13 is None: isbn13 = time.gmtime()[0] >= 2007
    if not isinstance(gtin, GTIN): gtin = GTIN(str(gtin), **kw)
    gtin = GTIN.__str__(gtin, short = True)
    if gtin[:4] not in ('0978', '0979'):
        raise ValueError('invalid literal for %s.%s(): %r' % (GTIN_to_ISBN.__module__, GTIN_to_ISBN.__name__, gtin))
    if (gtin[:4] == '0978') and not isbn13:
        isbn = gtin[4:][:-1]
        isbn = 'ISBN ' + isbn + 'X'.join(('%x' % checkPositionModulo(11, [ int(digit, 11) for digit in 'A'.join(isbn.split('X')) ])).upper().split('A'))
    else: isbn = 'ISBN ' + gtin[1:]
    match = isbn_re.match(isbn)
    assert match is not None
    o = []
    if not short: o.append('ISBN ')
    parts = []
    for variety in ('isbn13', 'isbn10', 'sbn'):
        for partname in ('prefix', 'group', 'publisher', 'item', 'opaque', 'check'):
            for key, value in match.groupdict().iteritems():
                if key.startswith(variety + partname) and value is not None:
                    parts.append(value)
                    break
                pass
            pass
        if len(parts): break
        pass
    o.append(((not short) and '-' or '').join(parts))
    return ''.join(o)

class ISBN(GTIN):
    '''
    Handle ISBN as a subset of GTIN.

    Not handled yet: five-digit price code extension a.k.a. "UPC5",
    which are sometimes printed to the right of the EAN-13 barcode:

    UPC-5 (a.k.a. EAN/5 or EAN/9) format:

    daaaa>

    Where: d is the currency code,
       aaaaa is the amount,
       and > is the optional "quiet zone" character

    Examples:
       0xxxx =  Reserved (fromerly GBP xxxx)
       00000 =  No designated price (do not use)
       1xxxx =  USD 1xx.xx (formerly GBP xxxx)
       2xxxx =  USD 2xx.xx
       3xxxx =  USD 3xx.xx (formerly AUD xx.xx)
       4xxxx =  USD 4xx.xx (formerly NZD xx.xx)
       5xxxx =  USD  xx.xx
       50000 =  No designated price (do not use)
       59999 =  Price exceeds USD 99.98 (manual entry)
       6xxxx =  Ignored (formerly CAD xx.xx)
       7xxxx =  Ignored
       8xxxx =  Ignored
 90000-98999 =  Internal use range
       90000 =  No price specified (BISG recommended)
       99xxx =  Reserved for special use
       9999x =  Reserved for National Association of College Stores (NACS)
       99990 =  NACS used books
       99991 =  NACS desk copies/complimentary

    The barcode form encodes a UPC-like check digit (alternating
    weights 3 9 3 9 3) in the parity of the digits.

    In the ISBN format, the price is printed after the ISBN with two spaces:
    ISBN 0-425-05382-2  2.75
    '''
    def __init__(self, s, **kw):
        GTIN.__init__(self, GTIN_from_ISBN(s, **kw), **kw)
        pass
    __str__ = GTIN_to_ISBN
    pass

issn_re = re.compile(
    r'''
    \A
    ISSN:?
    [ ]?
    (?P<issn>
    \d{4,4}-?\d\d\d
    )
    (?P<issncheck>[0-9X])
    \Z
    ''',
    re.UNICODE | re.VERBOSE | re.IGNORECASE)

def GTIN_from_ISSN(s, **kw):
    '''
    Construct a GTIN from an eight-digit International Standard Serial
    Number (ISSN), ISO 3297.

    The optional parameter autocorrect = True corrects incorrect check
    characters; if omitted, an incorrect check character will raise a
    ValueError.

    Allowed format:
    ISSN: xxxx-xxxy

    NOTE: Case is not significant and whitespace and hyphens are ignored.

    NOTE: The colon is optional.

    Where: x is a decimal digit,
       and y is a check character (0-9 or X) [checkPositionModulo].
    '''
    if isinstance(s, GTIN): s = GTIN_to_ISSN(s)
    match = issn_re.match(''.join(''.join(s.split()).upper().split('-')))
    if not match: raise ValueError('invalid literal for %s.%s(): %r' % (GTIN_from_ISSN.__module__, GTIN_from_ISSN.__name__, s))
    issn = (match.group('issn')).zfill(7)
    issncheck = match.group('issncheck')
    check = 'X'.join(('%x' % checkPositionModulo(11, [ int(digit, 11) for digit in 'A'.join(issn.split('X')) ])).upper().split('A'))
    if kw.has_key('autocorrect') and kw['autocorrect']: issncheck = check
    if issncheck != check:
        raise ValueError('invalid check character for %s: %s' % (s, issncheck))
    kw['autocorrect'] = True
    return GTIN('977' + issn + '000', **kw)

def GTIN_to_ISSN(gtin, short = False, **kw):
    '''
    Construct an International Standard Serial Number (ISSN) from a
    GTIN. The optional flag short = True omits colon, space and hyphen.

    Returned format (without flag short = True):
    ISSN: xxxx-xxxy

    Returned format (with flag short = True):
    ISSNxxxxxxxy

    Where: x is a decimal digit,
       and y is a check character (0-9 or X) [checkPositionModulo].
    '''
    if not isinstance(gtin, GTIN): gtin = GTIN(str(gtin), **kw)
    gtin = GTIN.__str__(gtin, short = True)
    if gtin[:4] != '0977':
        raise ValueError('invalid literal for %s.%s(): %r' % (GTIN_to_ISSN.__module__, GTIN_to_ISSN.__name__, gtin))
    issn = gtin[4:][:-3]
    prefix, hyphen = (not short) and ('ISSN: ', '-') or ('ISSN', '')
    return prefix + issn[:4] + hyphen + issn[4:] + 'X'.join(('%x' % checkPositionModulo(11, [ int(digit, 11) for digit in 'A'.join(issn.split('X')) ])).upper().split('A'))

class ISSN(GTIN):
    '''
    Handle ISSN as a subset of GTIN.

    
    Not implemented yet: two-digit price code, written in the EAN
    right after the ISSN (currently fixed at 00); this is 00 for
    normal issues, other values for special issues, double issues,
    etc.

    Not implemented yet: publication issue number, a two- or
    five-digit add-on managed by the publisher, separated by a blank
    space from the EAN (which format and what meaning to assign to it
    varies by country.) For example, 03 might represent the March
    issue (third month of the year) for a monthly periodical.
    '''
    def __init__(self, s, **kw):
        GTIN.__init__(self, GTIN_from_ISSN(s, **kw), **kw)
        pass
    __str__ = GTIN_to_ISSN
    pass

ismn_re = re.compile(
    r'''
    \A
    (?:
    (?:
    (?:ISMN|International Standard Music Number)(?:-?10)?:?[ ]?
    )?
    (?P<prefix0>M)
    |
    (?:
    (?:ISMN|International Standard Music Number)(?:-?13)?:?[ ]?
    )?
    (?P<prefix1>979[- ]?0)
    )
    [- ]?
    (?P<ismn>
    0\d\d[- ]?\d{5,5}
    |
    [1-3]\d\d\d[- ]?\d{4,4}
    |
    [4-6]\d{4,4}[- ]?\d\d\d
    |
    [78]\d{5,5}[- ]?\d\d
    |
    9\d{6,6}[- ]?\d
    )
    [- ]?
    (?P<ismncheck>\d)
    \Z
    ''',
    re.UNICODE | re.VERBOSE | re.IGNORECASE)

ismn_publisher_length = [ 3, 4, 4, 4, 5, 5, 5, 6, 6, 7 ]

def GTIN_from_ISMN(s, **kw):
    '''
    Construct a GTIN from an eight-digit International Standard Music
    Number (ISMN), ISO 10957. Supports both the current 10-character
    ISMNs (ISMN-10) and the proposed 13-character EAN.UCC "Musicland"
    ISMNs (ISMN-13).

    The optional parameter autocorrect = True corrects incorrect check
    characters; if omitted, an incorrect check character will raise a
    ValueError.

    Allowed formats:
    ISMN     M-321-76543-6
    ISMN 979-0-123-45678-3
         |___| |_| |___| |
           P    P    I   C
           R    U    T   H
           E    B    E   E
           F    L    M   C
           I    I        K
           X    S
                H        D
                E        I
                R        G
                         I
                         T

    NOTE: ISMN may be spelled out in full as International Standard
          Music Number.

    NOTE: Case is not significant and whitespace and hyphens are
          interchangeable and optional.

    NOTE: A colon is allowed after ISMN on input but not generated on
          output.

    NOTE: The publisher and item are variable-length but combined they
          are always eight digits. The length of the publisher portion
          depends on the first digit as follows:

                0:  3 digits
          1, 2, 3:  4 digits
          4, 5, 6:  5 digits
             7, 8:  6 digits
                9:  7 digits
    '''
    if isinstance(s, GTIN): s = GTIN_to_ISMN(s)
    match = ismn_re.match(''.join(''.join(s.upper().split()).split('-')))
    if not match: raise ValueError('invalid literal for %s.%s(): %r' % (GTIN_from_ISMN.__module__, GTIN_from_ISMN.__name__, s))
    prefix = (match.group('prefix0') or match.group('prefix1')).upper()
    ismn = ''.join(''.join(match.group('ismn').split()).split('-'))
    split = ismn_publisher_length[int(ismn[0])]
    publisher, item = ismn[:split], ismn[split:]
    ismncheck = match.group('ismncheck')
    digits = '3' + ismn
    check = str(checkStandardModulo(10, [ int(digit) for digit in digits ]))
    if kw.has_key('autocorrect') and kw['autocorrect']: ismncheck = check
    if ismncheck != check:
        raise ValueError('invalid check character for %s: %s' % (s, ismncheck))
    ean = '9790' + ismn + ismncheck
    return GTIN(ean, **kw)

def GTIN_to_ISMN(gtin, short = False, **kw):
    '''
    Construct an International Standard Serial Number (ISMN) from a
    GTIN. The optional flag short = True omits the ISMN prefix and
    hyphens.

                0:  3 digits
          1, 2, 3:  4 digits
          4, 5, 6:  5 digits
             7, 8:  6 digits
                9:  7 digits

    Returned formats (without short = True):
    ISMN M-xxx-xxxxx-c
    ISMN M-xxxx-xxxx-c
    ISMN M-xxxxx-xxx-c
    ISMN M-xxxxxx-xx-c
    ISMN M-xxxxxxx-x-c

    Returned formats (with short = True):
    Mxxxxxxxxc

    Where: x is a decimal digit,
       and c is a decimal check digit [checkStandardModulo].
    '''
    if not isinstance(gtin, GTIN): gtin = GTIN(str(gtin), **kw)
    gtin = GTIN.__str__(gtin, short = True)
    if gtin[:5] != '09790':
        raise ValueError('invalid literal for %s.%s(): %r' % (GTIN_to_ISMN.__module__, GTIN_to_ISMN.__name__, gtin))
    ismn, ismncheck = gtin[5:-1], gtin[-1]
    split = ismn_publisher_length[int(ismn[0])]
    publisher, item = ismn[:split], ismn[split:]
    prefix, hyphen = (not short) and ('ISMN ', '-') or ('', '')
    return prefix + 'M' + hyphen + publisher + hyphen + item + hyphen + ismncheck

class ISMN(GTIN):
    '''
    Handle ISMN as a subset of GTIN.
    '''
    def __init__(self, s, **kw):
        GTIN.__init__(self, GTIN_from_ISMN(s, **kw), **kw)
        pass
    __str__ = GTIN_to_ISMN
    pass

def test():
    '''
    Self-tests for the GTIN module
    '''
    # test the standard modulo check digit calculator (positive tests)
    for base, digits, ck in (
        # UPC/UCC-12
        (10, '61414121022- ', 0),
        # EAN/UCC-13
        (10, '101454121022- ', 3),
        # EAN/UCC-14
        (10, '9101454121022- ', 6),
        # SSCC
        (10, '10614141192837465- ', 7),
        (10, '37610425002123456- ', 9),
        # BoL
        (10, '0614141192837465- ', 0),
        # EAN/UCC-8
        (10, '4321012- ', 1),
        ):
        try: assert checkStandardModulo(base, [ int(digit, 10) for digit in ''.join(''.join(digits.split()).split('-')) ]) == ck
        except:
            print 'checkStandardModulo failed for:'
            print ' base =', base
            print ' digits =', digits
            print ' ck =', ck
            raise
        pass
    # test the MOD a,b check digit calculator (negative tests)
    for base, digits, ck in (
        # UPC/UCC-12
        (10, '61414121022- ', 1),
        # EAN/UCC-13
        (10, '101454121022- ', 0),
        # EAN/UCC-14
        (10, '9101454121022- ', 4),
        # SSCC
        (10, '10614141192837465- ', 3),
        # BoL
        (10, '0614141192837465- ', 9),
        # EAN/UCC-8
        (10, '4321012- ', 2),
        ):
        try: assert checkStandardModulo(base, [ int(digit, 10) for digit in ''.join(''.join(digits.split()).split('-')) ]) != ck
        except:
            print 'checkStandardModulo failed for:'
            print ' base =', base
            print ' digits =', digits
            print ' ck =', ck
            raise
        pass
    # test the GTIN constructor (positive tests)
    for s in (
        '011594022019',
        '00614141210220',
        '01014541210223',
        '91014541210226',
        '00000043210121',
        '614141210220',
        '1014541210223',
        '43210121',
        '50285549',
        '0 48500 00102 8',
        '978-0-11-000222-4',
        ):
        try: GTIN(s)
        except:
            print 'GTIN failed for s =', s
            raise
        pass
    # test the GTIN constructor (negative tests)
    for s in (
        '00614141210221',
        '01014541210220',
        '91014541210224',
        '00000043210122',
        '614141210221',
        '1014541210220',
        '43210122',
        '000614141210220',
        '0001014541210223',
        '00091014541210226',
        '000000000043210121',
        '106141411928374657',
        '06141411928374650',
        '106141411928374653',
        '06141411928374659',
        '9786000000004',
        '81014541210229',
        ):
        try: GTIN(s)
        except ValueError, v: pass
        else:
            print 'GTIN should have failed for s =', s
            assert False
            pass
        pass
    # test the GTIN constructor and the GTIN str() implementation
    assert str(GTIN('91014541210226')) == '91014541210226'
    assert GTIN('91014541210226').__str__(short = True) == '91014541210226'
    assert str(GTIN('01014541210223')) == '01014541210223'
    assert GTIN('01014541210223').__str__(short = True) == '01014541210223'
    assert str(GTIN('00614141210220')) == '00614141210220'
    assert GTIN('00614141210220').__str__(short = True) == '00614141210220'
    assert str(GTIN('00000043210121')) == '00000043210121'
    assert GTIN('00000043210121').__str__(short = True) == '00000043210121'
    assert str(GTIN( '1014541210223')) == '01014541210223'
    assert GTIN( '1014541210223').__str__(short = True) == '01014541210223'
    assert str(GTIN(  '614141210220')) == '00614141210220'
    assert GTIN(  '614141210220').__str__(short = True) == '00614141210220'
    assert str(GTIN(      '43210121')) == '00000043210121'
    assert GTIN(      '43210121').__str__(short = True) == '00000043210121'
    # test the EAN14, EAN13, UPC12, and EAN8 wrapper classes
    assert str(EAN14('91014541210226')) == 'EAN 91014541210226'
    assert EAN14('91014541210226').__str__(short = True) == '91014541210226'
    assert str(EAN13( '1014541210223')) == 'EAN 1014541210223'
    assert EAN13( '1014541210223').__str__(short = True) == '1014541210223'
    assert str(UPC12(  '614141210220')) == 'UPC 614141210220'
    assert UPC12(  '614141210220').__str__(short = True) == '614141210220'
    assert str( EAN8(      '43210121')) == 'EAN 43210121'
    assert  EAN8(      '43210121').__str__(short = True) == '43210121'
    assert str(EAN14('EAN 91014541210226')) == 'EAN 91014541210226'
    assert EAN14('EAN 91014541210226').__str__(short = True) == '91014541210226'
    assert str(EAN13( 'EAN 1014541210223')) == 'EAN 1014541210223'
    assert EAN13( 'EAN 1014541210223').__str__(short = True) == '1014541210223'
    assert str(UPC12(  'UPC 614141210220')) == 'UPC 614141210220'
    assert UPC12(  'UPC 614141210220').__str__(short = True) == '614141210220'
    assert str( EAN8(      'EAN 43210121')) == 'EAN 43210121'
    assert  EAN8(      'EAN 43210121').__str__(short = True) == '43210121'
    # test the GTIN comparison implementation
    assert GTIN('91014541210226') == GTIN('91014541210226')
    assert GTIN('01014541210223') == GTIN('01014541210223')
    assert GTIN('00614141210220') == GTIN('00614141210220')
    assert GTIN('00000043210121') == GTIN('00000043210121')
    assert GTIN( '1014541210223') == GTIN('01014541210223')
    assert GTIN(  '614141210220') == GTIN('00614141210220')
    assert GTIN(      '43210121') == GTIN('00000043210121')
    assert GTIN(      '43210122', autocorrect = True) == GTIN('00000043210121')
    assert GTIN('91014541210226') > GTIN('01014541210223')
    assert GTIN('00000043210121') < GTIN('00614141210220')
    assert GTIN( '1014541210223') != GTIN('00614141210220')
    # test the GTIN check character autocorrection feature, stringification, and comparison
    for r, s in (
        ('91014541210226', '91014541210224'),
        ('01014541210223', '01014541210220'),
        ('00614141210220', '00614141210221'),
        ('00000043210121', '00000043210122'),
        ):
        assert GTIN(r) == GTIN(s, autocorrect = True)
        assert str(GTIN(r)) == str(GTIN(s, autocorrect = True))
        assert GTIN(r).__str__(short = True) == GTIN(s, autocorrect = True).__str__(short = True)
        pass
    # make sure comparisons between GTINs and non-GTINs raise a TypeError
    try: 
        tmp = GTIN('91014541210226') != '91014541210226'
        assert tmp;
    except TypeError, t: pass
    else: raise RuntimeError('comparison between GTIN and string should not work')
    try: 
        tmp = '01014541210223' != GTIN('01014541210223')
        assert tmp
    except TypeError, t: pass
    else: raise RuntimeError('comparison between GTIN and string should not work')
    # test accessors
    i = GTIN('01014541210223')
    assert i.gtin == '0101454121022'
    assert i.gtincheck == '3'
    # test whitespace and hyphen removal
    assert GTIN('0 48500 00102 8') == GTIN('00048500001028')
    # test UPC E/UPC-8 conversion
    assert GTIN_from_UPC8('01987913') == GTIN('00019100008793')
    assert GTIN_to_UPC8(GTIN('00019100008793')) == 'UPC 01987913'
    # test the UPC8 wrapper class
    assert UPC8('01987913') == GTIN('00019100008793')
    assert UPC8('UPC 01987913') == GTIN('00019100008793')
    assert str(UPC8('01987913')) == 'UPC 01987913'
    assert UPC8('01987913').__str__(short = True) == '01987913'
    # test ISBN conversion
    assert GTIN_from_ISBN('SBN 306-40615-2') == GTIN('0-978-0-306-40615-7')
    assert GTIN_from_ISBN('ISBN 5864551155') == GTIN('0-978-586455115-8')
    assert GTIN_from_ISBN('ISBN 3896254170') == GTIN('0-978-389625417-7')
    assert GTIN_from_ISBN('ISBN 3-89625-417-0') == GTIN('0-978-3-89625-417-7')
    assert GTIN_from_ISBN('ISBN 0-306-40615-2') == GTIN('0-978-0-306-40615-7')
    assert GTIN_from_ISBN('ISBN 0201530821') == GTIN('0-978-020153082-7')
    assert GTIN_from_ISBN('ISBN: 1-4028-9462-7') == GTIN('0-978-1-4028-9462-6')
    assert GTIN_from_ISBN('ISBN-10: 1-56619-909-3') == GTIN('0-978-1-56619-909-4')
    assert GTIN_from_ISBN('ISBN-13: 978-1-56619-909-4') == GTIN('0-978-1-56619-909-4')
    assert GTIN_from_ISBN('ISBN 0-553-57335-7') == GTIN('0-978-0-553-57335-0')
    assert GTIN_from_ISBN('306-40615-2') == GTIN('0-978-0-306-40615-7')
    assert GTIN_from_ISBN('5864551155') == GTIN('0-978-586455115-8')
    assert GTIN_from_ISBN('3896254170') == GTIN('0-978-389625417-7')
    assert GTIN_from_ISBN('3-89625-417-0') == GTIN('0-978-3-89625-417-7')
    assert GTIN_from_ISBN('0-306-40615-2') == GTIN('0-978-0-306-40615-7')
    assert GTIN_from_ISBN('0201530821') == GTIN('0-978-020153082-7')
    assert GTIN_from_ISBN('1-4028-9462-7') == GTIN('0-978-1-4028-9462-6')
    assert GTIN_from_ISBN('1-56619-909-3') == GTIN('0-978-1-56619-909-4')
    assert GTIN_from_ISBN('978-1-56619-909-4') == GTIN('0-978-1-56619-909-4')
    assert GTIN_from_ISBN('0-553-57335-7') == GTIN('0-978-0-553-57335-0')
    assert GTIN_from_ISBN('ISBN 0-937383-18-X') == GTIN('0-978-0937383-18-6')
    assert GTIN_from_ISBN('International Standard Book Number 0-8352-2051-6') == GTIN('09780835220514')
    assert GTIN_to_ISBN('0-978-0-306-40615-7', isbn13 = False) == 'ISBN 0-306-40615-2'
    assert GTIN_to_ISBN('0-978-586455115-8', isbn13 = False) == 'ISBN 5-86455-115-5'
    assert GTIN_to_ISBN('0-978-389625417-7', isbn13 = False) == 'ISBN 3-89625-417-0'
    assert GTIN_to_ISBN('0-978-3-89625-417-7', isbn13 = False) == 'ISBN 3-89625-417-0'
    assert GTIN_to_ISBN('0-978-0-306-40615-7', isbn13 = False) == 'ISBN 0-306-40615-2'
    assert GTIN_to_ISBN('0-978-020153082-7', isbn13 = False) == 'ISBN 0-201-53082-1'
    assert GTIN_to_ISBN('0-978-1-4028-9462-6', isbn13 = False) == 'ISBN 1-4028-9462-7'
    assert GTIN_to_ISBN('0-978-1-56619-909-4', isbn13 = False) == 'ISBN 1-56619-909-3'
    assert GTIN_to_ISBN('0-978-0-553-57335-0', isbn13 = False) == 'ISBN 0-553-57335-7'
    assert GTIN_to_ISBN('0-978-0937383-18-6', isbn13 = False) == 'ISBN 0-937383-18-X'
    assert GTIN_to_ISBN('09780835220514', isbn13 = False) == 'ISBN 0-8352-2051-6'
    assert GTIN_to_ISBN('0-978-0-306-40615-7', isbn13 = True) == 'ISBN 978-0-306-40615-7'
    assert GTIN_to_ISBN('0-978-586455115-8', isbn13 = True) == 'ISBN 978-5-86455-115-8'
    assert GTIN_to_ISBN('0-978-389625417-7', isbn13 = True) == 'ISBN 978-3-89625-417-7'
    assert GTIN_to_ISBN('0-978-3-89625-417-7', isbn13 = True) == 'ISBN 978-3-89625-417-7'
    assert GTIN_to_ISBN('0-978-0-306-40615-7', isbn13 = True) == 'ISBN 978-0-306-40615-7'
    assert GTIN_to_ISBN('0-978-020153082-7', isbn13 = True) == 'ISBN 978-0-201-53082-7'
    assert GTIN_to_ISBN('0-978-1-4028-9462-6', isbn13 = True) == 'ISBN 978-1-4028-9462-6'
    assert GTIN_to_ISBN('0-978-1-56619-909-4', isbn13 = True) == 'ISBN 978-1-56619-909-4'
    assert GTIN_to_ISBN('0-978-0-553-57335-0', isbn13 = True) == 'ISBN 978-0-553-57335-0'
    assert GTIN_to_ISBN('0-978-0937383-18-6', isbn13 = True) == 'ISBN 978-0-937383-18-6'
    assert GTIN_to_ISBN('09780835220514', isbn13 = True) == 'ISBN 978-0-8352-2051-4'
    # test the ISBN wrapper class
    assert ISBN('SBN 306-40615-2') == GTIN('0-978-0-306-40615-7')
    assert ISBN('ISBN 5864551155') == GTIN('0-978-586455115-8')
    assert ISBN('ISBN 3896254170') == GTIN('0-978-389625417-7')
    assert ISBN('ISBN 3-89625-417-0') == GTIN('0-978-3-89625-417-7')
    assert ISBN('ISBN 0-306-40615-2') == GTIN('0-978-0-306-40615-7')
    assert ISBN('ISBN 0201530821') == GTIN('0-978-020153082-7')
    assert ISBN('ISBN: 1-4028-9462-7') == GTIN('0-978-1-4028-9462-6')
    assert ISBN('ISBN-10: 1-56619-909-3') == GTIN('0-978-1-56619-909-4')
    assert ISBN('ISBN-13: 978-1-56619-909-4') == GTIN('0-978-1-56619-909-4')
    assert ISBN('ISBN 0-553-57335-7') == GTIN('0-978-0-553-57335-0')
    assert ISBN('ISBN 0-937383-18-X') == GTIN('0-978-0937383-18-6')
    assert ISBN('International Standard Book Number 0-8352-2051-6') == GTIN('09780835220514')
    global isbn13_override
    old_isbn13_override = isbn13_override
    try:
        # simulate operation before the 2007-01-01 switch to ISBN-13
        isbn13_override = False
        assert str(ISBN('ISBN 978-0-306-40615-7')) == 'ISBN 0-306-40615-2'
        assert ISBN('ISBN 978-0-306-40615-7').__str__(short = True) == '0306406152'
        assert str(ISBN('ISBN 978-586455115-8')) == 'ISBN 5-86455-115-5'
        assert ISBN('ISBN 978-586455115-8').__str__(short = True) == '5864551155'
        assert str(ISBN('ISBN 978-389625417-7')) == 'ISBN 3-89625-417-0'
        assert ISBN('ISBN 978-389625417-7').__str__(short = True) == '3896254170'
        assert str(ISBN('ISBN 978-3-89625-417-7')) == 'ISBN 3-89625-417-0'
        assert ISBN('ISBN 978-3-89625-417-7').__str__(short = True) == '3896254170'
        assert str(ISBN('ISBN 978-0-306-40615-7')) == 'ISBN 0-306-40615-2'
        assert ISBN('ISBN 978-0-306-40615-7').__str__(short = True) == '0306406152'
        assert str(ISBN('ISBN 978-020153082-7')) == 'ISBN 0-201-53082-1'
        assert ISBN('ISBN 978-020153082-7').__str__(short = True) == '0201530821'
        assert str(ISBN('ISBN 978-1-4028-9462-6')) == 'ISBN 1-4028-9462-7'
        assert ISBN('ISBN 978-1-4028-9462-6').__str__(short = True) == '1402894627'
        assert str(ISBN('ISBN 978-1-56619-909-4')) == 'ISBN 1-56619-909-3'
        assert ISBN('ISBN 978-1-56619-909-4').__str__(short = True) == '1566199093'
        assert str(ISBN('ISBN 978-0-553-57335-0')) == 'ISBN 0-553-57335-7'
        assert ISBN('ISBN 978-0-553-57335-0').__str__(short = True) == '0553573357'
        assert str(ISBN('ISBN 0-937383-18-X')) == 'ISBN 0-937383-18-X'
        assert ISBN('ISBN 0-937383-18-X').__str__(short = True) == '093738318X'
        assert str(ISBN('International Standard Book Number 0-8352-2051-6')) == 'ISBN 0-8352-2051-6'
        assert ISBN('International Standard Book Number 0-8352-2051-6').__str__(short = True) == '0835220516'

        # simulate operation after the 2007-01-01 switch to ISBN-13
        isbn13_override = True
        assert str(ISBN('ISBN 978-0-306-40615-7')) == 'ISBN 978-0-306-40615-7'
        assert ISBN('ISBN 978-0-306-40615-7').__str__(short = True) == '9780306406157'
        assert str(ISBN('ISBN 978-586455115-8')) == 'ISBN 978-5-86455-115-8'
        assert ISBN('ISBN 978-586455115-8').__str__(short = True) == '9785864551158'
        assert str(ISBN('ISBN 978-389625417-7')) == 'ISBN 978-3-89625-417-7'
        assert ISBN('ISBN 978-389625417-7').__str__(short = True) == '9783896254177'
        assert str(ISBN('ISBN 978-3-89625-417-7')) == 'ISBN 978-3-89625-417-7'
        assert ISBN('ISBN 978-3-89625-417-7').__str__(short = True) == '9783896254177'
        assert str(ISBN('ISBN 978-0-306-40615-7')) == 'ISBN 978-0-306-40615-7'
        assert ISBN('ISBN 978-0-306-40615-7').__str__(short = True) == '9780306406157'
        assert str(ISBN('ISBN 978-020153082-7')) == 'ISBN 978-0-201-53082-7'
        assert ISBN('ISBN 978-020153082-7').__str__(short = True) == '9780201530827'
        assert str(ISBN('ISBN 978-1-4028-9462-6')) == 'ISBN 978-1-4028-9462-6'
        assert ISBN('ISBN 978-1-4028-9462-6').__str__(short = True) == '9781402894626'
        assert str(ISBN('ISBN 978-1-56619-909-4')) == 'ISBN 978-1-56619-909-4'
        assert ISBN('ISBN 978-1-56619-909-4').__str__(short = True) == '9781566199094'
        assert str(ISBN('ISBN 978-0-553-57335-0')) == 'ISBN 978-0-553-57335-0'
        assert ISBN('ISBN 978-0-553-57335-0').__str__(short = True) == '9780553573350'
        assert str(ISBN('ISBN 0-937383-18-X')) == 'ISBN 978-0-937383-18-6'
        assert ISBN('ISBN 0-937383-18-X').__str__(short = True) == '9780937383186'
        assert str(ISBN('International Standard Book Number 0-8352-2051-6')) == 'ISBN 978-0-8352-2051-4'
        assert ISBN('International Standard Book Number 0-8352-2051-6').__str__(short = True) == '9780835220514'
        assert str(ISBN('ISBN 0-306-40615-2')) == 'ISBN 978-0-306-40615-7'
        assert ISBN('0306406152').__str__(short = True) == '9780306406157'
        assert str(ISBN('ISBN 5-86455-115-5')) == 'ISBN 978-5-86455-115-8'
        assert ISBN('5864551155').__str__(short = True) == '9785864551158'
        assert str(ISBN('ISBN 3-89625-417-0')) == 'ISBN 978-3-89625-417-7'
        assert ISBN('3896254170').__str__(short = True) == '9783896254177'
        assert str(ISBN('ISBN 3-89625-417-0')) == 'ISBN 978-3-89625-417-7'
        assert ISBN('3896254170').__str__(short = True) == '9783896254177'
        assert str(ISBN('ISBN 0-306-40615-2')) == 'ISBN 978-0-306-40615-7'
        assert ISBN('0306406152').__str__(short = True) == '9780306406157'
        assert str(ISBN('ISBN 0-201-53082-1')) == 'ISBN 978-0-201-53082-7'
        assert ISBN('0201530821').__str__(short = True) == '9780201530827'
        assert str(ISBN('ISBN 1-4028-9462-7')) == 'ISBN 978-1-4028-9462-6'
        assert ISBN('1402894627').__str__(short = True) == '9781402894626'
        assert str(ISBN('ISBN 1-56619-909-3')) == 'ISBN 978-1-56619-909-4'
        assert ISBN('1566199093').__str__(short = True) == '9781566199094'
        assert str(ISBN('ISBN 0-553-57335-7')) == 'ISBN 978-0-553-57335-0'
        assert ISBN('0553573357').__str__(short = True) == '9780553573350'
    finally:
        isbn13_override = old_isbn13_override
    # test ISSN conversion
    assert GTIN_from_ISSN('ISSN 0953-4563') == GTIN('09770953456001')
    assert GTIN_to_ISSN('09770953456001') == 'ISSN: 0953-4563'
    # test the ISSN wrapper class
    assert ISSN('ISSN: 0953-4563') == GTIN('09770953456001')
    assert str(ISSN('ISSN: 0953-4563')) == 'ISSN: 0953-4563'
    assert ISSN('ISSN: 0953-4563').__str__(short = True) == 'ISSN09534563'
    assert ISSN('ISSN: 1304-2386') == GTIN('09771304238000')
    assert str(ISSN('ISSN: 1304-2386')) == 'ISSN: 1304-2386'
    assert ISSN('ISSN: 1304-2386').__str__(short = True) == 'ISSN13042386'
    assert ISSN('ISSN 0953-4563') == GTIN('09770953456001')
    assert str(ISSN('ISSN 0953-4563')) == 'ISSN: 0953-4563'
    assert ISSN('ISSN 0953-4563').__str__(short = True) == 'ISSN09534563'
    assert ISSN('ISSN 1304-2386') == GTIN('09771304238000')
    assert str(ISSN('ISSN 1304-2386')) == 'ISSN: 1304-2386'
    assert ISSN('ISSN 1304-2386').__str__(short = True) == 'ISSN13042386'
    assert ISSN('issn: 0953-4563') == GTIN('09770953456001')
    assert str(ISSN('issn: 0953-4563')) == 'ISSN: 0953-4563'
    assert ISSN('issn: 0953-4563').__str__(short = True) == 'ISSN09534563'
    assert ISSN('issn: 1304-2386') == GTIN('09771304238000')
    assert str(ISSN('issn: 1304-2386')) == 'ISSN: 1304-2386'
    assert ISSN('issn: 1304-2386').__str__(short = True) == 'ISSN13042386'
    assert ISSN('issn 0953-4563') == GTIN('09770953456001')
    assert str(ISSN('issn 0953-4563')) == 'ISSN: 0953-4563'
    assert ISSN('issn 0953-4563').__str__(short = True) == 'ISSN09534563'
    assert ISSN('issn 1304-2386') == GTIN('09771304238000')
    assert str(ISSN('issn 1304-2386')) == 'ISSN: 1304-2386'
    assert ISSN('issn 1304-2386').__str__(short = True) == 'ISSN13042386'
    # test ISMN conversion
    assert GTIN_from_ISMN('M-571-10051-3') == GTIN('979-0-571-10051-3')
    assert GTIN_from_ISMN('ISMN M-706700-00-7') == GTIN('9790706700007')
    assert GTIN_from_ISMN('9790345123458') == GTIN('9790345123458')
    assert GTIN_from_ISMN('ismn-10: m 299102349') == GTIN('0 979 0 299102349')
    assert GTIN_from_ISMN('ismn-10: m 299102349') == GTIN('09790299102349')
    assert GTIN_from_ISMN('ISMN-10 M 299102349') == GTIN('0 979 0 299102349')
    assert GTIN_from_ISMN('ISMN-10 M 299102349') == GTIN('09790299102349')
    assert GTIN_from_ISMN('ISMN-10: M 299102349') == GTIN('0 979 0 299102349')
    assert GTIN_from_ISMN('ISMN-10: M 299102349') == GTIN('09790299102349')
    assert GTIN_from_ISMN('ismn-10: m-321-76543-6') == GTIN('0-979-0-321-76543-6')
    assert GTIN_from_ISMN('ISMN-10 M-321-76543-6') == GTIN('0-979-0-321-76543-6')
    assert GTIN_from_ISMN('ISMN-10: M-321-76543-6') == GTIN('0-979-0-321-76543-6')
    assert GTIN_from_ISMN('ismn-10: m-321-76544-3') == GTIN('0-979-0-321-76544-3')
    assert GTIN_from_ISMN('ISMN-10 M-321-76544-3') == GTIN('0-979-0-321-76544-3')
    assert GTIN_from_ISMN('ISMN-10: M-321-76544-3') == GTIN('0-979-0-321-76544-3')
    assert GTIN_from_ISMN('ismn-10: m-321-76545-0') == GTIN('0-979-0-321-76545-0')
    assert GTIN_from_ISMN('ISMN-10 M-321-76545-0') == GTIN('0-979-0-321-76545-0')
    assert GTIN_from_ISMN('ISMN-10: M-321-76545-0') == GTIN('0-979-0-321-76545-0')
    assert GTIN_from_ISMN('ismn-10: m-321-76546-7') == GTIN('0-979-0-321-76546-7')
    assert GTIN_from_ISMN('ISMN-10 M-321-76546-7') == GTIN('0-979-0-321-76546-7')
    assert GTIN_from_ISMN('ISMN-10: M-321-76546-7') == GTIN('0-979-0-321-76546-7')
    assert GTIN_from_ISMN('ismn-10: m-321-76547-4') == GTIN('0-979-0-321-76547-4')
    assert GTIN_from_ISMN('ISMN-10 M-321-76547-4') == GTIN('0-979-0-321-76547-4')
    assert GTIN_from_ISMN('ISMN-10: M-321-76547-4') == GTIN('0-979-0-321-76547-4')
    assert GTIN_from_ISMN('ismn-10: m-321-76548-1') == GTIN('0-979-0-321-76548-1')
    assert GTIN_from_ISMN('ISMN-10 M-321-76548-1') == GTIN('0-979-0-321-76548-1')
    assert GTIN_from_ISMN('ISMN-10: M-321-76548-1') == GTIN('0-979-0-321-76548-1')
    assert GTIN_from_ISMN('ismn-10: m-321-76549-8') == GTIN('0-979-0-321-76549-8')
    assert GTIN_from_ISMN('ISMN-10 M-321-76549-8') == GTIN('0-979-0-321-76549-8')
    assert GTIN_from_ISMN('ISMN-10: M-321-76549-8') == GTIN('0-979-0-321-76549-8')
    assert GTIN_from_ISMN('ismn-10: m-321-76550-4') == GTIN('0-979-0-321-76550-4')
    assert GTIN_from_ISMN('ISMN-10 M-321-76550-4') == GTIN('0-979-0-321-76550-4')
    assert GTIN_from_ISMN('ISMN-10: M-321-76550-4') == GTIN('0-979-0-321-76550-4')
    assert GTIN_from_ISMN('ismn-10: m-321-76551-1') == GTIN('0-979-0-321-76551-1')
    assert GTIN_from_ISMN('ISMN-10 M-321-76551-1') == GTIN('0-979-0-321-76551-1')
    assert GTIN_from_ISMN('ISMN-10: M-321-76551-1') == GTIN('0-979-0-321-76551-1')
    assert GTIN_from_ISMN('ismn-10: m-345-12345-8') == GTIN('0-979-0-345-12345-8')
    assert GTIN_from_ISMN('ISMN-10 M-345-12345-8') == GTIN('0-979-0-345-12345-8')
    assert GTIN_from_ISMN('ISMN-10: M-345-12345-8') == GTIN('0-979-0-345-12345-8')
    assert GTIN_from_ISMN('ismn-13: 979 0 123 45678 5') == GTIN('0 979 0 123 45678 5')
    assert GTIN_from_ISMN('ismn-13: 979-0-123-45678-5') == GTIN('0-979-0-123-45678-5')
    assert GTIN_from_ISMN('ISMN-13 979 0 123 45678 5') == GTIN('0 979 0 123 45678 5')
    assert GTIN_from_ISMN('ISMN-13 979-0-123-45678-5') == GTIN('0-979-0-123-45678-5')
    assert GTIN_from_ISMN('ISMN-13: 979 0 123 45678 5') == GTIN('0 979 0 123 45678 5')
    assert GTIN_from_ISMN('ISMN-13: 979-0-123-45678-5') == GTIN('0-979-0-123-45678-5')
    assert GTIN_from_ISMN('ismn: 979 0 123 45678 5') == GTIN('0 979 0 123 45678 5')
    assert GTIN_from_ISMN('ismn: 979-0-123-45678-5') == GTIN('0-979-0-123-45678-5')
    assert GTIN_from_ISMN('ISMN 979 0 123 45678 5') == GTIN('0 979 0 123 45678 5')
    assert GTIN_from_ISMN('ISMN 979-0-123-45678-5') == GTIN('0-979-0-123-45678-5')
    assert GTIN_from_ISMN('ISMN: 979 0 123 45678 5') == GTIN('0 979 0 123 45678 5')
    assert GTIN_from_ISMN('ISMN: 979-0-123-45678-5') == GTIN('0-979-0-123-45678-5')
    assert GTIN_from_ISMN('ismn: m 299102349') == GTIN('0 979 0 299102349')
    assert GTIN_from_ISMN('ismn: m 299102349') == GTIN('09790299102349')
    assert GTIN_from_ISMN('ISMN M 299102349') == GTIN('0 979 0 299102349')
    assert GTIN_from_ISMN('ISMN M 299102349') == GTIN('09790299102349')
    assert GTIN_from_ISMN('ISMN: M 299102349') == GTIN('0 979 0 299102349')
    assert GTIN_from_ISMN('ISMN: M 299102349') == GTIN('09790299102349')
    assert GTIN_from_ISMN('ismn: m-321-76543-6') == GTIN('0-979-0-321-76543-6')
    assert GTIN_from_ISMN('ISMN M-321-76543-6') == GTIN('0-979-0-321-76543-6')
    assert GTIN_from_ISMN('ISMN: M-321-76543-6') == GTIN('0-979-0-321-76543-6')
    assert GTIN_from_ISMN('ismn: m-321-76544-3') == GTIN('0-979-0-321-76544-3')
    assert GTIN_from_ISMN('ISMN M-321-76544-3') == GTIN('0-979-0-321-76544-3')
    assert GTIN_from_ISMN('ISMN: M-321-76544-3') == GTIN('0-979-0-321-76544-3')
    assert GTIN_from_ISMN('ismn: m-321-76545-0') == GTIN('0-979-0-321-76545-0')
    assert GTIN_from_ISMN('ISMN M-321-76545-0') == GTIN('0-979-0-321-76545-0')
    assert GTIN_from_ISMN('ISMN: M-321-76545-0') == GTIN('0-979-0-321-76545-0')
    assert GTIN_from_ISMN('ismn: m-321-76546-7') == GTIN('0-979-0-321-76546-7')
    assert GTIN_from_ISMN('ISMN M-321-76546-7') == GTIN('0-979-0-321-76546-7')
    assert GTIN_from_ISMN('ISMN: M-321-76546-7') == GTIN('0-979-0-321-76546-7')
    assert GTIN_from_ISMN('ismn: m-321-76547-4') == GTIN('0-979-0-321-76547-4')
    assert GTIN_from_ISMN('ISMN M-321-76547-4') == GTIN('0-979-0-321-76547-4')
    assert GTIN_from_ISMN('ISMN: M-321-76547-4') == GTIN('0-979-0-321-76547-4')
    assert GTIN_from_ISMN('ismn: m-321-76548-1') == GTIN('0-979-0-321-76548-1')
    assert GTIN_from_ISMN('ISMN M-321-76548-1') == GTIN('0-979-0-321-76548-1')
    assert GTIN_from_ISMN('ISMN: M-321-76548-1') == GTIN('0-979-0-321-76548-1')
    assert GTIN_from_ISMN('ismn: m-321-76549-8') == GTIN('0-979-0-321-76549-8')
    assert GTIN_from_ISMN('ISMN M-321-76549-8') == GTIN('0-979-0-321-76549-8')
    assert GTIN_from_ISMN('ISMN: M-321-76549-8') == GTIN('0-979-0-321-76549-8')
    assert GTIN_from_ISMN('ismn: m-321-76550-4') == GTIN('0-979-0-321-76550-4')
    assert GTIN_from_ISMN('ISMN M-321-76550-4') == GTIN('0-979-0-321-76550-4')
    assert GTIN_from_ISMN('ISMN: M-321-76550-4') == GTIN('0-979-0-321-76550-4')
    assert GTIN_from_ISMN('ismn: m-321-76551-1') == GTIN('0-979-0-321-76551-1')
    assert GTIN_from_ISMN('ISMN M-321-76551-1') == GTIN('0-979-0-321-76551-1')
    assert GTIN_from_ISMN('ISMN: M-321-76551-1') == GTIN('0-979-0-321-76551-1')
    assert GTIN_from_ISMN('ismn: m-345-12345-8') == GTIN('0-979-0-345-12345-8')
    assert GTIN_from_ISMN('ISMN M-345-12345-8') == GTIN('0-979-0-345-12345-8')
    assert GTIN_from_ISMN('ISMN: M-345-12345-8') == GTIN('0-979-0-345-12345-8')
    assert GTIN_from_ISMN('m345123458') == GTIN('9790345123458')
    assert GTIN_from_ISMN('M345123458') == GTIN('9790345123458')
    assert GTIN_to_ISMN('0 979 0 123 45678 5') == 'ISMN M-1234-5678-5'
    assert GTIN_to_ISMN('0-979-0-123-45678-5') == 'ISMN M-1234-5678-5'
    assert GTIN_to_ISMN('0 979 0 299102349') == 'ISMN M-2991-0234-9'
    assert GTIN_to_ISMN('09790299102349') == 'ISMN M-2991-0234-9'
    assert GTIN_to_ISMN('0-979-0-321-76543-6') == 'ISMN M-3217-6543-6'
    assert GTIN_to_ISMN('0-979-0-321-76544-3') == 'ISMN M-3217-6544-3'
    assert GTIN_to_ISMN('0-979-0-321-76545-0') == 'ISMN M-3217-6545-0'
    assert GTIN_to_ISMN('0-979-0-321-76546-7') == 'ISMN M-3217-6546-7'
    assert GTIN_to_ISMN('0-979-0-321-76547-4') == 'ISMN M-3217-6547-4'
    assert GTIN_to_ISMN('0-979-0-321-76548-1') == 'ISMN M-3217-6548-1'
    assert GTIN_to_ISMN('0-979-0-321-76549-8') == 'ISMN M-3217-6549-8'
    assert GTIN_to_ISMN('0-979-0-321-76550-4') == 'ISMN M-3217-6550-4'
    assert GTIN_to_ISMN('0-979-0-321-76551-1') == 'ISMN M-3217-6551-1'
    assert GTIN_to_ISMN('0-979-0-345-12345-8') == 'ISMN M-3451-2345-8'
    assert GTIN_to_ISMN('9790345123458') == 'ISMN M-3451-2345-8'
    # test the ISMN wrapper class
    assert ISMN('M-571-10051-3') == GTIN('979-0-571-10051-3')
    assert ISMN('ISMN M-706700-00-7') == GTIN('9790706700007')
    assert ISMN('9790345123458') == GTIN('9790345123458')
    assert ISMN('ismn-10: m 299102349') == GTIN('0 979 0 299102349')
    assert ISMN('ismn-10: m 299102349') == GTIN('09790299102349')
    assert ISMN('ISMN-10 M 299102349') == GTIN('0 979 0 299102349')
    assert ISMN('ISMN-10 M 299102349') == GTIN('09790299102349')
    assert ISMN('ISMN-10: M 299102349') == GTIN('0 979 0 299102349')
    assert ISMN('ISMN-10: M 299102349') == GTIN('09790299102349')
    assert ISMN('ismn-10: m-321-76543-6') == GTIN('0-979-0-321-76543-6')
    assert ISMN('ISMN-10 M-321-76543-6') == GTIN('0-979-0-321-76543-6')
    assert ISMN('ISMN-10: M-321-76543-6') == GTIN('0-979-0-321-76543-6')
    assert ISMN('ismn-10: m-321-76544-3') == GTIN('0-979-0-321-76544-3')
    assert ISMN('ISMN-10 M-321-76544-3') == GTIN('0-979-0-321-76544-3')
    assert ISMN('ISMN-10: M-321-76544-3') == GTIN('0-979-0-321-76544-3')
    assert ISMN('ismn-10: m-321-76545-0') == GTIN('0-979-0-321-76545-0')
    assert ISMN('ISMN-10 M-321-76545-0') == GTIN('0-979-0-321-76545-0')
    assert ISMN('ISMN-10: M-321-76545-0') == GTIN('0-979-0-321-76545-0')
    assert ISMN('ismn-10: m-321-76546-7') == GTIN('0-979-0-321-76546-7')
    assert ISMN('ISMN-10 M-321-76546-7') == GTIN('0-979-0-321-76546-7')
    assert ISMN('ISMN-10: M-321-76546-7') == GTIN('0-979-0-321-76546-7')
    assert ISMN('ismn-10: m-321-76547-4') == GTIN('0-979-0-321-76547-4')
    assert ISMN('ISMN-10 M-321-76547-4') == GTIN('0-979-0-321-76547-4')
    assert ISMN('ISMN-10: M-321-76547-4') == GTIN('0-979-0-321-76547-4')
    assert ISMN('ismn-10: m-321-76548-1') == GTIN('0-979-0-321-76548-1')
    assert ISMN('ISMN-10 M-321-76548-1') == GTIN('0-979-0-321-76548-1')
    assert ISMN('ISMN-10: M-321-76548-1') == GTIN('0-979-0-321-76548-1')
    assert ISMN('ismn-10: m-321-76549-8') == GTIN('0-979-0-321-76549-8')
    assert ISMN('ISMN-10 M-321-76549-8') == GTIN('0-979-0-321-76549-8')
    assert ISMN('ISMN-10: M-321-76549-8') == GTIN('0-979-0-321-76549-8')
    assert ISMN('ismn-10: m-321-76550-4') == GTIN('0-979-0-321-76550-4')
    assert ISMN('ISMN-10 M-321-76550-4') == GTIN('0-979-0-321-76550-4')
    assert ISMN('ISMN-10: M-321-76550-4') == GTIN('0-979-0-321-76550-4')
    assert ISMN('ismn-10: m-321-76551-1') == GTIN('0-979-0-321-76551-1')
    assert ISMN('ISMN-10 M-321-76551-1') == GTIN('0-979-0-321-76551-1')
    assert ISMN('ISMN-10: M-321-76551-1') == GTIN('0-979-0-321-76551-1')
    assert ISMN('ismn-10: m-345-12345-8') == GTIN('0-979-0-345-12345-8')
    assert ISMN('ISMN-10 M-345-12345-8') == GTIN('0-979-0-345-12345-8')
    assert ISMN('ISMN-10: M-345-12345-8') == GTIN('0-979-0-345-12345-8')
    assert ISMN('ismn-13: 979 0 123 45678 5') == GTIN('0 979 0 123 45678 5')
    assert ISMN('ismn-13: 979-0-123-45678-5') == GTIN('0-979-0-123-45678-5')
    assert ISMN('ISMN-13 979 0 123 45678 5') == GTIN('0 979 0 123 45678 5')
    assert ISMN('ISMN-13 979-0-123-45678-5') == GTIN('0-979-0-123-45678-5')
    assert ISMN('ISMN-13: 979 0 123 45678 5') == GTIN('0 979 0 123 45678 5')
    assert ISMN('ISMN-13: 979-0-123-45678-5') == GTIN('0-979-0-123-45678-5')
    assert ISMN('ismn: 979 0 123 45678 5') == GTIN('0 979 0 123 45678 5')
    assert ISMN('ismn: 979-0-123-45678-5') == GTIN('0-979-0-123-45678-5')
    assert ISMN('ISMN 979 0 123 45678 5') == GTIN('0 979 0 123 45678 5')
    assert ISMN('ISMN 979-0-123-45678-5') == GTIN('0-979-0-123-45678-5')
    assert ISMN('ISMN: 979 0 123 45678 5') == GTIN('0 979 0 123 45678 5')
    assert ISMN('ISMN: 979-0-123-45678-5') == GTIN('0-979-0-123-45678-5')
    assert ISMN('ismn: m 299102349') == GTIN('0 979 0 299102349')
    assert ISMN('ismn: m 299102349') == GTIN('09790299102349')
    assert ISMN('ISMN M 299102349') == GTIN('0 979 0 299102349')
    assert ISMN('ISMN M 299102349') == GTIN('09790299102349')
    assert ISMN('ISMN: M 299102349') == GTIN('0 979 0 299102349')
    assert ISMN('ISMN: M 299102349') == GTIN('09790299102349')
    assert ISMN('ismn: m-321-76543-6') == GTIN('0-979-0-321-76543-6')
    assert ISMN('ISMN M-321-76543-6') == GTIN('0-979-0-321-76543-6')
    assert ISMN('ISMN: M-321-76543-6') == GTIN('0-979-0-321-76543-6')
    assert ISMN('ismn: m-321-76544-3') == GTIN('0-979-0-321-76544-3')
    assert ISMN('ISMN M-321-76544-3') == GTIN('0-979-0-321-76544-3')
    assert ISMN('ISMN: M-321-76544-3') == GTIN('0-979-0-321-76544-3')
    assert ISMN('ismn: m-321-76545-0') == GTIN('0-979-0-321-76545-0')
    assert ISMN('ISMN M-321-76545-0') == GTIN('0-979-0-321-76545-0')
    assert ISMN('ISMN: M-321-76545-0') == GTIN('0-979-0-321-76545-0')
    assert ISMN('ismn: m-321-76546-7') == GTIN('0-979-0-321-76546-7')
    assert ISMN('ISMN M-321-76546-7') == GTIN('0-979-0-321-76546-7')
    assert ISMN('ISMN: M-321-76546-7') == GTIN('0-979-0-321-76546-7')
    assert ISMN('ismn: m-321-76547-4') == GTIN('0-979-0-321-76547-4')
    assert ISMN('ISMN M-321-76547-4') == GTIN('0-979-0-321-76547-4')
    assert ISMN('ISMN: M-321-76547-4') == GTIN('0-979-0-321-76547-4')
    assert ISMN('ismn: m-321-76548-1') == GTIN('0-979-0-321-76548-1')
    assert ISMN('ISMN M-321-76548-1') == GTIN('0-979-0-321-76548-1')
    assert ISMN('ISMN: M-321-76548-1') == GTIN('0-979-0-321-76548-1')
    assert ISMN('ismn: m-321-76549-8') == GTIN('0-979-0-321-76549-8')
    assert ISMN('ISMN M-321-76549-8') == GTIN('0-979-0-321-76549-8')
    assert ISMN('ISMN: M-321-76549-8') == GTIN('0-979-0-321-76549-8')
    assert ISMN('ismn: m-321-76550-4') == GTIN('0-979-0-321-76550-4')
    assert ISMN('ISMN M-321-76550-4') == GTIN('0-979-0-321-76550-4')
    assert ISMN('ISMN: M-321-76550-4') == GTIN('0-979-0-321-76550-4')
    assert ISMN('ismn: m-321-76551-1') == GTIN('0-979-0-321-76551-1')
    assert ISMN('ISMN M-321-76551-1') == GTIN('0-979-0-321-76551-1')
    assert ISMN('ISMN: M-321-76551-1') == GTIN('0-979-0-321-76551-1')
    assert ISMN('ismn: m-345-12345-8') == GTIN('0-979-0-345-12345-8')
    assert ISMN('ISMN M-345-12345-8') == GTIN('0-979-0-345-12345-8')
    assert ISMN('ISMN: M-345-12345-8') == GTIN('0-979-0-345-12345-8')
    assert ISMN('m345123458') == GTIN('9790345123458')
    assert ISMN('M345123458') == GTIN('9790345123458')
    assert str(ISMN('ISMN 979 0 123 45678 5')) == 'ISMN M-1234-5678-5'
    assert str(ISMN('ISMN 979-0-123-45678-5')) == 'ISMN M-1234-5678-5'
    assert str(ISMN('ISMN 979 0 299102349')) == 'ISMN M-2991-0234-9'
    assert str(ISMN('ISMN 9790299102349')) == 'ISMN M-2991-0234-9'
    assert str(ISMN('ISMN 979-0-321-76543-6')) == 'ISMN M-3217-6543-6'
    assert str(ISMN('ISMN 979-0-321-76544-3')) == 'ISMN M-3217-6544-3'
    assert str(ISMN('ISMN 979-0-321-76545-0')) == 'ISMN M-3217-6545-0'
    assert str(ISMN('ISMN 979-0-321-76546-7')) == 'ISMN M-3217-6546-7'
    assert str(ISMN('ISMN 979-0-321-76547-4')) == 'ISMN M-3217-6547-4'
    assert str(ISMN('ISMN 979-0-321-76548-1')) == 'ISMN M-3217-6548-1'
    assert str(ISMN('ISMN 979-0-321-76549-8')) == 'ISMN M-3217-6549-8'
    assert str(ISMN('ISMN 979-0-321-76550-4')) == 'ISMN M-3217-6550-4'
    assert str(ISMN('ISMN 979-0-321-76551-1')) == 'ISMN M-3217-6551-1'
    assert str(ISMN('ISMN 979-0-345-12345-8')) == 'ISMN M-3451-2345-8'
    assert str(ISMN('International Standard Music Number 979-0-345-12345-8')) == 'ISMN M-3451-2345-8'
    assert str(ISMN('International Standard Music Number M-345-12345-8')) == 'ISMN M-3451-2345-8'
    assert str(ISMN('9790345123458')) == 'ISMN M-3451-2345-8'
    assert ISMN('ISMN 979 0 123 45678 5').__str__(short = True) == 'M123456785'
    assert ISMN('ISMN 979-0-123-45678-5').__str__(short = True) == 'M123456785'
    assert ISMN('ISMN 979 0 299102349').__str__(short = True) == 'M299102349'
    assert ISMN('ISMN 9790299102349').__str__(short = True) == 'M299102349'
    assert ISMN('ISMN 979-0-321-76543-6').__str__(short = True) == 'M321765436'
    assert ISMN('ISMN 979-0-321-76544-3').__str__(short = True) == 'M321765443'
    assert ISMN('ISMN 979-0-321-76545-0').__str__(short = True) == 'M321765450'
    assert ISMN('ISMN 979-0-321-76546-7').__str__(short = True) == 'M321765467'
    assert ISMN('ISMN 979-0-321-76547-4').__str__(short = True) == 'M321765474'
    assert ISMN('ISMN 979-0-321-76548-1').__str__(short = True) == 'M321765481'
    assert ISMN('ISMN 979-0-321-76549-8').__str__(short = True) == 'M321765498'
    assert ISMN('ISMN 979-0-321-76550-4').__str__(short = True) == 'M321765504'
    assert ISMN('ISMN 979-0-321-76551-1').__str__(short = True) == 'M321765511'
    assert ISMN('ISMN 979-0-345-12345-8').__str__(short = True) == 'M345123458'
    assert ISMN('International Standard Music Number M-345-12345-8').__str__(short = True) == 'M345123458'
    assert ISMN('International Standard Music Number 979-0-345-12345-8').__str__(short = True) == 'M345123458'
    assert ISMN('9790345123458').__str__(short = True) == 'M345123458'
    pass

def main(progname, infile = '-'):
    infile = (infile == '-') and sys.stdin or (type(infile) in (type(''), type(u'')) and file(infile) or infile)
    errors = 0
    while True:
        line = infile.readline()
        if not line: break
        line = line.strip()
        if line:
            public = True
            if line[:len('[private]')] == '[private]':
                line = line[len('[private]'):].strip()
                public = False
                pass
            i = None
            prev = None
            for c in UPC8, ISBN, ISMN, ISSN, EAN8, UPC12, EAN13, EAN14, GTIN:
                try:
                    try: i = c(line, public = public)
                    except: i = c(line)
                    pass
                except:
                    try: j = c(line, autocorrect = True)
                    except:
                        try: j = c(line, autocorrect = True, public = False)
                        except: pass
                        else: print 'Perhaps you meant [private] %s?' % j
                        pass
                    else: print 'Perhaps you meant %s?' % j
                else:
                    if prev is not None and prev == i:
                        print '==', `i`
                        print ' printed form =', str(i)
                        print ' short form =', i.__str__(short = True)
                        continue
                    if prev is not None: print '*** DIFFERS (AMBIGUOUS INPUT) ***' + '\n' + '!=',
                    print `i`
                    prev = i
                    print ' printed form =', str(i)
                    print ' short form =', i.__str__(short = True)
                    print ' public =', i.public
                    print ' gtin =', i.gtin
                    print ' gtin check digit =', i.gtincheck
                    print ' info =', `i.info`
                    print ' pack =', `i.pack`
                    print ' GTIN =', GTIN(i, public = public)
                    try: print ' ISSN = %s' % ISSN(i)
                    except: pass
                    try: print ' ISBN = %s' % ISBN(i)
                    except: pass
                    try: print ' ISMN = %s' % ISMN(i)
                    except: pass
                    try: print ' UPC E/UPC-8 = %s' % UPC8(i)
                    except: pass
                    try: print ' UPC A/UPC-12 = %s' % UPC12(i)
                    except: pass
                    try: print ' EAN-8 = %s' % EAN8(i)
                    except: pass
                    try: print ' EAN-13 = %s' % EAN13(i)
                    except: pass
                    try: print ' EAN-14 = %s' % EAN14(i)
                    except: pass
                    pass
                pass
            if i is None:
                try: GTIN(line)
                except Exception, e:
                    errors += 1
                    print e
                    pass
                pass
            pass
        pass
    return errors and 1 or 0

test()

if __name__ == '__main__': sys.exit(main(*(sys.argv)))
