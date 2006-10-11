from twisted.internet import protocol
from BTL.decorate import decorate_func

## someday twisted might do this for me
class SmartReconnectingClientFactory(protocol.ReconnectingClientFactory):

    def buildProtocol(self, addr):
        prot = protocol.ReconnectingClientFactory.buildProtocol(self, addr)

        # decorate the protocol with a delay reset
        prot.connectionMade = decorate_func(self.resetDelay,
                                            prot.connectionMade)
        
        return prot    