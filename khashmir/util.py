# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from struct import pack, unpack

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
    return pack('!BBBBH', *([int(i) for i in ip.split('.')] + [port]))

def packPeers(peers):
    return map(lambda a: compact_peer_info(a[0], a[1]), peers)

def reducePeers(peers):
    return reduce(lambda a, b: a + b, peers, '')

def unpackPeers(p):
    peers = []
    if type(p) == type(''):
        for x in xrange(0, len(p), 6):
            ip = '.'.join([str(ord(i)) for i in p[x:x+4]])
            port = unpack('!H', p[x+4:x+6])[0]
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
        port = unpack('!H', n[x+24:x+26])[0]
        nodes.append({'id':id, 'host':ip, 'port': port})
    return nodes  
