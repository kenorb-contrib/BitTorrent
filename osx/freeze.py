#!/usr/bin/env python
## this script copies BitTorrent dependent modules into the resource dir in a 
## configuration independent way (hopefully)

from os.path import join
from os import makedirs, system, environ
from shutil import copy
import sys

py_path = 'lib/python2.2'
so_path = 'lib/python2.2/lib-dynload'


py_modules = ['StringIO', 'UserDict', '__future__', 'atexit', 'base64', 'bisect', 'copy', 'copy_reg', 'dospath', 'ftplib', 'getopt', 'getpass', 'gopherlib', 'httplib', 'linecache', 'macpath', 'macurl2path', 'mimetools', 'mimetypes', 'ntpath', 'nturl2path', 'os', 'popen2', 'posixpath', 'pre', 'quopri', 'random', 're', 'repr', 'rfc822', 'socket', 'sre', 'sre_compile', 'sre_constants', 'sre_parse', 'stat', 'string', 'tempfile', 'termios', 'threading', 'traceback', 'types', 'urllib', 'urlparse', 'uu', 'warnings']

so_modules = ['_socket', 'sha', 'time', 'binascii', 'cStringIO', 'errno', 'macfs', 'math', 'pcre', 'pwd', 'select', 'strop']

dest = join(environ['SYMROOT'], 'BitTorrent.app/Contents/Resources/python')
try:
    makedirs(dest)
except OSError, reason:
    if reason.errno != 17:
	raise OSError, reason

print "Copying depedent Python modules..."

source = join(sys.prefix, py_path)
for module in py_modules:
    copy(join(source, module +".py"), dest)

source = join(sys.prefix, so_path)
for module in so_modules:
    copy(join(source, module +".so"), dest)

print "Stripping C modules..."
system("strip -x %s" % join(dest, "*.so"))
