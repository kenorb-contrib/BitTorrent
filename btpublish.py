#!/usr/bin/env python

# Written by Bram Cohen
# this file is public domain

from sys import argv, version
assert version >= '2', "Install Python 2.0 or greater"

from BitTorrent.parseargs import parseargs, formatDefinitions
from BitTorrent.publish import publish

configDefinitions = [
    # ( <name in config dict>, <long getopt descript>, <short getopt descript>, <default value>, '''usage''')
    ('max_uploads', 'max-uploads=', None, 10,
        """the maximum number of uploads to allow at once."""),
    ('piece_size', 'piece-size=', None, 2 ** 20,
        """Size of individually hashed pieces of file to be published."""),
    ('max_message_length', 'max-message-length=', None, 2 ** 23,
        """maximum length prefix encoding you'll accept over the wire - larger values get the connection dropped."""),
    ('port', 'port=', 'p:', 0, """Port to listen on, zero indicates choose randomly."""),
    ('max_poll_period', 'max-poll-period=', None, 2.0,
        """Maximum number of seconds to block in calls to select()"""),
    ('ip', 'ip=', 'i:', '',
        """ip to report you have to the publicist."""),
    ('location', 'location=', None, None,
        """The prefix url for announcing to the publicist."""),
    ('postlocation', 'post-location', None, '',
        """post url for announcing to the publicist."""),
    ]

if __name__ == '__main__':
    if len(argv) == 1:
        print "usage: %s [options] <file1> [<file2> [<file3 [...]]]" % argv[0]
        print formatDefinitions(configDefinitions)
    else:
        config, files = parseargs(argv[1:], configDefinitions, 1, 10000)
        publish(config, files)
