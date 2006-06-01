# The contents of this file are subject to the BitTorrent Open Source License
# Version 1.1 (the License).  You may not copy or use this file, in either
# source code or executable form, except in compliance with the License.  You
# may obtain a copy of the License at http://www.bittorrent.com/license/.
#
# Software distributed under the License is distributed on an AS IS basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied.  See the License
# for the specific language governing rights and limitations under the
# License.

# Written by Bram Cohen

import re
from BitTorrent.translation import _

from BitTorrent import BTFailure

allowed_path_re = re.compile(r'^[^/\\.~][^/\\]*$')

ints = (long, int)

def check_info(info, check_paths=True):
    if not isinstance(info, dict):
        raise BTFailure, _("bad metainfo - not a dictionary")
    pieces = info.get('pieces')
    if type(pieces) != str or len(pieces) % 20 != 0 or len(pieces) == 0:
        raise BTFailure, _("bad metainfo - bad pieces key")
    piecelength = info.get('piece length')
    if type(piecelength) not in ints or piecelength <= 0:
        raise BTFailure, _("bad metainfo - illegal piece length")
    name = info.get('name')
    if not isinstance(name, str):
        raise BTFailure, _("bad metainfo - bad name")
    #if not allowed_path_re.match(name):
    #    raise BTFailure, _("name %s disallowed for security reasons") % name
    if info.has_key('files') == info.has_key('length'):
        raise BTFailure, _("single/multiple file mix") 
    if info.has_key('length'): 
        length = info.get('length')
        if type(length) not in ints or length < 0:
            raise BTFailure, _("bad metainfo - bad length") 
    else:
        files = info.get('files')
        if type(files) != list:
            raise BTFailure, _('bad metainfo - "files" is not a list of files')
        for f in files:
            if type(f) != dict:
                raise BTFailure, _("bad metainfo - file entry must be a dict") 
            length = f.get('length')
            if type(length) not in ints or length < 0:
                raise BTFailure, _("bad metainfo - bad length")
            path = f.get('path')
            if type(path) != list or path == []:
                raise BTFailure, _("bad metainfo - bad path")
            for p in path:
                if type(p) != str:
                    raise BTFailure, _("bad metainfo - bad path dir")
                if check_paths and not allowed_path_re.match(p):
                    raise BTFailure, _("path %s disallowed for security reasons") % p
        f = ['/'.join(x['path']) for x in files]
        f.sort()
        i = iter(f)
        try:
            name2 = i.next()
            while True:
                name1 = name2
                name2 = i.next()
                if name2.startswith(name1):
                    if name1 == name2:
                        raise BTFailure, _("bad metainfo - duplicate path")
                    elif name2[len(name1)] == '/':
                        raise BTFailure(_("bad metainfo - name used as both"
                                          "file and subdirectory name"))
        except StopIteration:
            pass

def check_message(message, check_paths=True):
    if type(message) != dict:
        raise BTFailure, _("bad metainfo - wrong object type")
    check_info(message.get('info'), check_paths)
    if type(message.get('announce')) != str and type(message.get('nodes')) != list:
        raise BTFailure, _("bad metainfo - no announce URL string")
    if message.has_key('title') and type(message.get('title')) != str:
        raise BTFailure, _("bad metainfo - bad title - should be a string" )

    if message.has_key('nodes'):
        check_nodes(message.get('nodes'))

    if message.has_key('caches'):
        check_caches(message.get('caches'))

def check_nodes(nodes):
    ## note, these strings need changing
    for node in nodes:
        if type(node) != list:
            raise BTFailure, _("bad metainfo - node is not a list")
        if len(node) != 2:
            raise BTFailure, _("bad metainfo - node list must have only two elements")
        host, port = node
        if type(host) != str:
            raise BTFailure, _("bad metainfo - node host must be a string")
        if type(port) != int:
            raise BTFailure, _("bad metainfo - node port must be an integer")

def check_caches(caches):
    if type(caches) != list:
        raise BTFailure, _("bad metainfo - caches entry is not a list")        
    for entry in caches:
        if type(entry) != dict:
            raise BTFailure, _("bad metainfo - cache entry is not a dict")
        if not entry.has_key("domain"):
            raise BTFailure, _("bad metainfo - cache entry has no domain key")
        if type(entry['domain']) != str:
            raise BTFailure, _("bad metainfo - cache entry domain not a string")            
        if len(entry['domain']) > 255:
            raise BTFailure, _("bad metainfo - cache entry domain too long")            
        if entry.has_key("publisher"):
            if type(entry['publisher']) != str:
                raise BTFailure, _("bad metainfo - cache entry publisher not a string")
            if len(entry['publisher']) > 32:
                raise BTFailure, _("bad metainfo - cache entry publisher longer than 32 chars")                
        
def check_peers(message):
    if type(message) != dict:
        raise BTFailure
    if message.has_key('failure reason'):
        if type(message['failure reason']) != str:
            raise BTFailure, _("failure reason must be a string")
        return
    if message.has_key('warning message'):
        if type(message['warning message']) != str:
            raise BTFailure, _("warning message must be a string")
    peers = message.get('peers')
    if type(peers) == list:
        for p in peers:
            if type(p) != dict:
                raise BTFailure, _("invalid entry in peer list - peer info must be a dict")
            if type(p.get('ip')) != str:
                raise BTFailure, _("invalid entry in peer list - peer ip must be a string")
            port = p.get('port')
            if type(port) not in ints or p <= 0:
                raise BTFailure, _("invalid entry in peer list - peer port must be an integer")
            if p.has_key('peer id'):
                peerid = p.get('peer id')
                if type(peerid) != str or len(peerid) != 20:
                    raise BTFailure, _("invalid entry in peer list - invalid peerid")
    elif type(peers) != str or len(peers) % 6 != 0:
        raise BTFailure, _("invalid peer list")
    interval = message.get('interval', 1)
    if type(interval) not in ints or interval <= 0:
        raise BTFailure, _("invalid announce interval")
    minint = message.get('min interval', 1)
    if type(minint) not in ints or minint <= 0:
        raise BTFailure, _("invalid min announce interval")
    if type(message.get('tracker id', '')) != str:
        raise BTFailure, _("invalid tracker id")
    npeers = message.get('num peers', 0)
    if type(npeers) not in ints or npeers < 0:
        raise BTFailure, _("invalid peer count")
    dpeers = message.get('done peers', 0)
    if type(dpeers) not in ints or dpeers < 0:
        raise BTFailure, _("invalid seed count")
    last = message.get('last', 0)
    if type(last) not in ints or last < 0:
        raise BTFailure, _('invalid "last" entry')
