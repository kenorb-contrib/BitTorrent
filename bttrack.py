#!/usr/bin/env python

# Written by Bram Cohen
# see LICENSE.txt for license information

from sys import argv
from BitTorrent.parseargs import parseargs, formatDefinitions
from BitTorrent.track import track

defaults = [
    ('port', 'p', 80, "Port to listen on."),
    ('ip', 'i', None, "ip to report you have to downloaders."),
    ('file', 's', None, 'file to store state in'),
    ('dfile', 'd', None, 'file to store recent downloader info in'),
    ('logfile', None, None, 'file to write BitTorrent announcements to'),
    ('bind', None, '', 'ip to bind to locally'),
    ]

def run(args):
    if len(args) == 0:
        print formatDefinitions(defaults, 80)
    try:
        config, files = parseargs(args, defaults, 0, 0)
        track(config['ip'], config['port'], config['file'], 
            config['dfile'], config['logfile'], config['bind'])
    except ValueError, e:
        print 'error: ' + str(e)
        print 'run with no arguments for parameter explanations'

if __name__ == '__main__':
    run(argv[1:])
