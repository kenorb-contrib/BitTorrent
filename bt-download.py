#!/usr/bin/env python

# Written by Bram Cohen
# this file is public domain

from BitTorrent.download import downloadurl
from BitTorrent.parseargs import parseargs
from Tkinter import Tk
from tkFileDialog import asksaveasfilename
from sys import argv, version
assert version >= '2', "Install Python 2.0 or greater"

def getname(default):
    root = Tk()
    root.withdraw()
    return asksaveasfilename(initialfile = default)

configDefinitions = [
    # ( <name in config dict>, <long getopt descript>, <short getopt descript>, <default value>, '''usage''')
    ('unthrottle_diff', 'unthrottle-diff=', None, 2 ** 23,
     """How much a peer's balance must exceed that of the lowest balance current downloader before they get unthrottled.  Currently defaults to 2 ** 23.  Will be removed after the switch from balances to transfer rates."""),
    ('rethrottle_diff', 'rethrottle-diff=', None, 2 ** 20,
     """the point at which unthrottle_diff is undone. Defaults to 2 ** 20, will be removed after the switch to transfer rates."""),
    ('max_uploads', 'max-uploads=', None, 2,
     """the maximum number of uploads to allow at once. Default is 2, will be changed to 3."""),
    ('max_downloads', 'max-downloads=', None, 4,
     """the maximum number of downloads to do at once. Default is 4, will be increased."""),
    ('download_chunk_size', 'download-chunk-size=', None, 2 ** 15,
     """How many bytes to query for per requests. Defaults to 2 ** 15."""),
    ('request_backlog', 'request-backlog=', None, 5,
     """how many requests to keep in a single pipe at once. Defaults to 5."""),
    ('min_fast_reconnect', 'min-fast-reconnect=', None, None,
     """Minimum number of seconds to wait to try to reconnect a locally initiated connection which dropped."""),
    ('max_fast_reconnect', 'max-fast-reconnect=', None, None,
     """Maximum number of seconds to wait to try to reconnect a locally initiated connection which dropped."""),
    ('max_message_length', 'max-message-length=', None, None,
     """maximum length prefix encoding you'll accept over the wire - larger values get the connection dropped."""),
    ('port', 'port=', 'p:', 6800, """Port to listen on.  Defaults to 6800.  Will be random in the future."""),
    ('socket_poll_period', 'socket-poll-period=', None, None,
     """Number of milliseconds to block in calls to poll()"""),
    ('myip', 'ip=', 'i:', None,
     """ip to report you have to the publicist."""),
    (None, 'help', 'h', None, """Display the command line help.""")
    ]

if __name__ == '__main__':
    usageHeading = "usage: %s [options] <url>" % argv[0]
    # require 1 and only 1 file
    configDictionary, files = parseargs(argv[1:], usageHeading, configDefinitions, 1, 1) 
    downloadurl(files[0], getname, configDictionary)
