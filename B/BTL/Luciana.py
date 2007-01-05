# Two reactors spinning at once.
# IOCP reactor for most things
# selectreactor for SSL
#
# by Greg Hazel

from twisted.internet import iocpreactor
iocpreactor.proactor.install()

from twisted.internet.selectreactor import SelectReactor
selectreactor = SelectReactor()

from twisted.internet import reactor

selectreactor.spin_task = 0

def selectrun():
    selectreactor.iterate(0)
    if selectreactor.spin_task > 0:
        reactor.callLater(0.01, selectrun)
    
class HookedFactory(object):
    def __init__(self, factory):
        self.factory = factory

    def startedConnecting(self, connector):
        if selectreactor.spin_task == 0:
            reactor.callLater(0.01, selectrun)
        selectreactor.spin_task += 1
        return self.factory.startedConnecting(connector)
        
    def clientConnectionFailed(self, connector, reason):
        selectreactor.spin_task -= 1
        return self.factory.clientConnectionFailed(connector, reason)

    def clientConnectionLost(self, connector, reason):
        selectreactor.spin_task -= 1
        return self.factory.clientConnectionLost(connector, reason)

    def __getattr__(self, attr):
        return getattr(self.factory, attr)

def spin_ssl(host, port, factory, contextFactory, timeout=30, bindAddress=None):
    factory = HookedFactory(factory)
    connector = selectreactor.connectSSL(host, port, factory, contextFactory,
                                         timeout, bindAddress)
    return connector
        
reactor.connectSSL = spin_ssl
