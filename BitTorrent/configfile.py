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

###########
# Needs redesign.  Adding an app requires modifying a lot of if's. Blech.
#     --Dave
############

import os
import sys
import gettext
import locale

from BitTorrent.translation import _
from ConfigParser import RawConfigParser
from ConfigParser import MissingSectionHeaderError, ParsingError
from BitTorrent import parseargs, set_filesystem_encoding
from BitTorrent import app_name, version, BTFailure
from BitTorrent.platform import get_dot_dir, get_save_dir, locale_root, is_frozen_exe, get_incomplete_data_dir, enforce_shortcut, enforce_association, smart_gettext_and_install
from BitTorrent.zurllib import bind_tracker_connection, set_zurllib_rawserver


downloader_save_options = [
    # General
    'confirm_quit'          ,

    # Appearance
    'progressbar_style'     ,
    'toolbar_text'          ,
    'toolbar_size'          ,

    # Bandwidth
    'max_upload_rate'       ,
    'max_download_rate'     ,

    # Saving
    'save_in'               ,
    'save_incomplete_in'    ,
    'ask_for_save'          ,

    # Network
    'minport'               ,
    'maxport'               ,
    'upnp'                  ,
    'ip'                    ,

    # Misc
    'open_from'             ,
    'geometry'              ,
    'start_maximized'       ,
    'column_order'          ,
    'enabled_columns'       ,
    'column_widths'         ,
    'sort_column'           ,
    'sort_ascending'        ,
    'show_details'          ,
    'details_tab'           ,
    'theme'                 ,

    'donated'               ,
    'notified'              ,
    ]

if os.name == 'nt':
    downloader_save_options.extend([
        # General
        'enforce_association' ,
        'launch_on_startup'   ,
        'start_minimized'     ,
        'minimize_to_tray'    ,
        'close_to_tray'       ,

        # Bandwidth
        'bandwidth_management',
        ])

MAIN_CONFIG_FILE = 'ui_config'
TORRENT_CONFIG_FILE = 'torrent_config'

alt_uiname = {'bittorrent':'btdownloadgui',
              'maketorrent':'btmaketorrentgui',}

def _read_config(filename):
    """Returns a RawConfigParser that has parsed the config file specified by
       the passed filename."""

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
        error_callback(_("Could not permanently save options: ")+str(e))


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
    """This reads the key-value pairs from the specified section in the
       config file and from the common section.  It then places those
       appearing in the defaults into a dict, which is then returned.

       @type defaults: dict
       @param defaults: dict of name-value pairs derived from the
          defaults list for this application (see defaultargs.py).
       @type section: str
       @param section: in the configuration from which to read options.
          So far, the sections have been named after applications, e.g.,
          bittorrent, bittorrent-console, etc.
       @return: a dict containing option-value pairs.
       """
    assert type(defaults)==dict
    assert type(section)==str

    configdir = get_dot_dir()

    if configdir is None:
        return {}

    if not os.path.isdir(configdir):
        try:
            os.mkdir(configdir, 0700)
        except:
            pass

    p = _read_config(os.path.join(configdir, 'config'))  # returns parser.
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


def save_global_config(defaults, section, error_callback,
                       save_options=downloader_save_options):
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
            error_callback(err_str)
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
                    c[name] = value in ('1', 'True', True)
                else:
                    c[name] = type(global_config[name])(value)
            elif name == 'save_as':
                # Backwards compatibility for BitTorrent 4.4 torrent_config file
                c[name] = value
        return c

def remove_torrent_config(path, infohash, error_callback):
    section = infohash.encode('hex')
    filename = os.path.join(path, TORRENT_CONFIG_FILE)
    p = _read_config(filename)
    if p.has_section(section):
        p.remove_section(section)
    _write_config(error_callback, filename, p)

def parse_configuration_and_args(defaults, uiname, arglist=[], minargs=None,
                                 maxargs=None):
    """Given the default option settings and overrides these defaults
       from values read from the config file, and again overrides the
       config file with the arguments that appear in the arglist.

       'defaults' is a list of tuples of the form (optname, value, desc)
       where 'optname' is a string containing the option's name,
       value is the option's value, and desc is the option's description.

       'uiname' is a string specifying the user interface that has been
       created by the caller.  Ex: bittorrent, maketorrent.

       arglist is usually argv[1:], i.e., excluding the name used to
       execute the program.

       minargs specifies the minimum number of arguments that must appear in
       arglist.  If the number of arguments is less than the minimum then
       a BTFailure exception is raised.

       maxargs specifies the maximum number of arguments that can appear
       in arglist.  If the number of arguments exceeds the maximum then
       a BTFailure exception is raised.

       This returns the tuple (config,args) where config is
       a dictionary of (option, value) pairs, and args is the list
       of arguments in arglist after the command-line arguments have
       been removed.

       For example:

          bittorrent-curses.py --save_as lx-2.6.rpm lx-2.6.rpm.torrent --max_upload_rate 0

          returns a (config,args) pair where the
          config dictionary contains many defaults plus
          the mappings
            'save_as': 'linux-2.6.15.tar.gz'
          and
            'max_upload_rate': 0

          The args in the returned pair is
            args= ['linux-2.6.15.tar.gz.torrent']
    """
    assert type(defaults)==list
    assert type(uiname)==str
    assert type(arglist)==list
    assert minargs is None or type(minargs) in (int,long) and minargs>=0
    assert maxargs is None or type(maxargs) in (int,long) and maxargs>=minargs

    defconfig = dict([(name, value) for (name, value, doc) in defaults])
    if arglist[0:] == ['--version']:
        print version
        sys.exit(0)

    if arglist[0:] in (['--help'], ['-h'], ['--usage'], ['-?']):
        parseargs.printHelp(uiname, defaults)
        sys.exit(0)

    presets = get_config(defconfig, uiname)
    config = args = None
    try:
        config, args = parseargs.parseargs(arglist, defaults, minargs, maxargs,
                                           presets)
    except parseargs.UsageException, e:
        print e
        parseargs.printHelp(uiname, defaults)
        sys.exit(0)

    datadir = config.get('data_dir')

    found_4x_config = False

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
                    elif not found_4x_config:
                        # identify 4.x version config file
                        if name in ('start_torrent_behavior',
                                    'seed_forever',
                                    'seed_last_forever',
                                    'next_torrent_ratio',
                                    'next_torrent_time',
                                    'last_torrent_ratio',
                                    ):
                            found_4x_config = True
            parseargs.parse_options(defconfig, values)
            presets.update(values)
            config, args = parseargs.parseargs(arglist, defaults, minargs,
                                               maxargs, presets)

        for d in ('', 'resume', 'metainfo', 'torrents'):
            ddir = os.path.join(datadir, d)
            if not os.path.exists(ddir):
                os.mkdir(ddir, 0700)
            else:
                assert(os.path.isdir(ddir))

    if found_4x_config:
        # version 4.x stored KB/s, < version 4.x stores B/s
        config['max_upload_rate'] *= 1024

    if config.get('language'):
        # this is non-blocking if the language does not exist
        smart_gettext_and_install('bittorrent', locale_root,
                                  languages=[config['language']])

    if config.has_key('bind') and config['bind'] != '':
        bind_tracker_connection(config['bind'])

    if config.has_key('launch_on_startup'):
        enforce_shortcut(config, log_func=sys.stderr.write)

    if os.name == 'nt' and config.has_key('enforce_association'):
        enforce_association()

    if config.get('filesystem_encoding'):
        set_filesystem_encoding(config['filesystem_encoding'])

    if config.has_key('save_in') and config['save_in'] == '' and uiname != 'bittorrent':
        config['save_in'] = get_save_dir()

    if config.has_key('save_incomplete_in') and \
       config['save_incomplete_in'] == '':
        data_dir = get_incomplete_data_dir()
        config['save_incomplete_in'] = data_dir

    if uiname == "test-client" or ( uiname.startswith( "bittorrent") \
       and uiname != 'bittorrent-tracker' ): 
        if not config.has_key('ask_for_save') or not config['ask_for_save']:
            for k in ('save_in', 'save_incomplete_in'):
                if config[k]:
                    # Make sure these puppies exist
                    if not os.access(config[k], os.F_OK):
                        os.makedirs(config[k])

    return config, args
