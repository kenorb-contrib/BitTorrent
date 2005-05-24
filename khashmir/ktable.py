## Copyright 2002-2003 Andrew Loewenstern, All Rights Reserved
# see LICENSE.txt for license information

import time
from bisect import *
from types import *

import khash as hash
import const
from const import K, HASH_LENGTH, NULL_ID, MAX_FAILURES
from node import Node

class KTable:
    """local routing table for a kademlia like distributed hash table"""
    def __init__(self, node):
        # this is the root node, a.k.a. US!
        self.node = node
        self.buckets = [KBucket([], 0L, 2L**HASH_LENGTH)]
        self.insertNode(node)
        
    def _bucketIndexForInt(self, num):
        """the index of the bucket that should hold int"""
        return bisect_left(self.buckets, num)
    
    def findNodes(self, id, invalid=True):
        """
            return K nodes in our own local table closest to the ID.
        """
        
        if isinstance(id, str):
            num = hash.intify(id)
        elif isinstance(id, Node):
            num = id.num
        elif isinstance(id, int) or isinstance(id, long):
            num = id
        else:
            raise TypeError, "findNodes requires an int, string, or Node"
            
        nodes = []
        i = self._bucketIndexForInt(num)
        
        # if this node is already in our table then return it
        try:
            index = self.buckets[i].l.index(num)
        except ValueError:
            pass
        else:
            return [self.buckets[i].l[index]]
            
        # don't have the node, get the K closest nodes
        nodes = nodes + self.buckets[i].l
        if not invalid:
            nodes = [a for a in nodes if not a.invalid]
        if len(nodes) < K:
            # need more nodes
            min = i - 1
            max = i + 1
            while len(nodes) < K and (min >= 0 or max < len(self.buckets)):
                #ASw: note that this requires K be even
                if min >= 0:
                    nodes = nodes + self.buckets[min].l
                if max < len(self.buckets):
                    nodes = nodes + self.buckets[max].l
                min = min - 1
                max = max + 1
                if not invalid:
                    nodes = [a for a in nodes if not a.invalid]

        nodes.sort(lambda a, b, num=num: cmp(num ^ a.num, num ^ b.num))
        return nodes[:K]
        
    def _splitBucket(self, a):
        diff = (a.max - a.min) / 2
        b = KBucket([], a.max - diff, a.max)
        self.buckets.insert(self.buckets.index(a.min) + 1, b)
        a.max = a.max - diff
        # transfer nodes to new bucket
        for anode in a.l[:]:
            if anode.num >= a.max:
                a.l.remove(anode)
                b.l.append(anode)
    
    def replaceStaleNode(self, stale, new):
        """this is used by clients to replace a node returned by insertNode after
        it fails to respond to a Pong message"""
        i = self._bucketIndexForInt(stale.num)
        try:
            it = self.buckets[i].l.index(stale.num)
        except ValueError:
            if new:
                return self.insertNode(new)
            else:
                return
    
        del(self.buckets[i].l[it])
        if new:
            self.buckets[i].l.append(new)
            self.buckets[i].touch()
        return
    
    def insertNode(self, node, contacted=1, nocheck=False):
        """ 
        this insert the node, returning None if successful, returns the oldest node in the bucket if it's full
        the caller responsible for pinging the returned node and calling replaceStaleNode if it is found to be stale!!
        contacted means that yes, we contacted THEM and we know the node is reachable
        """
        assert node.id != NULL_ID
        if node.id == self.node.id: return

        if contacted:
            node.updateLastSeen()

        # get the bucket for this node
        i = self. _bucketIndexForInt(node.num)
        # check to see if node is in the bucket already
        try:
            it = self.buckets[i].l.index(node.num)
        except ValueError:
            # no
            pass
        else:
            if contacted:
                # move node to end of bucket
                xnode = self.buckets[i].l[it]
                del(self.buckets[i].l[it])
                # note that we removed the original and replaced it with the new one
                # utilizing this nodes new contact info
                self.buckets[i].l.append(node)
                self.buckets[i].touch()
            return
        
        # we don't have this node, check to see if the bucket is full
        if len(self.buckets[i].l) < K:
            # no, append this node and return
            self.buckets[i].l.append(node)
            self.buckets[i].touch()
            return

        # full bucket, check to see if any nodes are invalid
        invalid = [n for n in self.buckets[i].l if n.invalid]
        if len(invalid) and not nocheck:
            def ls(a, b):
                if a.lastSeen > b.lastSeen:
                    return 1
                elif b.lastSeen > a.lastSeen:
                    return -1
                return 0
            invalid.sort(ls)
            if invalid[0].lastSeen == 0 and invalid[0].fails < MAX_FAILURES:
                return invalid[0]
            else:
                return self.replaceStaleNode(invalid[0], node)

        
        # bucket is full and all nodes are valid, check to see if self.node is in the bucket
        if not (self.buckets[i].min <= self.node < self.buckets[i].max):
            self.buckets[i].sort()
            return self.buckets[i].l[0]
        
        # this bucket is full and contains our node, split the bucket
        if len(self.buckets) >= HASH_LENGTH:
            # our table is FULL, this is really unlikely
            print "Hash Table is FULL!  Increase K!"
            return
            
        self._splitBucket(self.buckets[i])
        
        # now that the bucket is split and balanced, try to insert the node again
        return self.insertNode(node, contacted)
    
    def justSeenNode(self, id):
        """call this any time you get a message from a node
        it will update it in the table if it's there """
        try:
            n = self.findNodes(id)[0]
        except IndexError:
            return None
        else:
            tstamp = n.lastSeen
            n.updateLastSeen()
            return tstamp
    
    def invalidateNode(self, n):
        """
            forget about node n - use when you know that node is invalid
        """
        n.invalid = True
    
    def nodeFailed(self, node):
        """ call this when a node fails to respond to a message, to invalidate that node """
        try:
            n = self.findNodes(node.num)[0]
        except IndexError:
            return None
        else:
            if n.msgFailed() >= const.MAX_FAILURES:
                self.invalidateNode(n)
                        
class KBucket:
    __slots__ = ('min', 'max', 'lastAccessed')
    def __init__(self, contents, min, max):
        self.l = contents
        self.min = min
        self.max = max
        self.lastAccessed = time.time()
        
    def touch(self):
        self.lastAccessed = time.time()

    def lacmp(self, a, b):
        if a.lastSeen > b.lastSeen:
            return 1
        elif b.lastSeen > a.lastSeen:
            return -1
        return 0
        
    def sort(self):
        self.l.sort(self.lacmp)
        
    def getNodeWithInt(self, num):
        if num in self.l: return num
        else: raise ValueError
        
    def __repr__(self):
        return "<KBucket %d items (%d to %d)>" % (len(self.l), self.min, self.max)
    
    ## Comparators    
    # necessary for bisecting list of buckets with a hash expressed as an integer or a distance
    # compares integer or node object with the bucket's range
    def __lt__(self, a):
        if isinstance(a, Node): a = a.num
        return self.max <= a
    def __le__(self, a):
        if isinstance(a, Node): a = a.num
        return self.min < a
    def __gt__(self, a):
        if isinstance(a, Node): a = a.num
        return self.min > a
    def __ge__(self, a):
        if isinstance(a, Node): a = a.num
        return self.max >= a
    def __eq__(self, a):
        if isinstance(a, Node): a = a.num
        return self.min <= a and self.max > a
    def __ne__(self, a):
        if isinstance(a, Node): a = a.num
        return self.min >= a or self.max < a


### UNIT TESTS ###
import unittest

class TestKTable(unittest.TestCase):
    def setUp(self):
        self.a = Node().init(hash.newID(), 'localhost', 2002)
        self.t = KTable(self.a)

    def testAddNode(self):
        self.b = Node().init(hash.newID(), 'localhost', 2003)
        self.t.insertNode(self.b)
        self.assertEqual(len(self.t.buckets[0].l), 1)
        self.assertEqual(self.t.buckets[0].l[0], self.b)

    def testRemove(self):
        self.testAddNode()
        self.t.invalidateNode(self.b)
        self.assertEqual(len(self.t.buckets[0].l), 0)

    def testFail(self):
        self.testAddNode()
        for i in range(const.MAX_FAILURES - 1):
            self.t.nodeFailed(self.b)
            self.assertEqual(len(self.t.buckets[0].l), 1)
            self.assertEqual(self.t.buckets[0].l[0], self.b)
            
        self.t.nodeFailed(self.b)
        self.assertEqual(len(self.t.buckets[0].l), 0)


if __name__ == "__main__":
    unittest.main()
