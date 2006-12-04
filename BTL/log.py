from logging import *

import time
import datetime
import logging
import logging.handlers

from BTL import twisted_logger


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


def injectLogger(use_syslog = True, log_file = None, verbose = False,
                 capture_output = True,
                 twisted_error_log_level = ERROR,
                 twisted_info_log_level = INFO):

    logger = logging.getLogger('')

    formatter = BTLFormatter("%(asctime)s - %(name)s - %(process)d - "
                             "%(levelname)s - %(message)s")

    if log_file is not None:
        lf_handler = logging.handlers.RotatingFileHandler(filename=log_file,
                                                          mode='a',
                                                          maxBytes=2**27,
                                                          backupCount=10)

        lf_handler.setFormatter(formatter)
        lf_handler.setLevel(logging.DEBUG)
        logger.addHandler(lf_handler)

    if use_syslog:
        SysLogHandler = logging.handlers.SysLogHandler
        sl_handler = SysLogHandler('/dev/log',
                                   facility=SysLogHandler.LOG_LOCAL0)
                                   #address = (SYSLOG_HOST, SYSLOG_PORT))
        # namespace - pid - level - message
        sl_handler.setFormatter(BTLFormatter("%(name)s - %(process)d - "
                                             "%(levelname)s - %(message)s"))
        sl_handler.setLevel(logging.DEBUG)
        logger.addHandler(sl_handler)

    if verbose:
        so_handler = logging.StreamHandler(sys.stdout)
        so_handler.setFormatter(formatter)
        so_handler.setLevel(logging.DEBUG)
        logger.addHandler(so_handler)

    twisted_logger.start(capture_output = capture_output,
                         error_log_level = twisted_error_log_level,
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


