#!/bin/bash

# The contents of this file are subject to the BitTorrent Open Source License
# Version 1.1 (the License).  You may not copy or use this file, in either
# source code or executable form, except in compliance with the License.  You
# may obtain a copy of the License at http://www.bittorrent.com/license/.
#
# Software distributed under the License is distributed on an AS IS basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied.  See the License
# for the specific language governing rights and limitations under the
# License.

# written by Matt Chisholm
# Who uses makefiles anyways these days?

# This script will install BitTorrent on your machine, attempting to
# use the native, local packaging system (rpm or deb) if possible.

echo "Checking to see if you have permission to install."
if ! `sudo -v` ; then
    echo 'Root permission is required to install.  Aborting install.'
    exit
fi

if python -c 'import sys; assert sys.version >= "2.3"'; then
    PYTHONVERSION=`python -c 'import sys; print sys.version[:3]'`
    echo "Python $PYTHONVERSION is already installed."
else
    echo 'Python 2.3 or greater is required, but it is not installed.  Aborting install.' 
    exit
fi


if python -c 'import wx; import wxPython; assert wxPython.__version__ >= "2.6";' ; then
    echo 'wyPython 2.6 or greater is already installed.'
else
    echo 'wxPython 2.6 or greater is required, but it is not installed.  Aborting install.' 
    exit
fi


if python -c 'import twisted; import twisted.copyright; assert twisted.copyright.version >= "1.3"' ; then
    echo 'Twisted 1.3 or greater is already installed.'    
else
    echo 'Twisted 1.3 or greater is required, but it is not installed.  Aborting install.' 
    exit
fi


if [[ -d /etc/apt/  &&  -x `which dpkg-deb` ]]; then
    echo -n "This appears to be a deb-based system, building .deb package.... "
    if sh build_nix_pkg.sh deb 2>/dev/null >/dev/null ; then
	echo 'Done.'
	PKG=`ls dist/*$PYTHONVERSION.deb`
	echo "Installing $PKG with sudo dpkg -i.... "
	if sudo dpkg -i $PKG; then
	    echo 'Installed.'
	else
	    echo 'Failed.'
	fi
    else
	echo 'Failed.'
    fi
elif [ -x `which rpm` ]; then
    echo -n "This appears to be a rpm-based system, building .rpm package.... "
    if sh build_nix_pkg.sh rpm 2>/dev/null >/dev/null ; then
	echo 'Done.'
	PKG=`ls dist/*$PYTHONVERSION.noarch.rpm`
	echo "Installing $PKG with sudo rpm -ivh.... "
	if sudo rpm -ivh $PKG; then
	    echo 'Installed.'
	else
	    echo 'Failed.'
	fi
    else
	echo 'Failed.'
    fi
else
    echo -n "Neither rpm nor deb package systems detected.  Installing binaries directly.... "
    if sudo python setup.py install; then
	echo 'Done.'
    else:
	echo 'Installation failed.'
    fi
fi
