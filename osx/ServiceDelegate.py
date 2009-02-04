# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#  ServiceDelegate.py
#  BitTorrent
#
#  Created by Drue Loewenstern on Sat Mar 27 2004.
#  Copyright (c) 2004 __MyCompanyName__. All rights reserved.
#

from Foundation import *
from AppKit import NSAppKitVersionNumber

class ServiceDelegate (NSObject):
    def init(self, func):
        self = super(ServiceDelegate, self).init()
        self.addPeerFunc = func
        self.publisher = self.browser = None
        return self
        
    def publish(self, info_hash, peer_id, listen_port):
        self.publisher = NSNetService.alloc().initWithDomain_type_name_port_("", "_BitTorrent-%s._tcp" % info_hash.encode('hex'), peer_id.encode('hex'), listen_port)
        self.publisher.setDelegate_(self)
        self.publisher.publish()
        self.browser = NSNetServiceBrowser.alloc().init()
        self.browser.setDelegate_(self)
        self.browser.searchForServicesOfType_inDomain_("_BitTorrent-%s._tcp" % info_hash.encode('hex'), "")
        
    def stop(self):
        self.stopPublisher()
        self.stopBrowser()

    def stopPublisher(self):
        if self.publisher:
            self.publisher.stop()
            self.publisher = None

    def stopBrowser(self):
        if self.browser:
            self.browser.stop()
            self.browser = None
        
    ### NSNetService delegate methods
    def netService_didNotPublish_(self, sender, errorDict):
        if errorDict["NSNetServicesErrorCode"] != -72003:
            NSLog(NSLocalizedString("Failed to publish Rendezvous advertisement...", ""))
        
    def netServiceBrowser_didFindService_moreComing_(self, browser, peer, moreComing):
        peer.setDelegate_(self)
        if NSAppKitVersionNumber >= 800:
            peer.resolveWithTimeout_(20)
        else:
            peer.resolve()
        if not moreComing:
            self.stopBrowser()
        
    def netServiceDidResolveAddress_(self, peer):
        name = str(peer.name()).decode('hex')
        for addr in peer.addresses():
            self.addPeerFunc(addr, name)
