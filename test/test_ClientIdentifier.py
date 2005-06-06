# The contents of this file are subject to the BitTorrent Open Source License
# Version 1.0 (the License).  You may not copy or use this file, in either
# source code or executable form, except in compliance with the License.  You
# may obtain a copy of the License at http://www.bittorrent.com/license/.
#
# Software distributed under the License is distributed on an AS IS basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied.  See the License
# for the specific language governing rights and limitations under the
# License.
#
# Written by Matt Chisholm

## To use:
##
## * modify btdownloadgui.py or some other client to pass a an open (log)
##   file object as the second argument to the
##   ClientIdentifier.identify_client()
##   method.  It will log all unknown clients.
##
## * run test/test_ClientIdentifier.py with the log file(s) as it's
##   argument(s).  It will report any newly identifiable clients in the log

import sys
sys.path.extend(('..', '.')) #HACK

from BitTorrent import ClientIdentifier

lognames = ['unknown_clients.log']
if len(sys.argv) > 1:
    lognames = sys.argv[1:]


for logname in lognames:
    log = open(logname, 'r')

    line = log.readline()
    next = True

    seenids = {}

    while line and next:
        #print 'l:', line
        #print 'n:', next

        if line[0:4] == '----':
            line = log.readline()
            continue

        peerid = ''

        next = log.readline()
        while next[0:4] != '----':
            peerid += line
            line = next
            next = log.readline()

        peerid += line[:-1]

        if not seenids.has_key(peerid):

            seenids[peerid] = True

            client, version = ClientIdentifier.identify_client(peerid)
            if client != 'unknown':
                print 'identified %s %s\t(from %s)' % (client, version, peerid.encode('hex'))
            elif peerid.startswith(chr(0)*12):
                print 'found peer id starting with 12 nulls'

        line = next
