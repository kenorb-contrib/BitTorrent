# The contents of this file are subject to the BitTorrent Open Source License
# Version 1.1 (the License).  You may not copy or use this file, in either
# source code or executable form, except in compliance with the License.  You
# may obtain a copy of the License at http://www.bittorrent.com/license/.
#
# Software distributed under the License is distributed on an AS IS basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied.  See the License
# for the specific language governing rights and limitations under the
# License.

# Written by Greg Hazel

class BaseMagic:
    base = None
    too_late = False

magic = BaseMagic()    

from BitTorrent import BTFailure

try:
    import RawServer_twisted
    magic.base = RawServer_twisted.RawServer
    Handler = RawServer_twisted.Handler
except ImportError:
    import RawServer
    magic.base = RawServer.RawServer
    Handler = RawServer.Handler

def switch_rawserver(choice):
    if magic.too_late:
        raise BTFailure(_("Too late to switch RawServer backends, %s has already been used.") % str(magic.base))
    
    if choice.lower() == 'twisted':
        import RawServer_twisted
        magic.base = RawServer_twisted.RawServer
    else:
        import RawServer
        magic.base = RawServer.RawServer

class _RawServerMetaclass:
    def __init__(self, *args):
        pass

    def __getattr__(self, name):
        magic.too_late = True
        try:
            return getattr(magic.base, name)
        except:
            raise AttributeError, name
    
class RawServer:
    __metaclass__ = _RawServerMetaclass
    def __init__(self, *args, **kwargs):
        magic.too_late = True
        self.instance = magic.base(*args, **kwargs)

    def __getattr__(self, name):
        try:
            return getattr(self.instance, name)
        except:
            raise AttributeError, name

