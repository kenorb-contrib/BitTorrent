# -*- coding: UTF-8 -*-
# The contents of this file are subject to the BitTorrent Open Source License
# Version 1.1 (the License).  You may not copy or use this file, in either
# source code or executable form, except in compliance with the License.  You
# may obtain a copy of the License at http://www.bittorrent.com/license/.
#
# Software distributed under the License is distributed on an AS IS basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied.  See the License
# for the specific language governing rights and limitations under the
# License.


app_name = 'BitTorrent'
version = '4.9.3'

URL = 'http://www.bittorrent.com/'
DONATE_URL = URL + 'donate.myt?client=%(client)s'
FAQ_URL = URL + 'FAQ.myt?client=%(client)s'
SEARCH_URL = 'http://www.bittorrent.com/search_result.myt?client=%(client)s&search=%(search)s'
LOCALE_URL = URL + 'translations/'

NAG_FREQUENCY = 3
PORT_RANGE = 5

import sys
assert sys.version_info >= (2, 3, 0), _("Python %s or newer required") % '2.3.0'
import os
import time
import atexit
import shutil
import logging
import logging.handlers
from StringIO import StringIO

class BTFailure(Exception):
    pass


class InfoHashType(str):
    def __repr__(self):
        return self.encode('hex')
    def short(self):
        return repr(self)[:8]


branch = None
if os.access('.cdv', os.F_OK):
    branch = os.path.split(os.path.realpath(os.path.split(sys.argv[0])[0]))[1]

from BitTorrent.language import languages, language_names
from BitTorrent.platform import get_home_dir, is_frozen_exe, get_filesystem_encoding

filesystem_encoding = get_filesystem_encoding(None)

def set_filesystem_encoding(encoding, errorfunc=None):
    global filesystem_encoding
    filesystem_encoding = get_filesystem_encoding(encoding, errorfunc=None)

if os.name == 'posix':
    if os.uname()[0] == "Darwin":
        from BitTorrent.platform import install_translation
        install_translation()

logroot = get_home_dir()

# hackery to get around bug in py2exe that tries to write log files to
# application directories, which may not be writable by non-admin users
if is_frozen_exe:
    if logroot is None:
        logroot = os.path.splitdrive(sys.executable)[0]
        if logroot[-1] != os.sep:
            logroot += os.sep
    logname = os.path.split(sys.executable)[1]
else:
    logname = os.path.split(os.path.abspath(sys.argv[0]))[1]
logname = os.path.splitext(logname)[0] + '.log'
logpath = os.path.join(logroot, logname)


# becuase I'm generous.
STDERR = logging.CRITICAL + 10
logging.addLevelName(STDERR, 'STDERR')

# define a Handler which writes INFO messages or higher to the sys.stderr
console = logging.StreamHandler()
console.setLevel(logging.DEBUG)
# set a format which is simpler for console use
formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
# tell the handler to use this format
console.setFormatter(formatter)
# add the handler to the root logger
logging.getLogger('').addHandler(console)

bt_log_fmt = logging.Formatter('[' + str(version) + ' %(asctime)s] %(levelname)-8s: %(message)s',
                               datefmt="%Y-%m-%d %H:%M:%S")

stderr_console = None
old_stderr = sys.stderr

def inject_main_logfile():
    # the main log file. log every kind of message, format properly, rotate the log
    # someday - SocketHandler
    mainlog = logging.handlers.RotatingFileHandler(filename=logpath, mode='a', maxBytes=2**20, backupCount=1)
    mainlog.setFormatter(bt_log_fmt)
    mainlog.setLevel(logging.DEBUG)
    logger = logging.getLogger('')
    logging.getLogger('').addHandler(mainlog)
    logging.getLogger('').removeHandler(console)
    atexit.register(lambda : logging.getLogger('').removeHandler(mainlog))

    if not is_frozen_exe:
        # write all stderr messages to stderr (unformatted)
        # as well as the main log (formatted)
        stderr_console = logging.StreamHandler(old_stderr)
        stderr_console.setLevel(STDERR)
        stderr_console.setFormatter(logging.Formatter('%(message)s'))
        logging.getLogger('').addHandler(stderr_console)

class StderrProxy(StringIO):

    def _flush_to_log(self):
        logging.log(STDERR, self.getvalue())
        self.seek(0)
        self.truncate()
        
    # whew. ugly. is there a simpler way to write this?
    # the goal is to stop every '\n' and flush to the log
    # otherwise keep buffering.
    def write(self, text, *args):
        if not StringIO: # interpreter shutdown
            return
        
        if '\n' not in text:
            StringIO.write(self, text)
            return
        
        last = False
        if text[-1] == '\n':
            last = True
        lines = text.split('\n')
        for t in lines[:-1]:
            StringIO.write(self, t)
            self._flush_to_log()
        if len(lines[-1]) > 0:
            StringIO.write(self, lines[-1])
            if last:
                self._flush_to_log()

sys.stderr = StderrProxy()
def reset_stderr():
    sys.stderr = old_stderr
atexit.register(reset_stderr)
