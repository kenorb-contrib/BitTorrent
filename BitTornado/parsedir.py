# Written by John Hoffman and Uoti Urpala
# see LICENSE.txt for license information
from bencode import bencode, bdecode
from BT1.btformats import check_info
from os.path import exists, isfile
from sha import sha
import sys, os

try:
    True
except:
    True = 1
    False = 0

NOISY = False

def _errfunc(x):
    print ":: "+x

def parsedir(dir, parsed, files, blocked,
             exts = ['.torrent'], return_metainfo = False, errfunc = _errfunc):
    if NOISY:
        errfunc('checking dir')
    dirs_to_check = [dir]
    new_files = {}
    new_blocked = {}
    torrent_type = {}
    while dirs_to_check:    # first, recurse directories and gather torrents
        dir = dirs_to_check.pop()
        newtorrents = False
        for f in os.listdir(dir):
            newtorrent = None
            for ext in exts:
                if f[-len(ext):] == ext:
                    newtorrent = ext[1:]
            if newtorrent:
                newtorrents = True
                p = os.path.join(dir,f)
                new_files[p] = [[os.path.getmtime(p), os.path.getsize(p)], 0]
                torrent_type[p] = newtorrent
        if not newtorrents:
            for f in os.listdir(dir):
                p = os.path.join(dir,f)
                if os.path.isdir(p):
                    dirs_to_check.append(p)

    new_parsed = {}
    to_add = []
    added = {}
    removed = {}
    for p,v in new_files.items():   # then, re-add old items and check for changes
        result = files.get(p)
        if not result:
            to_add.append(p)
            continue
        h = result[1]
        if result[0] == v[0]:
            if h:
                new_parsed[h] = parsed[h]
                new_files[p] = result
            elif blocked.has_key(p):
                new_files[p] = result
            else:
                to_add.append(p)    # try adding anyway, to stimulate an error
            continue
        if NOISY:
            errfunc('removing '+p+' (will re-add)')
        removed[h] = parsed[h]
        to_add.append(p)

    to_add.sort()    
    for p in to_add:                # then, parse new and changed torrents
        new_file = new_files[p]
        v = new_file[0]
        if NOISY:
            errfunc('adding '+p)
        try:
            ff = open(p, 'rb')
            d = bdecode(ff.read())
            ff.close()
            check_info(d['info'])
            h = sha(bencode(d['info'])).digest()
            if new_parsed.has_key(h):
                if blocked.get(p) != v:
                    errfunc('**warning** '+
                        p +' is a duplicate torrent for '+new_parsed[h]['path'])
                new_blocked[p] = v
                continue

            a = {}
            a['path'] = p
            f = os.path.basename(p)
            a['file'] = f
            a['type'] = torrent_type[p]
            i = d['info']
            l = 0
            nf = 0
            if i.has_key('length'):
                l = i.get('length',0)
                nf = 1
            elif i.has_key('files'):
                for li in i['files']:
                    nf += 1
                    if li.has_key('length'):
                        l += li['length']
            a['numfiles'] = nf
            a['length'] = l
            a['name'] = i.get('name', f)
            def setkey(k, d = d, a = a):
                if d.has_key(k):
                    a[k] = d[k]
            setkey('failure reason')
            setkey('warning message')
            setkey('announce-list')
            if return_metainfo:
                a['metainfo'] = d
        except:
            if blocked.get(p) != v:
                errfunc('**warning** '+p+' has errors')
            new_blocked[p] = v
            continue
        if NOISY:
            errfunc('... successful')
        new_file[1] = h
        new_parsed[h] = a
        added[h] = a

    for p,v in files.items():       # and finally, mark removed torrents
        if not new_files.has_key(p):
            if NOISY:
                errfunc('removing '+p)
            removed[v[1]] = parsed[v[1]]

    if NOISY:
        errfunc('done checking')
    return (new_parsed, new_files, new_blocked, added, removed)