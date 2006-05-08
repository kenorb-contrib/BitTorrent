# The contents of this file are subject to the BitTorrent Open Source License
# Version 1.1 (the License).  You may not copy or use this file, in either
# source code or executable form, except in compliance with the License.  You
# may obtain a copy of the License at http://www.bittorrent.com/license/.
#
# Software distributed under the License is distributed on an AS IS basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied.  See the License
# for the specific language governing rights and limitations under the
# License.

# Written by Bram Cohen and Greg Hazel

from __future__ import division
from __future__ import generators

import sys
import struct
import logging
from sha import sha
from array import array
from BitTorrent.translation import _

from BitTorrent.obsoletepythonsupport import set
from BitTorrent.sparse_set import SparseSet
from BitTorrent.bitfield import Bitfield
from BitTorrent.defer import Deferred
from BitTorrent.yielddefer import launch_coroutine, _wrap_task
from BitTorrent import BTFailure


NO_PLACE = -1

ALLOCATED = -1
UNALLOCATED = -2
FASTRESUME_PARTIAL = -3

global_logger = logging.getLogger('StorageWrapper')
#global_logger.setLevel(logging.DEBUG)
#global_logger.addHandler(logging.StreamHandler(sys.stdout))

class DataPig(object):
    def __init__(self, read, add_task):
        self.add_task = add_task
        self.read = read
        self.failed_pieces = {}
        self.download_history = {}

    def got_piece(self, index, begin, length, source):
        df = launch_coroutine(_wrap_task(self.add_task),
                              self._got_piece,
                              index, begin, length, source)
        return df

    def _got_piece(self, index, begin, piece, source):
        if index in self.failed_pieces:
            df = self.read(index, len(piece), offset=begin)
            yield df
            data = df.getResult()
            if data != piece:
                if (index in self.download_history and
                    begin in self.download_history[index]):
                    d = self.download_history[index][begin]
                    self.failed_pieces[index].add(d)
        self.download_history.setdefault(index, {})
        self.download_history[index][begin] = source

    def finished_piece(self, index):
        for d in self.download_history[index].itervalues():
            d.good(index)
        del self.download_history[index]
        if index in self.failed_pieces:
            for d in self.failed_pieces[index]:
                d.bad(index)
            del self.failed_pieces[index]        

    def failed_piece(self, index):
        self.failed_pieces[index] = set()
        allsenders = {}
        for d in self.download_history[index].itervalues():
            allsenders[d] = None
        if len(allsenders) == 1:
            culprit = allsenders.keys()[0]
            culprit.bad(index, bump = True)
            del self.failed_pieces[index] # found the culprit already
        
current_version = 1
resume_prefix = 'BitTorrent resume state file, version '
version_string = resume_prefix + str(current_version)

class StorageWrapper(object):

    def __init__(self, storage, config, hashes, piece_size,
                 statusfunc, doneflag, data_flunked,
                 infohash, # needed for partials
                 errorfunc, resumefile,
                 add_task, external_add_task):
        assert len(hashes) > 0
        assert piece_size > 0
        self.initialized = False
        self.numpieces = len(hashes)
        self.add_task = add_task
        self.external_add_task = external_add_task
        self.storage = storage
        self.config = config
        self.doneflag = doneflag
        self.hashes = hashes
        self.piece_size = piece_size
        self.data_flunked = data_flunked
        self.errorfunc = errorfunc
        self.statusfunc = statusfunc
        self.total_length = storage.get_total_length()
        self.amount_left = self.total_length
        self.amount_inactive = self.total_length
        if self.total_length <= piece_size * (self.numpieces - 1):
            raise BTFailure, _("bad data in responsefile - total too small")
        if self.total_length > piece_size * self.numpieces:
            raise BTFailure, _("bad data in responsefile - total too big")

        # If chunks have been requested then inactive_requests has a list
        # of the unrequested chunks. Otherwise the piece is not in the dict.
        self.inactive_requests = {}

        # If chunks have been requested then numactive has the number of
        # chunks which are pending on the network. Otherwise the piece is
        # not in the dict.
        self.numactive = {}
        
        # If chunks have been written and the piece is not complete, than
        # written_partials has a list of the written chunks. Otherwise the
        # piece is not in the dict
        self.written_partials = {}
        
        read = lambda index, length, offset : self._storage_read(self.places[index],
                                                                 length, offset=offset)
        self.datapig = DataPig(read, self.add_task)
        
        self.full_pieces = SparseSet()
        self.endgame = False
        self.have = Bitfield(self.numpieces)
        self.have_set = SparseSet()
        self.checked_pieces = SparseSet()
        self.fastresume = False
        self.fastresume_dirty = False

        self.partial_mark = ("BitTorrent - this part has not been downloaded " +
                             "yet." + infohash +
                             struct.pack('>i', self.config['download_slice_size']))

        if self.numpieces < 32768:
            self.typecode = 'h'
        else:
            self.typecode = 'l'
        # a index => df dict for locking pieces
        self.blocking_pieces = {}
        self.places = array(self.typecode, [NO_PLACE] * self.numpieces)
        check_hashes = self.config['check_hashes']

        self.done_checking_df = Deferred()
        self.lastlen = self._piecelen(self.numpieces - 1)

        global_logger.debug("Loading fastresume...")
        if not check_hashes:
            self.rplaces = array(self.typecode, range(self.numpieces))
            self._initialized(True)
        else:
            try:
                self.read_fastresume(resumefile)
            except Exception, e:
                if resumefile is not None:
                    global_logger.warning("Failed to read fastresume: " + str(e))
                self.rplaces = array(self.typecode, [UNALLOCATED] * self.numpieces)
                # full hashcheck
                df = self.hashcheck_pieces()
                df.addCallback(self._initialized)
                
    def _initialized(self, v):
        self.initialized = v
        global_logger.debug('Initialized')
        self.done_checking_df.callback(v)
                
    ## fastresume
    ############################################################################
    def read_fastresume(self, f):
        version_line = f.readline().strip()
        try:
            resume_version = version_line.split(resume_prefix)[1]
        except Exception, e:
            raise BTFailure(_("Unsupported fastresume file format, "
                              "probably corrupted: %s on (%s)") %
                            (e, repr(version_line)))
        global_logger.debug('Reading fastresume v' + resume_version)
        if resume_version == '1':
            self._read_fastresume_v1(f)
        elif resume_version == '2':
            self._read_fastresume_v2(f)
        else:
            raise BTFailure(_("Unsupported fastresume file format, "
                              "maybe from another client version?"))
        
    def _read_fastresume_v1(self, f):
        # skip a bunch of lines
        amount_done = int(f.readline())
        for b, e, filename in self.storage.ranges:
            line = f.readline()

        # now for the good stuff
        r = array(self.typecode)
        r.fromfile(f, self.numpieces)

        self.rplaces = r

        df = self.checkPieces_v1()
        df.addCallback(self._initialized)

    def checkPieces_v1(self):
        df = launch_coroutine(_wrap_task(self.add_task),
                              self._checkPieces_v1)
        return df
        
    def _checkPieces_v1(self):
        partials = {}

        needs_full_hashcheck = False
        for i in xrange(self.numpieces):

            piece_len = self._piecelen(i)

            t = self.rplaces[i]
            if t >= 0:
                self._markgot(t, i)
            elif t in (ALLOCATED, UNALLOCATED):
                pass
            elif t == FASTRESUME_PARTIAL:
                df = self.storage.read(self.piece_size * i,
                                       piece_len)
                yield df
                try:
                    data = df.getResult()
                except:
                    global_logger.error(_("Bad fastresume info (truncation at piece %d)") % i)
                    needs_full_hashcheck = True
                    i -= 1
                    break                    
                self._check_partial(i, partials, data)
                self.rplaces[i] = ALLOCATED

                # we're shutting down, abort.
                if self.doneflag.isSet():
                    yield False
            else:
                global_logger.error(_("Bad fastresume info (illegal value at piece %d)") % i)
                needs_full_hashcheck = True
                i -= 1
                break

        if needs_full_hashcheck:
            df = self.hashcheck_pieces(i)
            yield df
            r = df.getResult()
            if r == False:
                yield False

        self._realize_partials(partials)            
        yield True

    def write_fastresume(self, resumefile):
        if not self.initialized:
            return

        global_logger.debug('Writing fast resume: %s' % version_string)
        resumefile.write(version_string + '\n')
        # write fake junk
        resumefile.write(str(0) + '\n')
        for b, e, filename in self.storage.ranges:
            resumefile.write(str(0) + ' ' +
                             str(0) + '\n')
        
        # copy the array so as not to screw the current state of things
        rplaces = array(self.rplaces.typecode, list(self.rplaces))
        # Ow. -G
        for i in xrange(self.numpieces):
            if rplaces[i] >= 0 and not self.have[rplaces[i]]:
                rplaces[i] = FASTRESUME_PARTIAL
        rplaces.tofile(resumefile)
        self.fastresume_dirty = False

    ############################################################################

    def _realize_partials(self, partials):
        self.amount_left_with_partials = self.amount_left
        for piece in partials:
            if self.places[piece] < 0:
                pos = partials[piece][0]
                self.places[piece] = pos
                self.rplaces[pos] = piece

    def _markgot(self, piece, pos):
        if self.have[piece]:
            global_logger.debug("double have?")
            if piece != pos:
                return
            self.rplaces[self.places[pos]] = ALLOCATED
            self.places[pos] = self.rplaces[pos] = pos
            return
        self.places[piece] = pos
        self.rplaces[pos] = piece
        self.have[piece] = True
        self.have_set.add(piece)
        plen = self._piecelen(piece)
        self.storage.downloaded(self.piece_size * piece, plen)
        self.amount_left -= plen
        self.amount_inactive -= plen
        assert piece not in self.inactive_requests           

    ## hashcheck    
    ############################################################################
    def hashcheck_pieces(self, begin=0, end=None):
        df = launch_coroutine(_wrap_task(self.add_task),
                              self._hashcheck_pieces,
                              begin, end)
        return df

    def _hashcheck_pieces(self, begin=0, end=None):
        # we need a full reverse-lookup of hashes for out of order compatability
        targets = {}
        for i in xrange(self.numpieces):
            targets[self.hashes[i]] = i
        partials = {}

        if end is None:
            end = self.numpieces

        global_logger.debug('Hashcheck from %d to %d' % (begin, end))

        # TODO: make this work with more than one running at a time
        for i in xrange(begin, end):

            # we're shutting down, abort.
            if self.doneflag.isSet():
                yield False                

            piece_len = self._piecelen(i)

            if not self._waspre(i, piece_len):
                # hole in the file
                continue
                    
            df = self._storage_read(i, piece_len)
            yield df
            try:
                data = df.getResult()
            except:
                #global_logger.debug('Hashcheck error', exc_info=sys.exc_info())
                continue
            
            sh = sha(buffer(data, 0, self.lastlen))
            sp = sh.digest()
            sh.update(buffer(data, self.lastlen))
            s = sh.digest()
            # handle out-of-order pieces
            if s in targets and piece_len == self._piecelen(targets[s]):
                self.checked_pieces.add(targets[s])
                self._markgot(targets[s], i)
            # last piece junk. I'm not even sure this is right.
            elif (not self.have[self.numpieces - 1] and
                  sp == self.hashes[-1] and
                  (i == self.numpieces - 1 or
                   not self._waspre(self.numpieces - 1))):
                self.checked_pieces.add(self.numpieces - 1)
                self._markgot(self.numpieces - 1, i)
            else:
                self._check_partial(i, partials, data)
            self.statusfunc(fractionDone = 1 - self.amount_left /
                            self.total_length)
            
        global_logger.debug('Hashcheck from %d to %d complete.' % (begin, end))

        self._realize_partials(partials)            
        yield True
        

    def hashcheck_piece(self, index, data = None):
        df = launch_coroutine(_wrap_task(self.add_task),
                              self._hashcheck_piece,
                              index, data = data)
        return df

    def _hashcheck_piece(self, index, data = None):
        if not data:
            df = self._storage_read(index, self._piecelen(index))
            yield df
            data = df.getResult()
        if sha(data).digest() != self.hashes[index]:
            yield False
        self.checked_pieces.add(index)
        yield True
    ############################################################################
    
    ## out of order compatability
    ############################################################################
    def _initalloc(self, pos, piece):
        assert self.rplaces[pos] < 0
        assert self.places[piece] == NO_PLACE
        p = self.piece_size * pos
        length = self._piecelen(pos)
        self.places[piece] = pos
        self.rplaces[pos] = piece
        # "if self.rplaces[pos] != ALLOCATED:" to skip extra mark writes
        mark = self.partial_mark + struct.pack('>i', piece)
        mark += chr(0xff) * (self.config['download_slice_size'] - len(mark))
        mark *= (length - 1) // len(mark) + 1
        return self._storage_write(pos, buffer(mark, 0, length))

    def _move_piece(self, oldpos, newpos):
        assert self.rplaces[newpos] < 0
        assert self.rplaces[oldpos] >= 0
        df = self._storage_read(oldpos, self._piecelen(newpos))
        yield df
        data = df.getResult()
        df = self._storage_write(newpos, data)
        yield df
        df.getResult()
        piece = self.rplaces[oldpos]
        self.places[piece] = newpos
        self.rplaces[oldpos] = ALLOCATED
        self.rplaces[newpos] = piece
        if not self.have[piece]:
            return
        data = buffer(data, 0, self._piecelen(piece))
        if sha(data).digest() != self.hashes[piece]:
            raise BTFailure(_("data corrupted on disk - "
                              "maybe you have two copies running?"))
    ############################################################################



    def get_piece_range_for_filename(self, filename):
        begin, end = self.storage.get_byte_range_for_filename(filename)
        begin = int(begin / self.piece_size)
        end = int(end / self.piece_size)
        return begin, end

    def _waspre(self, piece, piece_len=None):
        if piece_len is None:
            piece_len = self._piecelen(piece)
        return self.storage.was_preallocated(piece * self.piece_size, piece_len)

    def _piecelen(self, piece):
        if piece < self.numpieces - 1:
            return self.piece_size
        else:
            return self.total_length - piece * self.piece_size

    def get_total_length(self):
        """Returns the total length of the torrent in bytes."""
        return self.total_length

    def get_num_pieces(self):
        """Returns the total number of pieces in this torrent."""
        return self.numpieces

    def get_amount_left(self):
        """Returns the number of bytes left to download."""
        return self.amount_left

    def do_I_have_anything(self):
        return self.amount_left < self.total_length

    def get_have_list(self):
        return self.have.tostring()

    def do_I_have(self, index):
        return self.have[index]

    def _block_piece(self, index, df):
        self.blocking_pieces[index] = df
        df.addCallback(lambda x: self.blocking_pieces.pop(index))
        return df


    def write(self, index, begin, piece, source):
        df = launch_coroutine(_wrap_task(self.add_task),
                              self._write,
                              index, begin, piece, source)
        return df

    def _write(self, index, begin, piece, source):

        if index in self.blocking_pieces:
            df = self.blocking_pieces[index]
            yield df
            df.getResult()

        if self.places[index] < 0:
            # since old versions of BT wrote out-of-order, we could
            # come across a piece which is misplaced. move it to the
            # correct place.
            if self.rplaces[index] >= 0:
                new_pos = self.rplaces[index]
                df = launch_coroutine(_wrap_task(self.add_task),
                                      self._move_piece, index, new_pos)
                yield self._block_piece(index, df)

            df = self._initalloc(index, index)
            yield self._block_piece(index, df)
            df.getResult()

        df = self.datapig.got_piece(index, begin, piece, source)
        yield df
        df.getResult()

        df = self._storage_write(self.places[index], piece, offset=begin)
        yield df
        df.getResult()
        self.numactive[index] -= 1
        self.written_partials.setdefault(index, []).append((begin, len(piece)))

        hashcheck = False
        if not self.want_requests(index) and not self.numactive[index]:
            hashcheck = True
            df = self.hashcheck_piece(self.places[index])
            yield df
            passed = df.getResult()
            length = self._piecelen(index)
            del self.inactive_requests[index]
            del self.written_partials[index]
            del self.numactive[index]
            self.full_pieces.remove(index)
            if passed:
                self.have[index] = True
                self.have_set.add(index)
                self.storage.downloaded(index * self.piece_size, length)
                self.amount_left -= length

                self.datapig.finished_piece(index)
            else: # hashcheck fail
                self.data_flunked(length, index)
                self.amount_inactive += length

                self.datapig.failed_piece(index)
        yield hashcheck

    def read(self, index, begin, length):
        df = launch_coroutine(_wrap_task(self.add_task),
                              self._read, index, begin, length)
        return df

    def _read(self, index, begin, length):
        if not self.have[index]:
            yield None

        if index in self.blocking_pieces:
            df = self.blocking_pieces[index]
            yield df
            df.getResult()

        if index not in self.checked_pieces:
            df = self.hashcheck_piece(self.places[index])
            yield df
            passed = df.getResult()
            if not passed:
                # TODO: this case should cause a total file hash check and
                # reconnect when done.
                raise BTFailure, _("told file complete on start-up, but piece failed hash check")
        if begin + length > self._piecelen(index):
            yield None
        df = self._storage_read(self.places[index], length, offset=begin)
        yield df
        data = df.getResult()
        yield data

    def _storage_read(self, index, amount, offset=0):
        return self.storage.read(index * self.piece_size + offset, amount)

    def _storage_write(self, index, data, offset=0):
        self.fastresume_dirty = True
        return self.storage.write(index * self.piece_size + offset, data)

    ## partials
    ############################################################################
    def _check_partial(self, pos, partials, data):
        index = None
        missing = False
        marklen = len(self.partial_mark)+4
        for i in xrange(0, len(data) - marklen,
                        self.config['download_slice_size']):
            if data[i:i+marklen-4] == self.partial_mark:
                ind = struct.unpack('>i', data[i+marklen-4:i+marklen])[0]
                if index is None:
                    index = ind
                    parts = []
                if ind >= self.numpieces or ind != index:
                    return
                parts.append(i)
            else:
                missing = True
        if index is not None and missing:
            i += self.config['download_slice_size']
            if i < len(data):
                parts.append(i)
            partials[index] = (pos, parts)

    def _get_partial(self, index):
        assert index in self.inactive_requests, "Why are you calling get_partial if index is not in self.inactive_requests?"

        l = self.inactive_requests[index]

        if len(l) == 0:
            # I have no parts
            return None

        length = self._piecelen(index)
        request_size = self.config['download_slice_size']
        parts = []
        for x in xrange(0, length, request_size):
            partlen = min(request_size, length - x)
            if (x, partlen) not in l:
                parts.append(x)
        return parts

    def _make_partial(self, index, parts):
        length = self._piecelen(index)
        l = []
        self.inactive_requests[index] = l
        x = 0
        self.amount_left_with_partials -= length
        request_size = self.config['download_slice_size']
        for x in xrange(0, length, request_size):
            partlen = min(request_size, length - x)
            if x in parts:
                l.append((x, partlen))
                self.amount_left_with_partials += partlen
            else:
                self.amount_inactive -= partlen
    ############################################################################


    ## request manager stuff
    ############################################################################
    def want_requests(self, index):
        # blah, this is dumb.
        if self.have[index]:
            return False
        # if all requests are pending, we'll have a blank list
        if (index in self.inactive_requests and
            len(self.inactive_requests[index]) == 0):
            return False
        return True

    def new_request(self, index):
        # returns (begin, length)
        # TEMP
        assert not self.have[index]
        if index not in self.inactive_requests:
            self._make_inactive(index)
        self.numactive[index] += 1
        rs = self.inactive_requests[index]
        r = min(rs)
        rs.remove(r)
        if len(rs) == 0:
            self.full_pieces.add(index)
        self.amount_inactive -= r[1]
        if self.amount_inactive == 0:
            self.endgame = True
        return r

    def _make_inactive(self, index):
        # convert 1 to a list of chunks.
        length = self._piecelen(index)
        l = []
        x = 0
        request_size = self.config['download_slice_size']
        while x + request_size < length:
            l.append((x, request_size))
            x += request_size
        l.append((x, length - x))
        self.inactive_requests[index] = l
        self.numactive[index] = 0

    def request_lost(self, index, begin, length):
        if len(self.inactive_requests[index]) == 0:
            self.full_pieces.remove(index)
        self.inactive_requests[index].append((begin, length))
        self.amount_inactive += length
        self.numactive[index] -= 1
    ############################################################################
