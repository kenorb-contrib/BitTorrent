# Written by Bram Cohen
# this file is public domain

def parseargs(argv):
    config = {}
    for i in xrange(len(argv)):
        s = argv[i]
        if s[:1] != '-':
            return (config, argv[i:])
        try:
            x = s.index('=')
            config[s[1:x]] = s[x+1:]
        except ValueError:
            config[s[1:]] = ''
    return (config, [])

def test():
    assert parseargs(['-a=3']) == ({'a': '3'}, [])
    assert parseargs(['']) == ({}, [''])
    assert parseargs(['-a=3', '-a=4']) == ({'a': '4'}, [])
    assert parseargs(['-a', 'b']) == ({'a': ''}, ['b'])
