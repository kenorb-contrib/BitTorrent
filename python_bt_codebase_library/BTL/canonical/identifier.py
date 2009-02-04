#!/usr/bin/env python
# -*- coding: utf-8 -*-
# fold input for homograph comparison

# see: http://www.unicode.org/reports/tr36/
import sys
import os
import unicodedata
import urllib
import time
import random

try:
    from BTL.obsoletepythonsupport import set
except:
    pass

from BTL.canonical.unicode import unichr, unichars, unilen, uniord

try:
    from _confuse import confusables, confusemap
except:
    confusables = { 'SL': {}, 'SA': {}, 'ML': {}, 'MA': {}, 'all': {} }
    confusemap = {}

_init_in_progress = False

_confuse_specials = {
    u'\N{LATIN SMALL LETTER DOTLESS I}\N{COMBINING DOT ABOVE}': u'i',
    u'\N{LATIN CAPITAL LETTER O WITH HORN}': u'O \N{COMBINING COMMA ABOVE}',
    u'\N{LATIN SMALL LETTER O WITH HORN}': u'o \N{COMBINING COMMA ABOVE}',
    }

def confuse(us, cclasses = [ 'all' ], asciify = True, smart = False):
    '''
    Fold input for homograph comparison.
    '''
    us = _confuse_internal(us, cclasses, asciify, smart)
    for i, o in _confuse_specials.iteritems():
        us = _confuse_internal(o, cclasses, asciify).join(us.split(_confuse_internal(i, cclasses, asciify, smart)))
    return us

def _confuse_internal(us, cclasses = [ 'all' ], asciify = True, smart = False):
    '''
    Fold input for homograph comparison. Does not handle the special cases that require postprocessing or multicharacter matching.
    '''
    assert type(us) == type(u'')
    global confusemap, confusables
    if cclasses == [ 'all' ] and asciify and confusemap and not smart:
        return u''.join([ confusemap.get(dest, unicodedata.normalize('NFC', dest.lower())) for dest in unichars(unicodedata.normalize('NFKD', us)) ])
    if not confusemap:
        _slow_init()
    out = []
    for ch in unichars(unicodedata.normalize('NFKD', us)):
        b = ch
        b2 = u''
        for cclass in cclasses:
            if ch in confusables[cclass]:
                if smart:
                    b = random.choice([ b ] + list(confusables[cclass][ch]))
                    break
                else:
                    for rep in confusables[cclass][ch]:
                        if unilen(rep) > unilen(b2) or rep < b2:
                            b, b2 = [rep] * 2
        out.append(b)
    out = u''.join(out)
    if asciify:
        out = unicodedata.normalize('NFC', out.lower())
    if out != us and cclasses == [ 'all' ] and not smart:
        out = _confuse_internal(out, cclasses, asciify)
    return out

def transform(cclasses, us):
    '''
    Fold input for homograph comparison.
    '''
    return confuse(us, cclasses, asciify = True)

def _slow_init(confusables_file = None):
    global confusables, confusemap, _init_in_progress
    if _init_in_progress:
        return
    _init_in_progress = True
    try:
        if confusables_file is None and __name__ == '__main__':
            try:
                confusables_file = file(os.path.join(os.path.split(sys.argv[0])[0], '../share/confusables.txt'), 'rb')
            except:
                pass
        if confusables_file is None:
            confusables_file = urllib.urlopen('http://www.unicode.org/reports/tr36/data/confusables.txt', 'rb')
        for line in confusables_file:
            line = line.decode('utf-8').rstrip()
            try:
                cmd, comment = [ field.strip() for field in line.split('#', 1) ]
                a, b, cclass = [ field.strip() for field in cmd.split(';') ]
                a, b = [ u''.join([ unichr(int(ch, 16)) for ch in field.split() ]) for field in (a, b) ]
                confusables[cclass][a] = confusables[cclass].get(a, set()) | set((b,))
            except:
                pass
        confusables_file.close()

        for chno in xrange(0, 0x110000):
            source = unichr(chno)
            sources = set([ source, unicodedata.normalize('NFKD', source),
                            source.upper(), unicodedata.normalize('NFKD', source.upper()),
                            source.title(), unicodedata.normalize('NFKD', source.title()),
                            source.lower(), unicodedata.normalize('NFKD', source.lower())])
            try:
                sources = sources | set([ source.encode('idna').decode('idna') ])
            except:
                pass
            while True:
                sources2 = sources
                for source in sources:
                    sources2 = sources2 | confusables['all'].get(source, set([ source ]))
                if sources2 == sources:
                    break
                sources = sources2
            if len(sources) > 1:
                for source in sources:
                    if unilen(source) == 1:
                        confusables['all'][source] = sources

        for cclass in confusables:
            if cclass == 'all':
                continue
            for source in confusables[cclass]:
                dest = confusables[cclass][source]
                dest = dest | confusables['all'].get(source, set()) | set([ source ])
                dest2 = dest
                for d in dest2:
                    dest = dest | confusables['all'].get(d, set())
                for d in dest:
                    if unilen(d) == 1:
                        confusables['all'][d] = confusables['all'].get(d, set()) | dest

        confusables['all2'] = {}

        for source in confusables['all']:
            sources = set([ source, unicodedata.normalize('NFKD', source),
                            source.upper(), unicodedata.normalize('NFKD', source.upper()),
                            source.title(), unicodedata.normalize('NFKD', source.title()),
                            source.lower(), unicodedata.normalize('NFKD', source.lower())])
            dest = set()
            for source2 in sources:
                dest = dest | confusables['all'].get(source2, set())
            sources = sources | dest
            dest = set()
            for source2 in sources:
                dest = dest | confusables['all'].get(source2, set())
            sources = sources | dest
            for source2 in sources:
                if unilen(source2) == 1:
                    confusables['all2'][source2] = sources

        confusables['all'] = confusables['all2']

        del confusables['all2']

        confusables['all2'] = {}

        for source in confusables['all']:
            sources = set([ source, unicodedata.normalize('NFKD', source),
                            source.upper(), unicodedata.normalize('NFKD', source.upper()),
                            source.title(), unicodedata.normalize('NFKD', source.title()),
                            source.lower(), unicodedata.normalize('NFKD', source.lower())])
            dest = set()
            for source2 in sources:
                dest = dest | confusables['all'].get(source2, set())
            sources = sources | dest
            dest = set()
            for source2 in sources:
                dest = dest | confusables['all'].get(source2, set())
            sources = sources | dest
            for source2 in sources:
                if unilen(source2) == 1:
                    confusables['all2'][source2] = sources

        confusables['all'] = confusables['all2']

        del confusables['all2']

        confusables['all2'] = {}

        for source in confusables['all']:
            sources = set([ source, unicodedata.normalize('NFKD', source),
                            source.upper(), unicodedata.normalize('NFKD', source.upper()),
                            source.title(), unicodedata.normalize('NFKD', source.title()),
                            source.lower(), unicodedata.normalize('NFKD', source.lower())])
            dest = set()
            for source2 in sources:
                dest = dest | confusables['all'].get(source2, set())
            sources = sources | dest
            dest = set()
            for source2 in sources:
                dest = dest | confusables['all'].get(source2, set())
            sources = sources | dest
            for source2 in sources:
                if unilen(source2) == 1:
                    confusables['all2'][source2] = sources

        confusables['all'] = confusables['all2']

        del confusables['all2']

        _confusemap = {}
        for chno in xrange(0, 0x110000):
            source = unichr(chno)
            dest = _confuse_internal(source, cclasses = [ 'all' ], asciify = True)
            dest2 = unicodedata.normalize('NFKC', source.lower())
            if dest != dest2 or (uniord(source) >= 0x10000 and source != dest):
                if dest != unicodedata.normalize('NFC', dest.lower()):
                    raise ValueError(repr(source) + ': ' + repr(dest))
                _confusemap[source] = dest
        confusemap = _confusemap
    finally:
        _init_in_progress = False

def test():
    '''
    Small smoke test to make sure this module is not broken.
    '''
    assert unilen(u'\U0010fffd') == 1
    assert len(u'Hello, world!') == unilen(u'Hello, world!')
    assert uniord(u'\U0010fffd') == 0x10fffd
    assert uniord(u'H') == ord(u'H')
    assert unichr(0x10fffd) == u'\U0010fffd'
    assert unichr(ord(u'H')) == u'H'
    assert [ ch for ch in unichars(u'H\U0010fffd') ] == [ 'H', u'\U0010fffd' ]
    assert confuse(u'Hello, world!', [ 'all' ], True) == confuse(u'he110, w0r1d!', [ 'all' ], True)
    assert confuse(u'Sergey Brin') == confuse(u'5e\N{GREEK SMALL LETTER GAMMA}g\N{GREEK SMALL LETTER EPSILON}\N{GREEK SMALL LETTER UPSILON} \N{GREEK CAPITAL LETTER BETA}r1\N{GREEK CAPITAL LETTER NU}')
    assert confuse(u'He\N{LATIN SMALL LETTER SHARP S}e') == confuse(u'Hesse')
    assert confuse(u'\N{GREEK CAPITAL LETTER KAPPA}\N{GREEK SMALL LETTER NU}\N{GREEK SMALL LETTER OMEGA}\N{GREEK SMALL LETTER SIGMA}\N{GREEK SMALL LETTER OMICRON WITH TONOS}\N{GREEK SMALL LETTER FINAL SIGMA}') == confuse(u'Kv\N{OHM SIGN}co\N{COMBINING ACUTE ACCENT}c')
    assert confuse(u'\N{LATIN SMALL LETTER I}') == confuse(u'\N{LATIN CAPITAL LETTER I}')
    assert confuse(u'\N{LATIN SMALL LETTER I}\N{COMBINING DOT ABOVE}') == confuse(u'\N{LATIN CAPITAL LETTER I WITH DOT ABOVE}')
    assert confuse(u'\N{LATIN SMALL LETTER DOTLESS I}') == confuse(u'\N{LATIN CAPITAL LETTER I}')
    assert confuse(u'\N{LATIN SMALL LETTER DOTLESS I}\N{COMBINING DOT ABOVE}') == confuse(u'\N{LATIN SMALL LETTER I}')
    assert confuse(u'\N{LATIN SMALL LETTER DOTLESS I}\N{COMBINING DOT ABOVE}') == confuse(u'\N{LATIN SMALL LETTER I}\N{COMBINING DOT ABOVE}')
    assert confuse(u'\N{LATIN SMALL LETTER DOTLESS I}\N{COMBINING DOT ABOVE}') == confuse(u'\N{LATIN CAPITAL LETTER I}\N{COMBINING DOT ABOVE}')
    assert confuse(u'\N{LATIN SMALL LETTER DOTLESS I}\N{COMBINING DOT ABOVE}') == confuse(u'\N{LATIN CAPITAL LETTER I WITH DOT ABOVE}')
    assert confuse(u'\N{LATIN CAPITAL LETTER I}\N{COMBINING DOT ABOVE}') == confuse(u'\N{LATIN CAPITAL LETTER I WITH DOT ABOVE}')
    assert confuse(u'\N{LATIN CAPITAL LETTER I WITH DOT ABOVE}') == confuse(u'\N{DIGIT ONE}\N{COMBINING DOT ABOVE}')
    assert confuse(u'\N{LATIN CAPITAL LETTER O WITH HORN}') == confuse(u'\N{DIGIT ZERO}\N{COMBINING HORN}')
    assert confuse(u'\N{LATIN SMALL LETTER O WITH HORN}') == confuse(u'\N{DIGIT ZERO}\N{COMBINING HORN}')
    assert confuse(u'\N{LATIN SMALL LETTER I}') == confuse(u'\N{LATIN SMALL LETTER I}\N{COMBINING DOT ABOVE}')
    assert confuse(u'\N{LATIN SMALL LETTER I}') == confuse(u'\N{LATIN CAPITAL LETTER I WITH DOT ABOVE}')
    assert confuse(u'\N{LATIN CAPITAL LETTER I WITH DOT ABOVE}') == confuse(u'\N{DIGIT ONE}')
    assert confuse(u'\N{LATIN CAPITAL LETTER O WITH HORN}') == confuse(u'\N{LATIN CAPITAL LETTER O}\N{SPACE}\N{COMBINING COMMA ABOVE}')
    assert confuse(u'\N{LATIN SMALL LETTER O WITH HORN}') == confuse(u'\N{LATIN CAPITAL LETTER O}\N{SPACE}\N{COMBINING COMMA ABOVE}')

    # NOTE: this is a weak bidi homograph for "i love you"
    assert confuse(u'ڸ٥ﻻ ﻉ√٥ﺎ ٱ') == confuse(u'\u06b8\u0665\ufefb \ufec9\u221a\u0665\ufe8e \u0671')
    assert confuse(u'\u06b8\u0665\u0644\u0627 \u0639\u221a\u0665\u0627 \u0671') == confuse(u'ڸ٥ﻻ ﻉ√٥ﺎ ٱ')
    assert (confuse(u''.join(u'''
    0\u09e6\u2080\u0d02\u0585\u3007\U0001d70a\U0001d5ae\u1d0f\U0001d40e\u1810\U0001d512\U0001d7f6\U0001d594\U0001d616\U0001d698\u0966\u101d\U0001d6f0\u039f\u041e\u0d20\U0001d7ec\uff4f\u0c66\U0001d630\U0001d428\U0001d72a\U0001d52c\uff2f\u0be6\u0030\u24c4\u0a66\u2134\U0001d6b6\U0001d7b8\u0ed0\U0001d79e\uff10\u03bf\u043e\u1040\U0001d442\U0001d744\U0001d546\U0001d5c8\U0001d64a\U0001d664\U0001d67e\u004f\U0001d7ce\u0e50\U0001d5e2\u0555\u2d54\u0c02\U0001d7d8\u0c82\U0001d45c\u24de\U0001d560\U0001d7e2\U0001d764\u0ae6\U0001d490\u0ce6\u0b66\U0001d4aa\u006f\u24ea\u2070\U0001d4de\U0001d476\u00ba\U0001d4f8\U0001d6d0\U0001d57a\U0001d5fc\U0001d77e
    1\U0001d408\U0001d456\U0001d591\U0001d610\u2112\u0399\u24db\u0322\u13a5\U0001d526\u03b9\U0001d43c\U0001d73e\U0001d5c5\U0001d644\u004c\U0001d7d9\U0001d4db\U0001d55a\U0001d75e\u2460\U0001d7ed\u006c\U0001d470\U0001d5f9\U0001d678\u24be\U0001d40b\U0001d58e\uff11\U0001d613\u0196\U0001d6a4\U0001d529\u0131\U0001d6b0\U0001d7b2\u2139\U0001d43f\u1fbe\u04c0\U0001d5c2\u0345\U0001d647\uff49\u24d8\U0001d55d\u13de\U0001d473\U0001d5f6\U0001d67b\u2081\U0001d704\u0406\U0001d48d\u2110\U0001d695\U0001d4d8\U0001d422\U0001d724\u0328\U0001d5ab\U0001d62a\uff2c\u00b9\u24c1\U0001d540\u2148\uff4c\U0001d7cf\u0456\U0001d5df\U0001d65e\u02e1\u2160\U0001d7e3\u0069\u216c\u2170\U0001d4f5\U0001d574\U0001d7f7\U0001d778\u217c\u2780\U0001d48a\U0001d50f\u2113\U0001d692\U0001d798\U0001d425\U0001d5a8\u2111\U0001d62d\u0031\U0001d4be\U0001d543\u0049\U0001d6ca\U0001d459\U0001d5dc\U0001d661\u0269\U0001d6ea\u2071\uff29\u2373\U0001d4f2\U0001d577\u0130
    2\u2781\u2461\u2082\U0001d7e4\U0001d7ee\U0001d7d0\uff12\U0001d7f8\u0032\U0001d7da\u00b2\u14bf
    3\u2083\u2782\U0001d409\u0408\U0001d48b\u148d\U0001d58f\U0001d611\u24d9\U0001d693\u0417\u0545\U0001d55b\U0001d423\U0001d4a5\U0001d527\U0001d5a9\u13ab\uff2a\u03f3\u00b3\u02b2\u0437\u0575\U0001d43d\u24bf\U0001d541\U0001d5c3\u004a\U0001d645\u0033\u2149\U0001d50d\uff4a\U0001d7d1\U0001d679\U0001d457\U0001d4d9\u0458\U0001d7db\U0001d5dd\u025c\U0001d65f\u2462\U0001d7e5\u13e7\u006a\uff13\U0001d7ef\U0001d471\U0001d4f3\U0001d575\U0001d4bf\U0001d5f7\U0001d7f9\U0001d62b
    4\u2783\u2084\U0001d7e6\u0034\u2463\u13ce\U0001d7f0\U0001d7d2\uff14\U0001d7fa\U0001d7dc\u2074
    5\U0001d598\U0001d600\U0001d682\u2085\u2784\u0053\u02e2\U0001d412\uff15\U0001d494\U0001d516\u0405\U0001d61a\U0001d69c\U0001d42c\U0001d4ae\U0001d530\uff33\U0001d5b2\u0035\U0001d634\u24c8\u01bd\u01bc\U0001d446\U0001d4c8\U0001d54a\U0001d5cc\U0001d64e\U0001d7d3\U0001d4e2\u13d5\u13da\U0001d7dd\u2464\U0001d460\u24e2\U0001d564\U0001d7e7\U0001d5e6\U0001d668\uff53\U0001d7f1\u0073\u2075\u0455\U0001d7fb\U0001d47a\U0001d4fc\u017f\U0001d57e
    6\u0431\u2785\u2086\U0001d7e8\u0036\u2076\u0411\U0001d7f2\U0001d7d4\uff16\u2465\U0001d7fc\U0001d7de
    7\u0037\u2087\u2786\U0001d7e9\u2466\u2077\U0001d7f3\U0001d7d5\uff17\U0001d7fd\U0001d7df
    8\U0001d7e0\u0b03\u0222\u2467\u2787\u09ea\u2088\U0001d7ea\uff18\u0223\U0001d7f4\U0001d7d6\u0038\u0a6a\u2078\U0001d7fe
    9\U0001d7e1\u2468\u2079\u0a67\u2089\u2788\U0001d7eb\u09ed\u0039\U0001d7f5\U0001d7d7\u0b68\uff19\U0001d7ff
    '''.split())) == confuse(
        u'0' * len('................................................................................')
        +
        u'1' * len('...............................................................................................................')
        +
        u'2' * len('.............')
        +
        u'3' * len('.........................................................')
        +
        u'4' * len('.............')
        +
        u'5' * len('....................................................')
        +
        u'6' * len('..............')
        +
        u'7' * len('............')
        +
        u'8' * len('.................')
        +
        u'9' * len('...............')
        ))
    pass

test()

def main(args):
    '''
    Command-line interface to this module.
    '''
    asciify = False
    if args[1:][:1] == [ '-a' ]:
        args = args[:1] + args[2:]
        asciify = True
    if args[1:][:1] == [ '-w' ]:
        args = args[:1] + args[2:]
        print '#!/usr/bin/env python'
        print '# automatically generated'
        print 'try:'
        print '    from BTL.obsoletepythonsupport import set'
        print 'except:'
        print '    pass'
        print 'confusables = {'
        for cclass in confusables:
            print '    %r: {' % cclass
            kk = confusables[cclass].keys()
            kk.sort()
            seen = {}
            for k in kk:
                seenkey = tuple(confusables[cclass][k])
                print '        ' + repr(k) + ':',
                if seenkey not in seen:
                    print 'set(['
                    for ch in confusables[cclass][k]:
                        print '            ' + repr(ch) + ','
                        if ch in kk:
                            kk
                    print '        ]),'
                    seen[seenkey] = k
                else:
                    print '%s,' % repr(seen[seenkey])
            print '    },'
        print '}'
        print 'def _init_confusables():'
        print '    global confusables'
        print '    for cclass in confusables:'
        print '        for k in confusables[cclass]:'
        print '            v = confusables[cclass][k]'
        print '            if type(v) == type(u\'\'):'
        print '                confusables[cclass][k] = confusables[cclass][v]'
        print '_init_confusables()'
        print 'confusemap = {'
        kk = confusemap.keys()
        kk.sort()
        for k in kk:
            print '    ' + repr(k) + ': ' + repr(confusemap[k]) + ','
        print '}'
        return
    if args[1:][:1] == [ '-a' ]:
        args = args[:1] + args[2:]
        asciify = True
    cclasses = args[1:] or [ 'all' ]
    for cclass in cclasses:
        assert cclass in confusables
    while True:
        line = sys.stdin.readline()
        if not line:
            break
        line = unicodedata.normalize('NFC', line.decode('utf-8'))
        sys.stdout.write(confuse(line, cclasses, asciify).encode('utf-8'))
        sys.stdout.flush()

if __name__ == '__main__':
    main(sys.argv)
