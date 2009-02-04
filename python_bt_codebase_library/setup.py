#!/usr/bin/env python
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
import sys, os
#try:
#    from BTL.bdistutils import setup
#except ImportError:
#    from distutils.core import setup, Extension
from setuptools import setup, find_packages

app_name = "setup"

#HACKHACKHACK
# setup does not build c++ interface files properly.  It creates the line:
#  swig -python -c++ -module cmap_swig -o BTL/cmap_swig_wrap.c BTL/cmap_swig.i
# but what we want is:
#  swig -python -c++ -module cmap_swig -o BTL/cmap_swig_wrap.cxx BTL/cmap_swig.i
# After looking around for a while, it appears that the only way to
# fix this is to change the distutils python library.  This would require
# everyone who wants to compile the library to first patch distutils.
# Patching distutils is more effort than forking a process to run
# gnu make.  I thus created this alternate HACK. XXX
#
# This hack is not appropriate for external distribution.
def make():
    print "copying .cxx, .h, and .i files to build/lib/BTL"
    if not os.path.exists( "build/lib/BTL" ):
        os.makedirs( "build/lib/BTL" )
    shutil.copy2( "BTL/cmap_swig.cxx", "build/lib/BTL/cmap_swig.cxx" )
    shutil.copy2( "BTL/cmultimap_swig.cxx", "build/lib/BTL/cmultimap_swig.cxx" )
    shutil.copy2( "BTL/cmap_swig.h", "build/lib/BTL/cmap_swig.h" )
    shutil.copy2( "BTL/cmultimap_swig.h", "build/lib/BTL/cmultimap_swig.h" )
    shutil.copy2( "BTL/cmap_swig.i", "build/lib/BTL/cmap_swig.i" )
    shutil.copy2( "BTL/cmultimap_swig.i", "build/lib/BTL/cmultimap_swig.i" )
    shutil.copy2( "BTL/Makefile", "build/lib/BTL/Makefile" )

    print "forking process to run make"
    child_pid = fork()
    if child_pid == 0:
        if not os.path.exists( "build/lib/BTL/cmap_swig.cxx" ):
            print "before chdir, I could not find cmap_swig.cxx"
        chdir("build/lib/BTL")
        #chdir("BTL")
        execlp("make")
    else:
        status = wait()

if len(sys.argv) > 1 and sys.argv[1] in ["install", "build","installdev"] \
  and sys.platform != "win32":
    import os
    from os import execlp, fork, wait, chdir
    import shutil
    from BTL.bdistutils import seteugid_to_login, getuid_for_path
    #if os.getuid() == 0 and getuid_for_path(".") != 0:
    #    seteugid_to_login()
    try:
        try:
            make()
        except:
            old_uid = os.geteuid()
            seteugid_to_login()
            make()
            os.seteuid(old_uid)
            
    except Exception ,e:
        print str(e)
        print ("If you are not building hypertracker then ignore this "
               "comment.  If you are building the hypertracker then you'll "
               "have to build cmap_swig and cmultimap_swig manually by running "
               "'make' in the BTL source directory." )
    #if os.getuid() == 0:
    #    os.seteuid(0)  # restore root privilege.
# END HACK

#lang = 'c++'
#swigOpts = ['-c++', '-module','cmap_swig']
#compilerArgs = []

setup(name="BTL",
    version="0.31",
    description = "BitTorrent Library",
    author="BitTorrent, Inc.",
    install_requires=[
        "pycrypto",
        "pycurl", # this must match libcurl3-dev version
        "Twisted",
    ],
    packages=find_packages(
        exclude=[
            'ez_setup',
        ],
    ),
    include_package_data = False,
    package_data={
        'BTL.canonical': ['metadata.html', 'metadata_example.html', 'metadata_source.html'],
    },
    #ext_modules=[Extension('cmap_swig', ['BTL/cmap_swig.i'],
    #    extra_compile_args=compilerArgs, language=lang, swig_opts=swigOpts)],
)
