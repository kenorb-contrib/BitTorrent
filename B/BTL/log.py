from logging import *

import time, sys
import datetime
import logging
import logging.handlers

from BTL import twisted_logger

# convenience re-export so that they can be used without import logging.
DEBUG = DEBUG
INFO = INFO
WARNING = WARNING
ERROR = ERROR
CRITICAL = CRITICAL
getLogger = getLogger

# Not used at the moment but can be changed later
SYSLOG_HOST                 = 'localhost'
SYSLOG_PORT                 = 514

class BTLFormatter(logging.Formatter):

    def formatTime(self, record, datefmt=None):
        ct = self.converter(record.created)
        try:
            dt = datetime.datetime.utcfromtimestamp(record.created)
            if datefmt:
                s = dt.strftime(datefmt)
            else:
                s = dt.isoformat()
        except:
            s = "Interpretter Shutdown"
        return s


class StdioPretender:
    """Pretends to be stdout or stderr."""
    # modified from twisted.python.log.StdioOnnaStick
    closed = 0
    softspace = 0
    mode = 'wb'
    name = '<stdio (log)>'

    def __init__(self, capture_name, level ):
        self.level = level
        self.logger = logging.getLogger( capture_name )
        self.buf = ''

    def close(self):
        pass

    def flush(self):
        pass

    def fileno(self):
        return -1

    def read(self):
        raise IOError("can't read from the log!")

    readline = read
    readlines = read
    seek = read
    tell = read

    def write(self, data):
        d = (self.buf + data).split('\n')
        self.buf = d[-1]
        messages = d[0:-1]
        for message in messages:
            self.logger.log( self.level, message )

    def writelines(self, lines):
        for line in lines:
            self.logger.log( self.level, message )



def injectLogger(use_syslog = True, log_file = None, verbose = False,
                 capture_output = True,
                 twisted_error_log_level = ERROR,
                 twisted_info_log_level = INFO,
                 capture_stderr_log_level = ERROR,
                 capture_stdout_log_level = INFO,
                 capture_stderr_name = 'stderr',
                 capture_stdout_name = 'stdout',
                 log_level = DEBUG, ):
    """
       Installs logging.  NOTE: WARNING! The installed logger will
       logger.setLevel(DEBUG) for all loggers that it touches.  To
       set the level, set the level argument to this function. If you
       want to affect a level change after calling injectLogger
       then change the appropriate log handlers.

       @param use_syslog:    log to syslog.  use_syslog, log_file, and verbose are not
                             mutually exclusive.
       @param log_file:      log to a file.
       @param verbose:       output logs to stdout.  Setting verbose and capture_output
                             to this function does NOT result in an infinite loop.
       @param capture_output: is not True by default because it can
                             create infinite loops with loggers that
                             output to stdout or stderr.
       @param twisted_error_log_level: log level for errors reported
                             by twisted.
       @param twisted_level: log level for non-errors reported by twisted.
                             If capture_output is set then this is also the log
                             level for anything output to stdout or stderr.
       @param log_level:     only log events that have level >= passed level
                             are logged.  This is achieved by setting the log level in
                             each of the installed handlers.
       @param capture_stderr_log_level: log level for output captured from stdout.
       @param capture_stdout_log_level: log level for output captured from stderr.
       @param capture_sterr_name:  log name used for stderr.  'name'
                             refers to the name arg passed to logging.getLogger(name).
       @param capture_stdout_name: log name used for stdout.  Analogous to capture_stderr_name.
    """
    logger = logging.getLogger('')
    logger.setLevel(DEBUG)  # we use log handler levels to control output level.

    formatter = BTLFormatter("%(asctime)s - %(name)s - %(process)d - "
                             "%(levelname)s - %(message)s")

    if log_file is not None:
        lf_handler = logging.handlers.RotatingFileHandler(filename=log_file,
                                                          mode='a',
                                                          maxBytes=2**27,
                                                          backupCount=10)

        lf_handler.setFormatter(formatter)
        lf_handler.setLevel(log_level)
        logger.addHandler(lf_handler)

    if use_syslog:
        SysLogHandler = logging.handlers.SysLogHandler
        sl_handler = SysLogHandler('/dev/log',
                                   facility=SysLogHandler.LOG_LOCAL0)
                                   #address = (SYSLOG_HOST, SYSLOG_PORT))
        # namespace - pid - level - message
        sl_handler.setFormatter(BTLFormatter("%(name)s - %(process)d - "
                                             "%(levelname)s - %(message)s"))
        sl_handler.setLevel(log_level)
        logger.addHandler(sl_handler)

    if verbose:
        # StreamHandler does not capture stdout, it directs output from
        # loggers to stdout.
        so_handler = logging.StreamHandler(sys.stdout)
        so_handler.setFormatter(formatter)
        so_handler.setLevel(log_level)
        logger.addHandler(so_handler)

    if capture_output:
        sys.stdout = StdioPretender( capture_stdout_name, capture_stdout_log_level )
        sys.stderr = StdioPretender( capture_stderr_name, capture_stderr_log_level )

    twisted_logger.start(error_log_level = twisted_error_log_level,
                         info_log_level = twisted_info_log_level)


if __name__ == '__main__':

    injectLogger(log_file = "your.log", use_syslog=False, verbose=True)
    logger = logging.getLogger("myapp")
    logger.warning("You are awesome")

    print 'stdout!'
    print >>sys.stderr, 'stderr!'
    from twisted.internet import reactor
    from twisted.python import failure
    def foo():
        reactor.stop()
        zul = dana

    reactor.callLater(0, foo)
    reactor.run()


