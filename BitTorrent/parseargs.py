# The contents of this file are subject to the BitTorrent Open Source License
# Version 1.1 (the License).  You may not copy or use this file, in either
# source code or executable form, except in compliance with the License.  You
# may obtain a copy of the License at http://www.bittorrent.com/license/.
#
# Software distributed under the License is distributed on an AS IS basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied.  See the License
# for the specific language governing rights and limitations under the
# License.

# Written by Bill Bumgarner and Bram Cohen

from types import *
from cStringIO import StringIO

from BitTorrent.obsoletepythonsupport import *

from BitTorrent.defaultargs import MyBool, MYTRUE
from BitTorrent import BTFailure
from BitTorrent.bencode import bdecode
from BitTorrent.platform import is_frozen_exe
from BitTorrent.RawServer_magic import switch_rawserver

def makeHelp(uiname, defaults):
    ret = ''
    ret += (_("Usage: %s ") % uiname)
    if uiname.startswith('launchmany'):
        ret += _("[OPTIONS] [TORRENTDIRECTORY]\n\n")
        ret += _("If a non-option argument is present it's taken as the value\n"
                 "of the torrent_dir option.\n")
    elif uiname == 'bittorrent':
        ret += _("[OPTIONS] [TORRENTFILES]\n")
    elif uiname.startswith('bittorrent'):
        ret += _("[OPTIONS] [TORRENTFILE]\n")
    elif uiname.startswith('maketorrent'):
        ret += _("[OPTION] TRACKER_URL FILE [FILE]\n")
    ret += '\n'
    ret += _("arguments are -\n") + formatDefinitions(defaults, 80)
    return ret

def printHelp(uiname, defaults):
    if uiname in ('bittorrent','maketorrent') and is_frozen_exe:
        from BitTorrent.GUI import HelpWindow
        HelpWindow(None, makeHelp(uiname, defaults))
    else:
        print makeHelp(uiname, defaults)

def formatDefinitions(options, COLS):
    s = StringIO()
    indent = " " * 10
    width = COLS - 11

    if width < 15:
        width = COLS - 2
        indent = " "

    for option in options:
        (longname, default, doc) = option
        if doc == '':
            continue
        s.write('--' + longname)
        is_boolean = type(default) is MyBool
        if is_boolean:
            s.write(', --no_' + longname)
        else:
            s.write(' <arg>')
        s.write('\n')
        if default is not None:
            doc += _(" (defaults to ") + repr(default) + ')'
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
    raise BTFailure(str)

def format_key(key):
    if len(key) == 1:
        return '-%s'%key
    else:
        return '--%s'%key

def parseargs(argv, options, minargs=None, maxargs=None, presets=None):
    config = {}
    for option in options:
        longname, default, doc = option
        config[longname] = default
    args = []
    pos = 0
    if presets is None:
        presets = {}
    else:
        presets = presets.copy()
    while pos < len(argv):
        if argv[pos][:1] != '-':             # not a cmdline option
            args.append(argv[pos])
            pos += 1
        else:
            key, value = None, None
            if argv[pos].startswith('--'):        # --aaa 1
                if argv[pos].startswith('--no_'):
                    key = argv[pos][5:]
                    boolval = False
                else:
                    key = argv[pos][2:]
                    boolval = True
                if key not in config:
                    raise BTFailure(_("unknown key ") + format_key(key))
                if type(config[key]) is MyBool: # boolean cmd line switch, no value
                    value = boolval
                    pos += 1
                else: # --argument value
                    if pos == len(argv) - 1:
                        usage(_("parameter passed in at end with no value"))
                    key, value = argv[pos][2:], argv[pos+1]
                    pos += 2
            elif argv[pos][:1] == '-':
                key = argv[pos][1:2]
                if len(argv[pos]) > 2:       # -a1
                    value = argv[pos][2:]
                    pos += 1
                else:                        # -a 1
                    if pos == len(argv) - 1:
                        usage(_("parameter passed in at end with no value"))
                    value = argv[pos+1]
                    pos += 2
            else:
                raise BTFailure(_("command line parsing failed at ")+argv[pos])

            presets[key] = value
    parse_options(config, presets)
    config.update(presets)
    for key, value in config.items():
        if value is None:
            usage(_("Option %s is required.") % format_key(key))
    if minargs is not None and len(args) < minargs:
        usage(_("Must supply at least %d arguments.") % minargs)
    if maxargs is not None and len(args) > maxargs:
        usage(_("Too many arguments - %d maximum.") % maxargs)

    if config.has_key('twisted'):
        if config['twisted'] == 0:
            switch_rawserver('untwisted')
        elif config['twisted'] == 1:
            switch_rawserver('twisted')
    
    return (config, args)

def parse_options(defaults, newvalues):
    for key, value in newvalues.iteritems():
        if not defaults.has_key(key):
            raise BTFailure(_("unknown key ") + format_key(key))
        try:
            t = type(defaults[key])
            if t is MyBool:
                if value in ('True', '1', MYTRUE, True):
                    value = True
                else:
                    value = False
                newvalues[key] = value
            elif t in (StringType, NoneType):
                newvalues[key] = value
            elif t in (IntType, LongType):
                if value == 'False':
                    newvalues[key] == 0
                elif value == 'True':
                    newvalues[key] == 1
                else:
                    newvalues[key] = int(value)
            elif t is FloatType:
                newvalues[key] = float(value)
            else:
                raise TypeError, str(t)

        except ValueError, e:
            raise BTFailure(_("wrong format of %s - %s") % (format_key(key), str(e)))

