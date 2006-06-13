# The contents of this file are subject to the BitTorrent Open Source License
# Version 1.0 (the License).  You may not copy or use this file, in either
# source code or executable form, except in compliance with the License.  You
# may obtain a copy of the License at http://www.bittorrent.com/license/.
#
# Software distributed under the License is distributed on an AS IS basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied.  See the License
# for the specific language governing rights and limitations under the
# License.

# Written by Matt Chisholm

import os
from BitTorrent.hash import sha
from time import time
try:
    getpid = os.getpid
except AttributeError:
    def getpid():
        return 1

from BitTorrent import version

def make_id():
    myid = 'M' + version.split()[0].replace('.', '-')
    padded = myid[:8] + '-' * (8-len(myid))
    myid = padded + sha(repr(time()) + ' ' +
                        str(getpid())).digest()[-6:].encode('hex')
    return myid
