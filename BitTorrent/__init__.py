# The contents of this file are subject to the BitTorrent Open Source License
# Version 1.0 (the License).  You may not copy or use this file, in either
# source code or executable form, except in compliance with the License.  You
# may obtain a copy of the License at http://www.bittorrent.com/license/.
#
# Software distributed under the License is distributed on an AS IS basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied.  See the License
# for the specific language governing rights and limitations under the
# License.

app_name = "BitTorrent"
version = '3.9.0'

import sys
assert sys.version_info >= (2, 2, 1), "Python 2.2.1 or newer required"
import os

def calc_unix_dirs():
    appdir = '%s-%s'%(app_name, version)
    ip = os.path.join('share', 'pixmaps', appdir)
    dp = os.path.join('share', 'doc'    , appdir)
    return ip, dp

app_root = os.path.split(os.path.abspath(sys.argv[0]))[0]
image_root = os.path.join(app_root, 'images')
doc_root = app_root

if app_root.startswith(os.path.join(sys.prefix,'bin')):
    # I'm installed on *nix
    image_root, doc_root = map( lambda p: os.path.join(sys.prefix, p), calc_unix_dirs() )

del sys


INFO = 0
WARNING = 1
ERROR = 2
CRITICAL = 3

class BTFailure(Exception):
    pass
