# The contents of this file are subject to the BitTorrent Open Source License
# Version 1.0 (the License).  You may not copy or use this file, in either
# source code or executable form, except in compliance with the License.  You
# may obtain a copy of the License at http://www.bittorrent.com/license/.
#
# Software distributed under the License is distributed on an AS IS basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied.  See the License
# for the specific language governing rights and limitations under the
# License.

# Written by Uoti Urpala

import os
import sys
# Python 2.2 doesn't have RawConfigParser
try:
    from ConfigParser import RawConfigParser
except ImportError:
    from ConfigParser import ConfigParser as RawConfigParser

from ConfigParser import MissingSectionHeaderError, ParsingError

from BitTorrent import parseargs
from BitTorrent import ERROR
from BitTorrent import version
from __init__ import get_config_dir


def _read_config(filename):
    # check for bad config files (Windows corrupts them all the time)
    p = RawConfigParser()
    fp = None
    try:
        fp = open(filename)
    except IOError:
        pass

    if fp is not None:
        try:
            p.readfp(fp, filename=filename)
        except MissingSectionHeaderError:
            fp.close()
            del fp
            bad_config(filename)
        except ParsingError:
            fp.close()
            del fp
            bad_config(filename)
        else:
            fp.close()
    return p


def bad_config(filename):
    base_bad_filename = filename + '.broken'
    bad_filename = base_bad_filename
    i = 0
    while os.access(bad_filename, os.F_OK):
        bad_filename = base_bad_filename + str(i)
        i+=1
    os.rename(filename, bad_filename)
    sys.stderr.write(("Error reading config file. "
                      "Old config file stored in \"%s\"") % bad_filename)


def get_config(defaults, section):
    dir_root = get_config_dir()
    if dir_root is None and os.name == 'nt':
        tmp_dir_root = os.path.split(sys.executable)[0]
        if os.access(tmp_dir_root, os.R_OK|os.W_OK):
            dir_root = tmp_dir_root

    if dir_root is None:
        return {}

    configdir = os.path.join(dir_root, '.bittorrent')
    if not os.path.isdir(configdir):
        try:
            os.mkdir(configdir, 0700)
        except:
            pass

    p = _read_config(os.path.join(configdir, 'config'))
    values = {}
    if p.has_section(section):
        for name, value in p.items(section):
            if name in defaults:
                values[name] = value
    if p.has_section('common'):
        for name, value in p.items('common'):
            if name in defaults and name not in values:
                values[name] = value
    if defaults.get('data_dir') == '' and \
           'data_dir' not in values and os.path.isdir(configdir):
        datadir = os.path.join(configdir, 'data')
        values['data_dir'] = datadir
    parseargs.parse_options(defaults, values)
    return values


def save_ui_config(defaults, section, save_options, error_callback):
    filename = os.path.join(defaults['data_dir'], 'ui_config')
    p = _read_config(filename)
    p.remove_section(section)
    p.add_section(section)
    for name in save_options:
        p.set(section, name, defaults[name])
    try:
        f = file(filename, 'w')
        p.write(f)
        f.close()
    except Exception, e:
        try:
            f.close()
        except:
            pass
        error_callback(ERROR, 'Could not permanently save options: '+
                       str(e))


def parse_configuration_and_args(defaults, uiname, arglist=[], minargs=0,
                                 maxargs=0):
    defconfig = dict([(name, value) for (name, value, doc) in defaults])
    if arglist[0:] == ['--version']:
        print version
        sys.exit(0)

    if arglist[0:] in (['--help'], ['-h'], ['--usage'], ['-?']): 
        parseargs.printHelp(uiname, defaults)
        sys.exit(0)
    
    presets = get_config(defconfig, uiname)
    config, args = parseargs.parseargs(arglist, defaults, minargs, maxargs,
                                       presets)
    datadir = config['data_dir']
    if datadir:
        if uiname in ('btdownloadgui', 'btmaketorrentgui'):
            values = {}
            p = _read_config(os.path.join(datadir, 'ui_config'))
            if p.has_section(uiname):
                for name, value in p.items(uiname):
                    if name in defconfig:
                        values[name] = value
            parseargs.parse_options(defconfig, values)
            presets.update(values)
            config, args = parseargs.parseargs(arglist, defaults, minargs,
                                               maxargs, presets)
        rdir = os.path.join(datadir, 'resume')
        mdir = os.path.join(datadir, 'metainfo')
        try:
            if not os.path.exists(datadir):
                os.mkdir(datadir, 0700)
            if not os.path.exists(mdir):
                os.mkdir(mdir, 0700)
            if not os.path.exists(rdir):
                os.mkdir(rdir, 0700)
        except:
            pass
    return config, args
