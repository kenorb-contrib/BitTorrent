#!/usr/bin/env python

# Written by Bram Cohen
# this file is public domain

from sys import argv, version
assert version >= '2', "Install Python 2.0 or greater"

from BitTorrent.parseargs import parseargs
from BitTorrent.publish import publish

configDefinitions = [
    # ( <name in config dict>, <long getopt descript>, <short getopt descript>, <default value>, '''usage''')
    ('max_uploads', 'max-uploads=', None, 6,
     """the maximum number of uploads to allow at once."""),
    ('piece_size', 'piece-size=', None, 2 ** 20,
     """Size of individually hashed pieces of file to be published."""),
    ('max_message_length', 'max-message-length=', None, None,
     """maximum length prefix encoding you'll accept over the wire - larger values get the connection dropped."""),
    ('port', 'port=', 'p:', 6800, """Port to listen on.  Defaults to 6800.  Will be random in the future."""),
    ('max_poll_period', 'max-poll-period=', None, 2.0,
     """Maximum number of seconds to block in calls to poll()"""),
    ('myip', 'ip=', 'i:', None,
     """ip to report you have to the publicist."""),
    ('location', 'location=', None, None,
     """The prefix url for announcing to the publicist."""),
    ('postlocation', 'post-location', None, '',
     """Optional post url for announcing to the publicist."""),
    (None, 'help', 'h', None, """Display the command line help.""")
    ]

if __name__ == '__main__':
    usageHeading = "usage: %s [options] <file1> [<file2> [<file3 [...]]]" % argv[0]
    configDictionary, files = parseargs(argv[1:], usageHeading, configDefinitions, 1, 10000)
    publish(configDictionary, files)
