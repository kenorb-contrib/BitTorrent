#!/usr/bin/env python

# Written by Bram Cohen
# see LICENSE.txt for license information

import sys
assert sys.version >= '2', "Install Python 2.0 or greater"
from distutils.core import setup, Extension

setup(
    name = "BitTorrent",
    version = "2.8.1",
    author = "Bram Cohen",
    author_email = "<bram@bitconjurer.org>",
    url = "http://www.bitconjurer.org/BitTorrent/",
    license = "MIT",
    
    packages = ["BitTorrent"],

    scripts = ["btdownloadgui.py", "btdownloadheadless.py", "btdownloadlibrary.py", 
        "btdownloadprefetched.py", "bttrack.py", "btpublish.py"]
    
    )
