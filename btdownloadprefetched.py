#!/usr/bin/env python

# Written by Bram Cohen
# this file is public domain

"""
You're probably wondering 'what the hell is prefetched there for anyway?'
well, you see, the dorks making Internet Explorer are were incapable of 
making a mapping from mimetypes to applications, so instead they created 
a mapping from mimetypes to file extensions, and take the contents of 
an http return with a funny mimetype and create a temporary file with 
the listed extension, then 'invoke' that file, which hopefully results 
in invoking the correct application. 

Needless to say, this prevents passing any other useful information to the 
invoked application - like, say, the original url, which is why the 
tracker requires you give it it's own ip. 

btdownloadprefetched is the file to get executed by Internet Explorer.
"""

from sys import argv, version
assert version >= '2', "Install Python 2.0 or greater"
from btdownloadgui import run

if __name__ == '__main__':
    h = open(files[0])
    prefetched = h.read()
    h.close()
    run({}, [], prefetched)
