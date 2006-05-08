# The contents of this file are subject to the BitTorrent Open Source License
# Version 1.1 (the License).  You may not copy or use this file, in either
# source code or executable form, except in compliance with the License.  You
# may obtain a copy of the License at http://www.bittorrent.com/license/.
#
# Software distributed under the License is distributed on an AS IS basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied.  See the License
# for the specific language governing rights and limitations under the
# License.

# Written by Uoti Urpala

# required for Python 2.2
from __future__ import generators

import os
import sys
import logging
from sha import sha

from BitTorrent.translation import _
from BitTorrent.obsoletepythonsupport import *

from BitTorrent.bencode import bencode
from BitTorrent import btformats
from BitTorrent import BTFailure, filesystem_encoding, InfoHashType


WINDOWS_UNSUPPORTED_CHARS ='"*/:<>?\|'
windows_translate = [chr(i) for i in range(256)]
for x in WINDOWS_UNSUPPORTED_CHARS:
    windows_translate[ord(x)] = '-'
windows_translate = ''.join(windows_translate)

noncharacter_translate = {}
for i in xrange(0xD800, 0xE000):
    noncharacter_translate[i] = ord('-')
for i in xrange(0xFDD0, 0xFDF0):
    noncharacter_translate[i] = ord('-')
for i in (0xFFFE, 0xFFFF):
    noncharacter_translate[i] = ord('-')

del x, i

def generate_names(name, is_dir):
    if is_dir:
        prefix = name + '.'
        suffix = ''
    else:
        pos = name.rfind('.')
        if pos == -1:
            pos = len(name)
        prefix = name[:pos] + '.'
        suffix = name[pos:]
    i = 0
    while True:
        yield prefix + str(i) + suffix
        i += 1

class ConvertedMetainfo(object):

    def __init__(self, metainfo):
        self.bad_torrent_wrongfield = False
        self.bad_torrent_unsolvable = False
        self.bad_torrent_noncharacter = False
        self.bad_conversion = False
        self.bad_windows = False
        self.bad_path = False
        self.reported_errors = False
        self.is_batch = False
        self.orig_files = None
        self.files_fs = None
        self.total_bytes = 0
        self.sizes = []
        self.comment = None
        self.title = None          # descriptive title text for whole torrent
        self.creation_date = None
        self.metainfo = metainfo

        btformats.check_message(metainfo, check_paths=False)
        info = metainfo['info']
        if info.has_key('length'):
            self.total_bytes = info['length']
            self.sizes.append(self.total_bytes)
        else:
            self.is_batch = True
            r = []
            self.orig_files = []
            self.sizes = []
            i = 0
            for f in info['files']:
                l = f['length']
                self.total_bytes += l
                self.sizes.append(l)
                path = self._get_attr_utf8(f, 'path')
                for x in path:
                    if not btformats.allowed_path_re.match(x):
                        if l > 0:
                            raise BTFailure(_("Bad file path component: ")+x)
                        # BitComet makes bad .torrent files with empty
                        # filename part
                        self.bad_path = True
                        break
                else:
                    p = []
                    for x in path:
                        p.append((self._enforce_utf8(x), x))
                    path = p
                    self.orig_files.append('/'.join([x[0] for x in path]))
                    k = []
                    for u,o in path:
                        tf2 = self._to_fs_2(u)
                        k.append((tf2, u, o))
                    r.append((k,i))
                    i += 1
            # If two or more file/subdirectory names in the same directory
            # would map to the same name after encoding conversions + Windows
            # workarounds, change them. Files are changed as
            # 'a.b.c'->'a.b.0.c', 'a.b.1.c' etc, directories or files without
            # '.' as 'a'->'a.0', 'a.1' etc. If one of the multiple original
            # names was a "clean" conversion, that one is always unchanged
            # and the rest are adjusted.
            r.sort()
            self.files_fs = [None] * len(r)
            prev = [None]
            res = []
            stack = [{}]
            for x in r:
                j = 0
                x, i = x
                while x[j] == prev[j]:
                    j += 1
                del res[j:]
                del stack[j+1:]
                name = x[j][0][1]
                if name in stack[-1]:
                    for name in generate_names(x[j][1], j != len(x) - 1):
                        name = self._to_fs(name)
                        if name not in stack[-1]:
                            break
                stack[-1][name] = None
                res.append(name)
                for j in xrange(j + 1, len(x)):
                    name = x[j][0][1]
                    stack.append({name: None})
                    res.append(name)
                self.files_fs[i] = os.path.join(*res)
                prev = x

        self.name = self._get_field_utf8(info, 'name')
        self.name_fs = self._to_fs(self.name)
        self.piece_length = info['piece length']
        self.is_trackerless = False
        if metainfo.has_key('announce-list'):
            self.announce_list = metainfo['announce-list']
        else:
            self.announce_list = None
        if metainfo.has_key('announce'):
            self.announce = metainfo['announce']
        elif metainfo.has_key('nodes'):
            self.is_trackerless = True
            self.nodes = metainfo['nodes']

        if metainfo.has_key('title'):
            self.title = metainfo['title']
        if metainfo.has_key('comment'):
            self.comment = metainfo['comment']
        if metainfo.has_key('creation date'):
            self.creation_date = metainfo['creation date']

        self.hashes = [info['pieces'][x:x+20] for x in xrange(0,
            len(info['pieces']), 20)]
        self.infohash = InfoHashType(sha(bencode(info)).digest())

    def show_encoding_errors(self, errorfunc):
        self.reported_errors = True
        if self.bad_torrent_unsolvable:
            errorfunc(logging.ERROR,
                      _("This .torrent file has been created with a broken "
                        "tool and has incorrectly encoded filenames. Some or "
                        "all of the filenames may appear different from what "
                        "the creator of the .torrent file intended."))
        elif self.bad_torrent_noncharacter:
            errorfunc(logging.ERROR,
                      _("This .torrent file has been created with a broken "
                        "tool and has bad character values that do not "
                        "correspond to any real character. Some or all of the "
                        "filenames may appear different from what the creator "
                        "of the .torrent file intended."))
        elif self.bad_torrent_wrongfield:
            errorfunc(logging.ERROR,
                      _("This .torrent file has been created with a broken "
                        "tool and has incorrectly encoded filenames. The "
                        "names used may still be correct."))
        elif self.bad_conversion:
            errorfunc(logging.WARNING,
                      _('The character set used on the local filesystem ("%s") '
                        'cannot represent all characters used in the '
                        'filename(s) of this torrent. Filenames have been '
                        'changed from the original.') % filesystem_encoding)
        elif self.bad_windows:
            errorfunc(logging.WARNING,
                      _("The Windows filesystem cannot handle some "
                        "characters used in the filename(s) of this torrent. "
                        "Filenames have been changed from the original."))
        elif self.bad_path:
            errorfunc(logging.WARNING,
                      _("This .torrent file has been created with a broken "
                        "tool and has at least 1 file with an invalid file "
                        "or directory name. However since all such files "
                        "were marked as having length 0 those files are "
                        "just ignored."))

    # At least BitComet seems to make bad .torrent files that have
    # fields in an arbitrary encoding but separate 'field.utf-8' attributes
    def _get_attr_utf8(self, d, attrib):
        v = d.get(attrib + '.utf-8')
        if v is not None:
            if v != d[attrib]:
                self.bad_torrent_wrongfield = True
        else:
            v = d[attrib]
        return v

    def _enforce_utf8(self, s):
        try:
            s = s.decode('utf-8')
        except:
            self.bad_torrent_unsolvable = True
            s = s.decode('utf-8', 'replace')
        t = s.translate(noncharacter_translate)
        if t != s:
            self.bad_torrent_noncharacter = True
        return t.encode('utf-8')

    def _get_field_utf8(self, d, attrib):
        r = self._get_attr_utf8(d, attrib)
        return self._enforce_utf8(r)

    def _fix_windows(self, name, t=windows_translate):
        bad = False
        r = name.translate(t)
        # for some reason name cannot end with '.' or space
        if r[-1] in '. ':
            r = r + '-'
        if r != name:
            self.bad_windows = True
            bad = True
        return (r, bad)

    def _to_fs(self, name):
        return self._to_fs_2(name)[1]

    def _to_fs_2(self, name):
        bad = False
        if sys.platform.startswith('win'):
            name, bad = self._fix_windows(name)
        name = name.decode('utf-8')
        try:
            r = name.encode(filesystem_encoding)
        except:
            self.bad_conversion = True
            bad = True
            r = name.encode(filesystem_encoding, 'replace')

        if sys.platform.startswith('win'):
            # encoding to mbcs with or without 'replace' will make the
            # name unsupported by windows again because it adds random
            # '?' characters which are invalid windows filesystem
            # character
            r, bad = self._fix_windows(r)
        return (bad, r)


    def to_data(self):
        return bencode(self.metainfo)


    def check_for_resume(self, path):
        """
        Determine whether this torrent was previously downloaded to
        path.  Returns:
        
        -1: STOP! gross mismatch of files
         0: MAYBE a resume, maybe not
         1: almost definitely a RESUME - file contents, sizes, and count match exactly
        """
        STOP   = -1
        MAYBE  =  0
        RESUME =  1
        
        if self.is_batch != os.path.isdir(path):
            return STOP

        disk_files = {}
        if self.is_batch:

            def collect_files(top, dir, files):
                here = dir[len(top)+1:]
                for f in files:
                    fullpath = os.path.join(dir, f)
                    if not os.path.isdir(fullpath):
                        disk_files[os.path.join(here, f)] = os.stat(fullpath)[6]
            os.path.walk(path, collect_files, path)
            metainfo_files = dict(zip(self.files_fs, self.sizes))
        else:
            if os.access(path, os.F_OK):
                disk_files[self.name_fs] = os.stat(path)[6]
            metainfo_files = {self.name_fs : self.sizes[0]}

        if len(disk_files) == 0:
            # no files on disk, definitely not a resume
            return STOP

        if set(disk_files.keys()) != set(metainfo_files.keys()):
            # check files
            if len(disk_files) > len(metainfo_files):
                # file on disk that's not in the torrent
                return STOP
            if len(metainfo_files) > len(disk_files):
                #file in the torrent that's not on disk
                return MAYBE
            else:
                # otherwise, file mismatch both on disk and in torrent
                return STOP
        else:
            # check sizes
            ret = RESUME
            for f, s in disk_files.iteritems():
                
                if f not in disk_files:
                    print f, disk_files, metainfo_files
                if f not in metainfo_files:
                    print f, disk_files, metainfo_files
                    
                if disk_files[f] > metainfo_files[f]:
                    # file on disk that's bigger than the corresponding one in the torrent
                    return STOP
                elif disk_files[f] < metainfo_files[f]:
                    # file on disk that's smaller than the corresponding one in the torrent
                    ret = MAYBE
                else:
                    # file sizes match exactly
                    continue
            return ret

