#!/usr/bin/env python
## this script copies BitTorrent dependent modules into the resource dir in a 
## configuration independent way (hopefully)

from os.path import join
from os import makedirs, system, environ, listdir
from shutil import copy
import sys

py_path = 'lib/python2.2'
so_path = 'lib/python2.2/lib-dynload'


## add dependend modules to one or the other list, depending on the type
## there are probably some extra modules in here that aren't actually used

py_modules = ['StringIO', 'UserDict', '__future__', 'atexit', 'base64', 'bisect', 'copy', 'copy_reg', 'dospath', 'ftplib', 'getopt', 'getpass', 'gopherlib', 'httplib', 'linecache', 'macpath', 'macurl2path', 'mimetools', 'mimetypes', 'ntpath', 'nturl2path', 'os', 'popen2', 'posixpath', 'pre', 'quopri', 'random', 're', 'repr', 'rfc822', 'socket', 'sre', 'sre_compile', 'sre_constants', 'sre_parse', 'stat', 'string', 'tempfile', 'termios', 'threading', 'traceback', 'types', 'urllib', 'urlparse', 'uu', 'warnings']

so_modules = ['_socket', 'sha', 'time', 'binascii', 'cStringIO', 'errno', 'macfs', 'math', 'pcre', 'pwd', 'select', 'strop']

res = join(environ['SYMROOT'], '%s.%s/Contents/Resources' % (environ['PRODUCT_NAME'], environ['WRAPPER_EXTENSION']))
py = join(res, 'lib/python2.2')
dy = join(py, 'lib-dynload')
bt = join(res, 'BitTorrent')

try:
    makedirs(py)
except OSError, reason:
    # ignore errno=17 directory already exists...
    if reason.errno != 17:
	raise OSError, reason

try:
    makedirs(dy)
except OSError, reason:
    # ignore errno=17 directory already exists...
    if reason.errno != 17:
	raise OSError, reason

try:
    makedirs(bt)
except OSError, reason:
    # ignore errno=17 directory already exists...
    if reason.errno != 17:
	raise OSError, reason

print "Copying depedent Python modules..."

source = join(sys.prefix, py_path)
for module in py_modules:
    copy(join(source, module +".py"), py)

source = join(sys.prefix, so_path)
for module in so_modules:
    copy(join(source, module +".so"), dy)


source = join(environ['SRCROOT'], '../BitTorrent')
for f in listdir(source):
    if f[-3:] == '.py':
	copy(join(source, f), bt)

print "Stripping C modules..."
system("strip -x %s" % join(dy, "*.so"))
