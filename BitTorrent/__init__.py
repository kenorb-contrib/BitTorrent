
version = "S-5.8.11 (SHAD0W's experimental)"

version_short = version.split(' ')[0]

from types import StringType
from sha import sha
from time import time
try:
    from os import getpid
except ImportError:
    def getpid():
        return 1

mapbase64 = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz.-'

def createPeerID(ins = '---'):
    assert type(ins) is StringType
    assert len(ins) == 3
    myid = version_short[0]
    for subver in version_short[2:].split('.'):
        try:
            subver = int(subver)
        except:
            subver = 0
        myid += mapbase64[subver]
    myid += ('-' * (6-len(myid)))
    myid += ins
    for i in sha(repr(time()) + str(getpid())).digest()[-11:]:
        myid += mapbase64[ord(i) & 0x3F]
    return myid