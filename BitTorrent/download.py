# The contents of this file are subject to the BitTorrent Open Source License
# Version 1.0 (the License).  You may not copy or use this file, in either
# source code or executable form, except in compliance with the License.  You
# may obtain a copy of the License at http://www.bittorrent.com/license/.
#
# Software distributed under the License is distributed on an AS IS basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied.  See the License
# for the specific language governing rights and limitations under the
# License.

# Written by Bram Cohen and Uoti Urpala

from __future__ import division
# required for python 2.2
from __future__ import generators

import os
import sys
import threading
from sha import sha
from socket import error as socketerror
from random import seed
from time import time
from cStringIO import StringIO
from traceback import print_exc
from math import sqrt
try:
    getpid = os.getpid
except AttributeError:
    def getpid():
        return 1

from BitTorrent.btformats import check_message
from BitTorrent.Choker import Choker
from BitTorrent.Storage import Storage, FilePool
from BitTorrent.StorageWrapper import StorageWrapper
from BitTorrent.Uploader import Upload
from BitTorrent.Downloader import Downloader
from BitTorrent.Encoder import Encoder, SingleportListener
from BitTorrent.RateLimiter import RateLimiter
from BitTorrent.RawServer import RawServer
from BitTorrent.Rerequester import Rerequester
from BitTorrent.DownloaderFeedback import DownloaderFeedback
from BitTorrent.RateMeasure import RateMeasure
from BitTorrent.CurrentRateMeasure import Measure
from BitTorrent.PiecePicker import PiecePicker
from BitTorrent.ConvertedMetainfo import ConvertedMetainfo, set_filesystem_encoding
from BitTorrent import version
from BitTorrent import BTFailure, INFO, WARNING, ERROR, CRITICAL


class Feedback(object):

    def finished(self, torrent):
        pass

    def failed(self, torrent):
        pass

    def error(self, torrent, level, text):
        pass

    def exception(self, torrent, text):
        self.error(torrent, CRITICAL, text)

    def started(self, torrent):
        pass


class Multitorrent(object):

    def __init__(self, config, doneflag, errorfunc, listen_fail_ok=False):
        self.config = dict(config)
        self.rawserver = RawServer(doneflag, config['timeout_check_interval'],
                                   config['timeout'], errorfunc=errorfunc,
                                   bindaddr=config['bind'])
        e = 'maxport less than minport - no ports to check'
        self.serversocket = None
        for listen_port in xrange(config['minport'], config['maxport'] + 1):
            try:
                self.serversocket = self.rawserver.create_serversocket(
                    listen_port, config['bind'], reuse=True,
                    tos=config['peer_socket_tos'])
                break
            except socketerror, e:
                pass
        else:
            if not listen_fail_ok:
                raise BTFailure, "Couldn't open a listening port: " + str(e)
            errorfunc(CRITICAL, "Could not open a listening port: " + str(e) +\
                      ". Check your port range settings.")
            listen_port = 0
        self.filepool = FilePool(config['max_files_open'])
        self.ratelimiter = RateLimiter(self.rawserver.add_task)
        self.ratelimiter.set_parameters(config['max_upload_rate'],
                                        config['upload_unit_size'])
        self.singleport_listener = SingleportListener(listen_port)
        set_filesystem_encoding(config['filesystem_encoding'],
                                                 errorfunc)
        if self.serversocket is not None:
            self.rawserver.start_listening(self.serversocket,
                                           self.singleport_listener)

    def close_listening_socket(self):
        if self.serversocket is not None:
            self.rawserver.stop_listening(self.serversocket)
            self.serversocket.close()

    def start_torrent(self, metainfo, config, feedback, filename):
        torrent = _SingleTorrent(self.rawserver, self.singleport_listener,
                                 self.ratelimiter, self.filepool, config)
        self.rawserver.add_context(torrent)
        def start():
            torrent.start_download(metainfo, feedback, filename)
        self.rawserver.add_task(start, 0, torrent)
        return torrent

    def set_option(self, option, value):
        if option not in self.config or self.config[option] == value:
            return
        if option not in 'max_upload_rate upload_unit_size '\
               'max_files_open'.split():
            return
        self.config[option] = value
        if option == 'max_files_open':
            self.filepool.set_max_files_open(value)
        elif option == 'max_upload_rate':
            self.ratelimiter.set_parameters(value,
                                            self.config['upload_unit_size'])
        elif option == 'upload_unit_size':
            self.ratelimiter.set_parameters(self.config['max_upload_rate'],
                                            value)

    def get_completion(self, config, metainfo, save_path, filelist=False):
        if not config['data_dir']:
            return None
        infohash = metainfo.infohash
        if metainfo.is_batch:
            myfiles = [os.path.join(save_path, f) for f in metainfo.files_fs]
        else:
            myfiles = [save_path]

        if metainfo.total_bytes == 0:
            if filelist:
                return None
            return 1
        try:
            s = Storage(None, None, zip(myfiles, metainfo.sizes),
                        check_only=True)
        except:
            return None
        filename = os.path.join(config['data_dir'], 'resume',
                                infohash.encode('hex'))
        try:
            f = file(filename, 'rb')
        except:
            f = None
        try:
            r = s.check_fastresume(f, filelist, metainfo.piece_length,
                                   len(metainfo.hashes), myfiles)
        except:
            r = None
        if f is not None:
            f.close()
        if r is None:
            return None
        if filelist:
            return r[0] / metainfo.total_bytes, r[1], r[2]
        return r / metainfo.total_bytes


class _SingleTorrent(object):

    def __init__(self, rawserver, singleport_listener, ratelimiter, filepool,
                 config):
        self._rawserver = rawserver
        self._singleport_listener = singleport_listener
        self._ratelimiter = ratelimiter
        self._filepool = filepool
        self.config = dict(config)
        self._storage = None
        self._storagewrapper = None
        self._ratemeasure = None
        self._upmeasure = None
        self._downmeasure = None
        self._encoder = None
        self._rerequest = None
        self._statuscollecter = None
        self._announced = False
        self._listening = False
        self._myfiles = None
        self.started = False
        self.is_seed = False
        self.closed = False
        self.infohash = None
        self.total_bytes = None
        self._doneflag = threading.Event()
        self.finflag = threading.Event()
        self._hashcheck_thread = None
        self._contfunc = None
        self._activity = ('Initial startup', 0)
        self.feedback = None
        self.errors = []

    def start_download(self, *args, **kwargs):
        it = self._start_download(*args, **kwargs)
        def cont():
            try:
                it.next()
            except StopIteration:
                self._contfunc = None
        def contfunc():
            self._rawserver.external_add_task(cont, 0, self)
        self._contfunc = contfunc
        contfunc()

    def _start_download(self, metainfo, feedback, save_path):
        self.feedback = feedback
        config = self.config
        self._set_auto_uploads()

        self.infohash = metainfo.infohash
        self.total_bytes = metainfo.total_bytes
        if not metainfo.reported_errors:
            metainfo.show_encoding_errors(self._error)

        myid = 'M' + version.split()[0].replace('.', '-')
        myid = myid + ('-' * (8-len(myid)))+sha(repr(time())+ ' ' +
                                     str(getpid())).digest()[-6:].encode('hex')
        seed(myid)
        def schedfunc(func, delay):
            self._rawserver.add_task(func, delay, self)
        def externalsched(func, delay):
            self._rawserver.external_add_task(func, delay, self)
        if metainfo.is_batch:
            myfiles = [os.path.join(save_path, f) for f in metainfo.files_fs]
        else:
            myfiles = [save_path]
        self._filepool.add_files(myfiles, self)
        self._myfiles = myfiles
        self._storage = Storage(config, self._filepool, zip(myfiles,
                                                            metainfo.sizes))
        resumefile = None
        if config['data_dir']:
            filename = os.path.join(config['data_dir'], 'resume',
                                    self.infohash.encode('hex'))
            if os.path.exists(filename):
                try:
                    resumefile = file(filename, 'rb')
                    if self._storage.check_fastresume(resumefile) == 0:
                        resumefile.close()
                        resumefile = None
                except Exception, e:
                    self._error(WARNING, 'Could not load fastresume data: '+
                                str(e) + '. Will perform full hash check.')
                    if resumefile is not None:
                        resumefile.close()
                    resumefile = None
        def data_flunked(amount, index):
            self._ratemeasure.data_rejected(amount)
            self._error(INFO, 'piece %d failed hash check, '
                        're-downloading it' % index)
        backthread_exception = []
        def errorfunc(level, text):
            def e():
                self._error(level, text)
            externalsched(e, 0)
        def hashcheck():
            def statusfunc(activity = None, fractionDone = 0):
                if activity is None:
                    activity = self._activity[0]
                self._activity = (activity, fractionDone)
            try:
                self._storagewrapper = StorageWrapper(self._storage,
                     config, metainfo.hashes, metainfo.piece_length,
                     self._finished, statusfunc, self._doneflag, data_flunked,
                     self.infohash, errorfunc, resumefile)
            except:
                backthread_exception.append(sys.exc_info())
            self._contfunc()
        thread = threading.Thread(target = hashcheck)
        thread.setDaemon(False)
        self._hashcheck_thread = thread
        thread.start()
        yield None
        self._hashcheck_thread = None
        if resumefile is not None:
            resumefile.close()
        if backthread_exception:
            a, b, c = backthread_exception[0]
            raise a, b, c

        if self._storagewrapper.amount_left == 0:
            self._finished()
        choker = Choker(config, schedfunc, self.finflag.isSet)
        upmeasure = Measure(config['max_rate_period'],
            config['upload_rate_fudge'])
        downmeasure = Measure(config['max_rate_period'])
        self._upmeasure = upmeasure
        self._downmeasure = downmeasure
        def make_upload(connection, ratelimiter = self._ratelimiter,
                totalup = upmeasure, choker = choker,
                storagewrapper = self._storagewrapper,
                max_slice_length = config['max_slice_length'],
                max_rate_period = config['max_rate_period'],
                fudge = config['upload_rate_fudge']):
            return Upload(connection, ratelimiter, totalup, choker,
                storagewrapper, max_slice_length, max_rate_period, fudge)
        self._ratemeasure = RateMeasure(self._storagewrapper.
                                        amount_left_with_partials)
        picker = PiecePicker(len(metainfo.hashes), config)
        for i in xrange(len(metainfo.hashes)):
            if self._storagewrapper.do_I_have(i):
                picker.complete(i)
        for i in self._storagewrapper.stat_dirty:
            picker.requested(i)
        def kickpeer(connection):
            def kick():
                connection.close()
            schedfunc(kick, 0)
        def banpeer(ip):
            self._encoder.ban(ip)
        downloader = Downloader(config, self._storagewrapper, picker,
            len(metainfo.hashes), downmeasure, self._ratemeasure.data_came_in,
                                kickpeer, banpeer)
        self._encoder = Encoder(make_upload, downloader, choker,
                     len(metainfo.hashes), self._ratelimiter, self._rawserver,
                     config, myid, schedfunc, self.infohash, self)
        reported_port = self.config['forwarded_port']
        if not reported_port:
            reported_port = self._singleport_listener.port
        self._rerequest = Rerequester(metainfo.announce, config,
            schedfunc, self._encoder.how_many_connections,
            self._encoder.start_connection, externalsched,
            self._storagewrapper.get_amount_left, upmeasure.get_total,
            downmeasure.get_total, reported_port, myid,
            self.infohash, self._error, self.finflag, upmeasure.get_rate,
            downmeasure.get_rate, self._encoder.ever_got_incoming)
        self._statuscollecter = DownloaderFeedback(choker, upmeasure.get_rate,
            downmeasure.get_rate, upmeasure.get_total, downmeasure.get_total,
            self._ratemeasure.get_time_left, self._ratemeasure.get_size_left,
            self.total_bytes, self.finflag, downloader, self._myfiles)

        self._singleport_listener.add_torrent(self.infohash, self._encoder)
        self._listening = True

        self._announced = True
        self._rerequest.begin()
        self.started = True
        if not self.finflag.isSet():
            self._activity = ('downloading', 0)
        self.feedback.started(self)

    def got_exception(self, e):
        if isinstance(e, BTFailure):
            self._error(CRITICAL, str(e))
            self._activity = ('download failed: ' + str(e), 0)
        elif isinstance(e, IOError):
            self._error(CRITICAL, 'IO Error ' + str(e))
            self._activity = ('killed by IO error: ' + str(e), 0)
        elif isinstance(e, OSError):
            self._error(CRITICAL, 'OS Error ' + str(e))
            self._activity = ('killed by OS error: ' + str(e), 0)
        else:
            data = StringIO()
            print_exc(file=data)
            self._error(CRITICAL, data.getvalue(), True)
            self._activity = ('killed by internal exception: ' + str(e), 0)
        try:
            self._close()
        except Exception, e:
            self._error(ERROR, 'Additional error when closing down due to '
                        'error: ' + str(e))
        if self.config['data_dir'] and self._storage is not None:
            filename = os.path.join(self.config['data_dir'], 'resume',
                                    self.infohash.encode('hex'))
            if os.path.exists(filename):
                try:
                    os.remove(filename)
                except Exception, e:
                    self._error(WARNING, 'Could not remove fastresume file '
                                'after failure:' + str(e))
        self.feedback.failed(self)

    def _finished(self):
        self.finflag.set()
        # Call self._storage.close() to flush buffers and change files to
        # read-only mode (when they're possibly reopened). Let exceptions
        # from self._storage.close() kill the torrent since files might not
        # be correct on disk if file.close() failed.
        self._storage.close()
        # If we haven't announced yet, normal first announce done later will
        # tell the tracker about seed status.
        self.is_seed = True
        if self._announced:
            self._rerequest.announce(1)
        self._activity = ('seeding', 1)
        self.feedback.finished(self)
        if self.config['check_hashes']:
            self._save_fastresume(True)

    def _save_fastresume(self, on_finish=False):
        if not on_finish and (self.finflag.isSet() or not self.started):
            return
        if not self.config['data_dir']:
            return
        if on_finish:    # self._ratemeasure might not exist yet
            amount_done = self.total_bytes
        else:
            amount_done = self.total_bytes - self._ratemeasure.get_size_left()
        filename = os.path.join(self.config['data_dir'], 'resume',
                                self.infohash.encode('hex'))
        resumefile = None
        try:
            resumefile = file(filename, 'wb')
            self._storage.write_fastresume(resumefile, amount_done)
            self._storagewrapper.write_fastresume(resumefile)
            resumefile.close()
        except Exception, e:
            self._error(WARNING, 'Could not write fastresume data: ' + str(e))
            if resumefile is not None:
                resumefile.close()

    def shutdown(self):
        if self.closed:
            return
        try:
            self._close()
            self._save_fastresume()
            self._activity = ('shut down', 0)
        except Exception, e:
            self.got_exception(e)

    def _close(self):
        if self.closed:
            return
        self.closed = True
        self._rawserver.remove_context(self)
        self._doneflag.set()
        if self._announced:
            self._rerequest.announce(2)
        if self._hashcheck_thread is not None:
            self._hashcheck_thread.join() # should die soon after doneflag set
        if self._myfiles is not None:
            self._filepool.remove_files(self._myfiles)
        if self._listening:
            self._singleport_listener.remove_torrent(self.infohash)
        if self._encoder is not None:
            self._encoder.close_connections()
        if self._storage is not None:
            self._storage.close()

    def get_status(self, spew = False, fileinfo=False):
        if self.started and not self.closed:
            r = self._statuscollecter.get_statistics(spew, fileinfo)
            r['activity'] = self._activity[0]
        else:
            r = dict(zip(('activity', 'fractionDone'), self._activity))
        return r

    def get_total_transfer(self):
        if self._upmeasure is None:
            return (0, 0)
        return (self._upmeasure.get_total(), self._downmeasure.get_total())

    def set_option(self, option, value):
        if self.closed:
            return
        if option not in self.config or self.config[option] == value:
            return
        if option not in 'min_uploads max_uploads max_initiate max_allow_in '\
           'data_dir ip max_upload_rate retaliate_to_garbled_data'.split():
            return
        # max_upload_rate doesn't affect upload rate here, just auto uploads
        self.config[option] = value
        self._set_auto_uploads()

    def _set_auto_uploads(self):
        uploads = self.config['max_uploads']
        rate = self.config['max_upload_rate']
        if uploads > 0:
            pass
        elif rate <= 0:
            uploads = 7 # unlimited, just guess something here...
        elif rate < 9:
            uploads = 2
        elif rate < 15:
            uploads = 3
        elif rate < 42:
            uploads = 4
        else:
            uploads = int(sqrt(rate * .6))
        self.config['max_uploads_internal'] = uploads

    def _error(self, level, text, exception=False):
        self.errors.append((time(), level, text))
        if exception:
            self.feedback.exception(self, text)
        else:
            self.feedback.error(self, level, text)
