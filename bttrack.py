#!/usr/bin/env python

# Written by Bram Cohen
# see LICENSE.txt for license information

from BitTornado import PSYCO
if PSYCO.psyco:
    try:
        import psyco
#        assert psyco.__version__ >= 0x010100f0
        psyco.full()
    except:
        pass
    
from sys import argv
from BitTornado.BT1.track import track

if __name__ == '__main__':
    track(argv[1:])
