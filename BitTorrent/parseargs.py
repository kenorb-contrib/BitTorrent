# Written by Bram Cohen
# this file is public domain

from getopt import getopt, GetoptError
from types import *
from cStringIO import StringIO

def combined(longname, shortname):
    s = ''
    if longname:
        s = '--' + longname
        if shortname:
            s += '/'
    if shortname:
        s += '-' + shortname
    return s

def formatDefinitions(options, COLS):
    s = StringIO()
    indent = " " * 10
    width = COLS - 11

    if width < 15:
        width = COLS - 2
        indent = " "

    for (longname, shortname, default, doc) in options:
        s.write(combined(longname, shortname) + ' <arg>\n')
        if default is not None:
            doc += ' defaults to ' + `default`
        i = 0
        for word in doc.split():
            if i == 0:
                s.write(indent + word)
                i = len(word)
            elif i + len(word) >= width:
                s.write('\n' + indent + word)
                i = len(word)
            else:
                s.write(' ' + word)
                i += len(word) + 1
        s.write('\n\n')
    return s.getvalue()

def usage(str):
    raise ValueError(str)

def parseargs(argv, options, minargs, maxargs):
    config = {}
    required = {}

    shortopts = ''
    longopts = []
    shortkeyed = {}
    longkeyed = {}
    for option in options:
        longname, shortname, default, doc = option
        if shortname:
            shortopts += shortname + ':'
            shortkeyed['-' + shortname] = option

        if longname:
            longopts.append(longname + '=')
            longkeyed['--' + longname] = option

        if default is None:
            required[longname] = option
        else:
            config[longname] = default

    try:
        options, args = getopt(argv, shortopts, longopts)
    except GetoptError, e:
        usage(str(e))

    for key, value in options:
        if shortkeyed.has_key(key):
            longname, shortname, default, doc = shortkeyed[key]
        else:
            longname, shortname, default, doc = longkeyed[key]
        try:
            t = type(config.get(longname))
            if t is NoneType or t is StringType:
                config[longname] = value
            elif t is IntType or t is LongType:
                config[longname] = long(value)
            elif t is FloatType:
                config[longname] = float(value)
            else:
                assert 0
        except ValueError, e:
            usage('wrong format of %s - %s' % (key, str(e)))

    for key in required.keys():
        if not config.has_key(key):
            longname, shortname, default, doc = required[key]
            usage("Option %s is required." % combined(longname, shortname))

    if len(args) < minargs:
        usage("Must supply at least %d args." % minimumArgs)
    if len(args) > maxargs:
        usage("Too many args - %d max." % maximumArgs)

    return (config, args)
