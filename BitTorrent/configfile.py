# The contents of this file are subject to the BitTorrent Open Source License
# Version 1.1 (the License).  You may not copy or use this file, in either
# source code or executable form, except in compliance with the License.  You
# may obtain a copy of the License at http://www.bittorrent.com/license/.
#
# Software distributed under the License is distributed on an AS IS basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied.  See the License
# for the specific language governing rights and limitations under the
# License.

# Written by Uoti Urpala and Matt Chisholm

import os
import sys
import gettext
import locale

# Python 2.2 doesn't have RawConfigParser
try:
    from ConfigParser import RawConfigParser
except ImportError:
    from ConfigParser import ConfigParser as RawConfigParser

from ConfigParser import MissingSectionHeaderError, ParsingError
from BitTorrent import parseargs
from BitTorrent import app_name, version, ERROR, BTFailure
from BitTorrent.platform import get_config_dir, locale_root, is_frozen_exe
from BitTorrent.defaultargs import MYTRUE
from BitTorrent.zurllib import bind_tracker_connection, set_zurllib_rawserver

MAIN_CONFIG_FILE = 'ui_config'
TORRENT_CONFIG_FILE = 'torrent_config'

alt_uiname = {'bittorrent':'btdownloadgui',
              'maketorrent':'btmaketorrentgui',}

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


def _write_config(error_callback, filename, p):
    try:
        f = file(filename, 'w')
        p.write(f)
        f.close()
    except Exception, e:
        try:
            f.close()
        except:
            pass
        error_callback(ERROR, _("Could not permanently save options: ")+
                       str(e))


def bad_config(filename):
    base_bad_filename = filename + '.broken'
    bad_filename = base_bad_filename
    i = 0
    while os.access(bad_filename, os.F_OK):
        bad_filename = base_bad_filename + str(i)
        i+=1
    os.rename(filename, bad_filename)
    sys.stderr.write(_("Error reading config file. "
                       "Old config file stored in \"%s\"") % bad_filename)


def get_config(defaults, section):
    dir_root = get_config_dir()

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
    filename = os.path.join(defaults['data_dir'], MAIN_CONFIG_FILE)
    p = _read_config(filename)
    p.remove_section(section)
    if p.has_section(alt_uiname[section]):
        p.remove_section(alt_uiname[section])
    p.add_section(section)
    for name in save_options:
        if defaults.has_key(name):
            p.set(section, name, defaults[name])
        else:
            err_str = _("Configuration option mismatch: '%s'") % name
            if is_frozen_exe:
                err_str = _("You must quit %s and reinstall it. (%s)") % (app_name, err_str)
            error_callback(ERROR, err_str)
    _write_config(error_callback, filename, p)


def save_torrent_config(path, infohash, config, error_callback):
    section = infohash.encode('hex')
    filename = os.path.join(path, TORRENT_CONFIG_FILE)
    p = _read_config(filename)
    p.remove_section(section)
    p.add_section(section)
    for key, value in config.items():
        p.set(section, key, value)
    _write_config(error_callback, filename, p)

def read_torrent_config(global_config, path, infohash, error_callback):
    section = infohash.encode('hex')
    filename = os.path.join(path, TORRENT_CONFIG_FILE)
    p = _read_config(filename)
    if not p.has_section(section):
        return {}
    else:
        c = {}
        for name, value in p.items(section):
            if global_config.has_key(name):
                t = type(global_config[name])
                if t == bool:
                    c[name] = value in ('1', 'True', MYTRUE, True)
                else:
                    c[name] = type(global_config[name])(value)
        return c

def remove_torrent_config(path, infohash, error_callback):
    section = infohash.encode('hex')
    filename = os.path.join(path, TORRENT_CONFIG_FILE)
    p = _read_config(filename)
    if p.has_section(section):
        p.remove_section(section)
    _write_config(error_callback, filename, p)

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
        if uiname in ('bittorrent', 'maketorrent'):
            values = {}
            p = _read_config(os.path.join(datadir, MAIN_CONFIG_FILE))
            if not p.has_section(uiname) and p.has_section(alt_uiname[uiname]):
                uiname = alt_uiname[uiname]
            if p.has_section(uiname):
                for name, value in p.items(uiname):
                    if name in defconfig:
                        values[name] = value
            parseargs.parse_options(defconfig, values)
            presets.update(values)
            config, args = parseargs.parseargs(arglist, defaults, minargs,
                                               maxargs, presets)

        for d in ('', 'resume', 'metainfo'):
            ddir = os.path.join(datadir, d)
            try:
                if not os.path.exists(ddir):
                    os.mkdir(ddir, 0700)
            except:
                pass
            
    if config['language'] != '':
        try:
            lang = gettext.translation('bittorrent', locale_root,
                                       languages=[config['language']])
            lang.install()
        except IOError:
            # don't raise an error, just continue untranslated
            sys.stderr.write(_('Could not find translation for language "%s"\n') %
                             config['language'])
    if config.has_key('bind') and ['bind'] != '':
        bind_tracker_connection(config['bind'])
    return config, args
