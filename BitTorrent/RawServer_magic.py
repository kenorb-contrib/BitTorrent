# this file contains black magic.

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
    
    if choice.lower() == "twisted":
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

