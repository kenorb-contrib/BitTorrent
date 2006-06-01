# Zeroconf discovery of other BT clients on the local network.
#
# by Greg Hazel

import sys
import random
import socket
import logging
import Zeroconf
from BitTorrent.HostIP import get_host_ip

discovery_logger = logging.getLogger('LocalDiscovery')
discovery_logger.setLevel(logging.DEBUG)
#discovery_logger.addHandler(logging.StreamHandler(sys.stdout))

class LocalDiscovery(object):

    def __init__(self, rawserver, port, got_peer):
        self.rawserver = rawserver
        self.port = port
        self.got_peer = got_peer
        self.server = Zeroconf.Zeroconf()

    def announce(self, infohash, peerid):
        discovery_logger.info("announcing: %s", infohash)
        service_name = "_BitTorrent-%s._tcp.local." % infohash
        
        # do I need to keep the browser around?
        browser = Zeroconf.ServiceBrowser(self.server, service_name, self)

        addr = socket.inet_aton(get_host_ip())
        service = Zeroconf.ServiceInfo(service_name,
                                       peerid + "." + service_name,
                                       address = addr,
                                       port = self.port,
                                       weight = 0, priority=0,
                                       properties = {}
                                      )
        self.server.registerService(service)

    def addService(self, server, type, name):
        discovery_logger.info("Service %s added", repr(name))
        # Request more information about the service
        info = server.getServiceInfo(type, name)
        if info:
            host = socket.inet_ntoa(info.address)
            try:
                port = int(info.port)
            except:
                discovery_logger.exception("Invalid Service (port not an int): %s" + repr(info.__dict__))
                return
                
            addr = (host, port)
            if addr == (get_host_ip(), self.port):
                # talking to self
                return

            infohash = name.split("_BitTorrent-")[1][:-len("._tcp.local.")]

            discovery_logger.info("Got peer: %s:%d %s", host, port, infohash)

            # BUG: BitTorrent is so broken!
            t = random.random() * 3

            self.rawserver.external_add_task(t, self._got_peer, addr, infohash)

    def removeService(self, server, type, name):
        discovery_logger.info("Service %s removed", repr(name))

    def _got_peer(self, addr, infohash):
        if self.got_peer:
            self.got_peer(addr, infohash)
            
    def stop(self):
        self.port = None
        self.got_peer = None
        self.server.close()

if __name__ == '__main__':
    import string
    import threading
    from BitTorrent.RawServer_twisted import RawServer

    config = {'max_incomplete': 10,
              'max_upload_rate': 350000,
              'bind': '',
              'close_with_rst': False,
              'socket_timeout': 3000}

    event = threading.Event()
    rawserver = RawServer(config=config, noisy=True)

    rawserver.install_sigint_handler()    

    def run_task_and_exit():
        l = LocalDiscovery(rawserver, 6881, lambda *a:sys.stdout.write("GOT: %s\n" % str(a)))
        l.announce("63f27f5023d7e49840ce89fc1ff988336c514b64", ''.join(random.sample(string.letters, 5)))
    
    rawserver.add_task(0, run_task_and_exit)

    rawserver.listen_forever(event)    
    
