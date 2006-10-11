import logging
from twisted.python import reflect
from twisted.python import log
from BTL import defer # for failure decoration

class LogLogObserver(log.FileLogObserver):
    """Log observer that writes to a python logger."""

    def __init__(self, error_log_level, info_log_level):
        self.error_log_level = error_log_level
        self.info_log_level = info_log_level

    def emit(self, eventDict):
        system = eventDict['system']
        if system == '-':
            system = 'twisted'
        else:
            system = 'twisted.' + system
        logger = logging.getLogger(system)
        edm = eventDict['message'] or ''
        if eventDict['isError'] and eventDict.has_key('failure'):
            if not edm:
                edm = 'Failure:'
            logger.log(self.error_log_level,
                       edm, exc_info=eventDict['failure'].exc_info())
        elif eventDict.has_key('format'):
            text = self._safeFormat(eventDict['format'], eventDict)
            logger.log(self.info_log_level, text)
        else:
            text = ' '.join(map(reflect.safe_str, edm))
            logger.log(self.info_log_level, text)


def start(capture_output = True,
          error_log_level = logging.ERROR,
          info_log_level = logging.INFO):
    o = LogLogObserver(error_log_level, info_log_level)
    log.startLoggingWithObserver(o.emit, setStdout=int(capture_output))

