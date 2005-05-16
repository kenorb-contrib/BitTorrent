## Copyright 2002-2005 Andrew Loewenstern, All Rights Reserved
# see LICENSE.txt for license information

def bucket_stats(l):
    """given a list of khashmir instances, finds min, max, and average number of nodes in tables"""
    max = avg = 0
    min = None
    def count(buckets):
        c = 0
        for bucket in buckets:
            c = c + len(bucket.l)
        return c
    for node in l:
        c = count(node.table.buckets)
        if min == None:
            min = c
        elif c < min:
            min = c
        if c > max:
            max = c
        avg = avg + c
    avg = avg / len(l)
    return {'min':min, 'max':max, 'avg':avg}

def compact_peer_info(ip, port):
    return ''.join([chr(int(i)) for i in ip.split('.')]) + chr((port & 0xFF00) >> 8) + chr(port & 0xFF)

def packPeers(peers):
    return map(lambda a: compact_peer_info(a[0], a[1]), peers)

def reducePeers(peers):
    return reduce(lambda a, b: a + b, peers, '')

def unpackPeers(p):
    peers = []
    if type(p) == type(''):
        for x in xrange(0, len(p), 6):
            ip = '.'.join([str(ord(i)) for i in p[x:x+4]])
            port = (ord(p[x+4]) << 8) | ord(p[x+5])
            peers.append((ip, port, None))
    else:
        for x in p:
            peers.append((x['ip'], x['port'], x.get('peer id')))
    return peers


def compact_node_info(id, ip, port):
    return id + compact_peer_info(ip, port)

def packNodes(nodes):
    return ''.join([compact_node_info(x['id'], x['host'], x['port']) for x in nodes])

def unpackNodes(n):
    nodes = []
    for x in xrange(0, len(n), 26):
        id = n[x:x+20]
        ip = '.'.join([str(ord(i)) for i in n[x+20:x+24]])
        port = (ord(n[x+24]) << 8) | ord(n[x+25])
        nodes.append({'id':id, 'host':ip, 'port': port})
    return nodes  
