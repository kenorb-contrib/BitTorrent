# The contents of this file are subject to the BitTorrent Open Source License
# Version 1.1 (the License).  You may not copy or use this file, in either
# source code or executable form, except in compliance with the License.  You
# may obtain a copy of the License at http://www.bittorrent.com/license/.
#
# Software distributed under the License is distributed on an AS IS basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied.  See the License
# for the specific language governing rights and limitations under the
# License.


# False and True are not distinct from 0 and 1 under Python 2.2,
# and we want to handle boolean options differently.
class MyBool(object):

    def __init__(self, value):
        self.value = value

    def __repr__(self):
        if self.value:
            return 'True'
        return 'False'

    def __nonzero__(self):
        return self.value

MYTRUE = MyBool(True)
MYFALSE = MyBool(False)

import os
### add your favorite here
BAD_LIBC_WORKAROUND_DEFAULT = MYFALSE
if os.name == 'posix':
    if os.uname()[0] in ['Darwin']:
        BAD_LIBC_WORKAROUND_DEFAULT = MYTRUE

MIN_INCOMPLETE = 100
if os.name == 'nt':
    from BitTorrent.platform import win_version_num
    # starting in XP SP2 the incomplete outgoing connection limit was set to 10
    if win_version_num >= (2, 5, 1, 2, 0):
        MIN_INCOMPLETE = 10
    
from BitTorrent import languages

basic_options = [
    ('data_dir', '',
     _("directory under which variable data such as fastresume information "
       "and GUI state is saved. Defaults to subdirectory 'data' of the "
       "bittorrent config directory.")),
    ('filesystem_encoding', '',
     _("character encoding used on the local filesystem. "
       "If left empty, autodetected. "
       "Autodetection doesn't work under python versions older than 2.3")),
    ('language', '',
     _("ISO Language code to use") + ': ' + ', '.join(languages)),
    ]

common_options = [
    ('ip', '',
     _("ip to report to the tracker (has no effect unless you are on the same "
       "local network as the tracker)")),
    ('forwarded_port', 0,
     _("world-visible port number if it's different from the one the client "
       "listens on locally")),
    ('minport', 6881,
     _("minimum port to listen on, counts up if unavailable")),
    ('maxport', 6999,
     _("maximum port to listen on")),
    ('bind', '',
     _("ip to bind to locally")),
    ('display_interval', .5,
     _("seconds between updates of displayed information")),
    ('rerequest_interval', 5 * 60,
     _("minutes to wait between requesting more peers")),
    ('min_peers', 20,
     _("minimum number of peers to not do rerequesting")),
    ('max_initiate', 60,
     _("number of peers at which to stop initiating new connections")),
    ('max_incomplete', MIN_INCOMPLETE,
     _("max number of outgoing incomplete connections")),
    ('max_allow_in', 80,
     _("maximum number of connections to allow, after this new incoming "
       "connections will be immediately closed")),
    ('check_hashes', MYTRUE,
     _("whether to check hashes on disk")),
    ('max_upload_rate', 20,
     _("maximum kB/s to upload at, 0 means no limit")),
    ('min_uploads', 2,
     _("the number of uploads to fill out to with extra optimistic unchokes")),
    ('max_files_open', 50,
     _("the maximum number of files in a multifile torrent to keep open at a "
       "time, 0 means no limit. Used to avoid running out of file descriptors.")),
    ('start_trackerless_client', MYTRUE,
     _("Initialize a trackerless client.  This must be enabled in order to download trackerless torrents.")),
    ('upnp', MYTRUE,
     _("Enable automatic port mapping")+' (UPnP)'),
    ]


rare_options = [
    ('keepalive_interval', 120.0,
     _("number of seconds to pause between sending keepalives")),
    ('download_slice_size', 2 ** 14,
     _("how many bytes to query for per request.")),
    ('max_message_length', 2 ** 23,
     _("maximum length prefix encoding you'll accept over the wire - larger "
       "values get the connection dropped.")),
    ('socket_timeout', 300.0,
     _("seconds to wait between closing sockets which nothing has been "
       "received on")),
    ('timeout_check_interval', 60.0,
     _("seconds to wait between checking if any connections have timed out")),
    ('max_slice_length', 16384,
     _("maximum length slice to send to peers, close connection if a larger "
       "request is received")),
    ('max_rate_period', 20.0,
     _("maximum time interval over which to estimate the current upload and download rates")),
    ('max_rate_period_seedtime', 100.0,
     _("maximum time interval over which to estimate the current seed rate")),
    ('max_announce_retry_interval', 1800,
     _("maximum time to wait between retrying announces if they keep failing")),
    ('snub_time', 30.0,
     _("seconds to wait for data to come in over a connection before assuming "
       "it's semi-permanently choked")),
    ('rarest_first_cutoff', 4,
     _("number of downloads at which to switch from random to rarest first")),
    ('upload_unit_size', 1380,
     _("how many bytes to write into network buffers at once.")),
    ('retaliate_to_garbled_data', MYTRUE,
     _("refuse further connections from addresses with broken or intentionally "
       "hostile peers that send incorrect data")),
    ('one_connection_per_ip', MYTRUE,
     _("do not connect to several peers that have the same IP address")),
    ('peer_socket_tos', 8,
     _("if nonzero, set the TOS option for peer connections to this value")),
    ('bad_libc_workaround', BAD_LIBC_WORKAROUND_DEFAULT,
     _("enable workaround for a bug in BSD libc that makes file reads very slow.")),
    ('tracker_proxy', '',
     _("address of HTTP proxy to use for tracker connections")),
    ('close_with_rst', 0,
     _("close connections with RST and avoid the TCP TIME_WAIT state")),
    ('twisted', -1,
     _("Use Twisted network libraries for network connections. 1 means use twisted, 0 means do not use twisted, -1 means autodetect, and prefer twisted")),
    ]


def get_defaults(ui):
    assert ui in ("bittorrent" , "bittorrent-curses", "bittorrent-console" , 
                  "maketorrent",                      "maketorrent-console",
                                 "launchmany-curses", "launchmany-console" ,
                  )
    r = []

    if ui.startswith('bittorrent') or ui.startswith('launchmany'):
        r.extend(common_options)

    if ui == 'bittorrent':
        r.extend([
            ('save_as', '',
             _("file name (for single-file torrents) or directory name (for "
               "batch torrents) to save the torrent as, overriding the default "
               "name in the torrent. See also --save_in, if neither is "
               "specified the user will be asked for save location")),
            ('advanced', MYFALSE,
             _("display advanced user interface")),
            ('next_torrent_time', 300,
             _("the maximum number of minutes to seed a completed torrent "
               "before stopping seeding")),
            ('next_torrent_ratio', 80,
             _("the minimum upload/download ratio, in percent, to achieve "
               "before stopping seeding. 0 means no limit.")),
            ('last_torrent_ratio', 0,
             _("the minimum upload/download ratio, in percent, to achieve "
               "before stopping seeding the last torrent. 0 means no limit.")),
            ('seed_forever', MYFALSE,
             _("Seed each completed torrent indefinitely "
               "(until the user cancels it)")),
            ('seed_last_forever', MYTRUE,
             _("Seed the last torrent indefinitely "
               "(until the user cancels it)")),
            ('pause', MYFALSE,
             _("start downloader in paused state")),
            ('start_torrent_behavior', 'replace',
             _('specifies how the app should behave when the user manually '
               'tries to start another torrent: "replace" means always replace '
               'the running torrent with the new one, "add" means always add '
               'the running torrent in parallel, and "ask" means ask the user '
               'each time.')),
            ('open_from', '',
             'local directory to look in for .torrent files to open'),
            ('ask_for_save', MYFALSE,
             'whether or not to ask for a location to save downloaded files in'),
            ('start_minimized', MYFALSE,
             _("Start BitTorrent minimized")),
            ('new_version', '',
             _("override the version provided by the http version check "
               "and enable version check debugging mode")),
            ('current_version', '',
             _("override the current version used in the version check "
               "and enable version check debugging mode")),
            ('geometry', '',
             _("specify window size and position, in the format: "
               "WIDTHxHEIGHT+XOFFSET+YOFFSET")),
            ])

        if os.name == 'nt':
            r.extend([
                ('launch_on_startup', MYTRUE,
                 _("Launch BitTorrent when Windows starts")),
                ('minimize_to_tray', MYTRUE,
                 _("Minimize to system tray")),            
            ])

    if ui in ('bittorrent-console', 'bittorrent-curses'):
        r.append(
            ('save_as', '',
             _("file name (for single-file torrents) or directory name (for "
               "batch torrents) to save the torrent as, overriding the "
               "default name in the torrent. See also --save_in")))

    if ui.startswith('bittorrent'):
        r.extend([
            ('max_uploads', -1,
             _("the maximum number of uploads to allow at once. -1 means a "
               "(hopefully) reasonable number based on --max_upload_rate. "
               "The automatic values are only sensible when running one "
               "torrent at a time.")),
            ('save_in', '',
             _("local directory where the torrent contents will be saved. The "
               "file (single-file torrents) or directory (batch torrents) will "
               "be created under this directory using the default name "
               "specified in the .torrent file. See also --save_as.")),
            ('responsefile', '',
             _("deprecated, do not use")),
            ('url', '',
             _("deprecated, do not use")),
            ('ask_for_save', 0,
             _("whether or not to ask for a location to save downloaded files in")),
            ])

    if ui.startswith('launchmany'):
        r.extend([
            ('max_uploads', 6,
             _("the maximum number of uploads to allow at once. -1 means a "
               "(hopefully) reasonable number based on --max_upload_rate. The "
               "automatic values are only sensible when running one torrent at "
               "a time.")),
            ('save_in', '',
             _("local directory where the torrents will be saved, using a "
               "name determined by --saveas_style. If this is left empty "
               "each torrent will be saved under the directory of the "
               "corresponding .torrent file")),
            ('parse_dir_interval', 60,
              _("how often to rescan the torrent directory, in seconds") ),
            ('launch_delay', 0,
             _("wait this many seconds after noticing a torrent before starting it, to avoid race with tracker")),
            ('saveas_style', 4,
              _("How to name torrent downloads: "
                "1: use name OF torrent file (minus .torrent);  " 
                "2: use name encoded IN torrent file;  "
                "3: create a directory with name OF torrent file "
                "(minus .torrent) and save in that directory using name "
                "encoded IN torrent file;  "
                "4: if name OF torrent file (minus .torrent) and name "
                "encoded IN torrent file are identical, use that "
                "name (style 1/2), otherwise create an intermediate "
                "directory as in style 3;  " 
                "CAUTION: options 1 and 2 have the ability to "
                "overwrite files without warning and may present "
                "security issues."
                ) ),
            ('display_path', ui == 'launchmany-console' and MYTRUE or MYFALSE,
              _("whether to display the full path or the torrent contents for "
                "each torrent") ),
            ])

    if ui.startswith('launchmany') or ui == 'maketorrent':
        r.append(
            ('torrent_dir', '',
             _("directory to look for .torrent files (semi-recursive)")),)

    if ui in ('bittorrent-curses', 'bittorrent-console'):
        r.append(
            ('spew', MYFALSE,
             _("whether to display diagnostic info to stdout")))

    if ui.startswith('maketorrent'):
        r.extend([
            ('piece_size_pow2', 18,
             _("which power of two to set the piece size to")),
            ('tracker_name', 'http://my.tracker:6969/announce',
             _("default tracker name")),
            ('tracker_list', '', ''),
            ('use_tracker', MYTRUE,
             _("if false then make a trackerless torrent, instead of "
               "announce URL, use reliable node in form of <ip>:<port> or an "
               "empty string to pull some nodes from your routing table")),
            ])

    r.extend(basic_options)
    
    if ui.startswith('bittorrent') or ui.startswith('launchmany'):
        r.extend(rare_options)
    
    return r
