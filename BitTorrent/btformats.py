# Written by Bram Cohen
# see LICENSE.txt for license information

from types import StringType, LongType, ListType, DictType
from re import compile

reg = compile(r'^[^/\\.~][^/\\]*$')

def check_info(info):
    if type(info) != DictType:
        raise ValueError
    pieces = info.get('pieces')
    if type(pieces) != StringType or len(pieces) % 20 != 0:
        raise ValueError
    piecelength = info.get('piece length')
    if type(piecelength) != LongType or piecelength <= 0:
        raise ValueError
    name = info.get('name')
    if type(name) != StringType or not reg.match(name):
        raise ValueError
    if info.has_key('files') == info.has_key('length'):
        raise ValueError, 'single/multiple file mix'
    if info.has_key('length'):
        length = info.get('length')
        if type(length) != LongType or length < 0:
            raise ValueError
    else:
        files = info.get('files')
        if type(files) != ListType:
            raise ValueError
        for f in files:
            if type(f) != DictType:
                raise ValueError
            length = f.get('length')
            if type(length) != LongType or length <= 0:
                raise ValueError
            path = f.get('path')
            if type(path) != ListType or path == []:
                raise ValueError
            for p in path:
                if type(p) != StringType or not reg.match(p):
                    raise ValueError
        for i in xrange(len(files)):
            for j in xrange(i):
                if files[i]['path'] == files[j]['path']:
                    raise ValueError

def check_message(message):
    if type(message) != DictType:
        raise ValueError
    check_info(message.get('info'))
    if type(message.get('announce')) != StringType:
        raise ValueError

def check_peers(message):
    if type(message) != DictType:
        raise ValueError
    if message.has_key('failure reason'):
        if type(message['failure reason']) != StringType:
            raise ValueError
        return
    peers = message.get('peers')
    if type(peers) != ListType:
        raise ValueError
    for p in peers:
        if type(p) != DictType:
            raise ValueError
        if type(p.get('ip')) != StringType:
            raise ValueError
        port = p.get('port')
        if type(port) != LongType or p <= 0:
            raise ValueError
        id = p.get('peer id')
        if type(id) != StringType or len(id) != 20:
            raise ValueError
    interval = message.get('interval')
    if type(interval) != LongType or interval <= 0:
        raise ValueError
    
