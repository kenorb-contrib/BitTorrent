#!/usr/bin/env python

# Written by Bram Cohen
# this file is public domain

from BitTorrent.download import downloadurl
from BitTorrent.parseargs import parseargs, formatDefinitions
from threading import Event
from sys import argv, version
assert version >= '2', "Install Python 2.0 or greater"

configDefinitions = [
    # ( <name in config dict>, <long getopt descript>, <short getopt descript>, <default value>, '''usage''')
    ('unthrottle_diff', 'unthrottle-diff=', None, 2 ** 23,
        """How much a peer's balance must exceed that of the lowest balance current downloader before they get unthrottled. Will be removed after the switch from balances to transfer rates."""),
    ('rethrottle_diff', 'rethrottle-diff=', None, 2 ** 20,
        """the point at which unthrottle_diff is undone, will be removed after the switch to transfer rates."""),
    ('max_uploads', 'max-uploads=', None, 3,
        """the maximum number of uploads to allow at once."""),
    ('max_downloads', 'max-downloads=', None, 6,
        """the maximum number of downloads to do at once."""),
    ('download_chunk_size', 'download-chunk-size=', None, 2 ** 15,
        """How many bytes to query for per request."""),
    ('request_backlog', 'request-backlog=', None, 5,
        """how many requests to keep in a single pipe at once."""),
    ('max_message_length', 'max-message-length=', None, 2 ** 23,
        """maximum length prefix encoding you'll accept over the wire - larger values get the connection dropped."""),
    ('max_poll_period', 'max-poll-period=', None, 2.0,
        """Maximum number of seconds to block in calls to select()"""),
    ('port', 'port=', 'p:', 0,
        """Port to listen on, zero means choose randomly"""),
    ('ip', 'ip=', 'i:', '',
        """ip to report you have to the publicist."""),
    ]

def display(text, type):
    print '\n\n\n\n' + text

if __name__ == '__main__':
    if len(argv) == 1:
        print "usage: %s [options] <url> <file>" % argv[0]
        print formatDefinitions(configDefinitions)
    else:
        config, files = parseargs(argv[1:], configDefinitions, 2, 2) 
        downloadurl(files[0], lambda x: files[1], display, Event(), config)
