#!/bin/bash

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

# written by Matt Chisholm
# Who uses makefiles anyways these days?

# This script requires Python distutils (python-setuptools and
# python-dev) to build the source, and also the debian packaging tool
# dpkg-deb to build the deb.

cdv update
sh makei18n.sh
rm -fr build dist


build_pkg() {
    PKG=$1
    for PYV in "2.4"; do
        PYTHON="python$PYV"
	if [ `which $PYTHON` ]; then
            PYTHONVERSION=`$PYTHON -c 'import sys; print sys.version[:3]'`
            _build_$PKG
        else
            echo "Cannot build $PKG package for Python $PYV because it is not installed."
        fi
    done
}


_build_rpm() {
    echo "
Building rpm for Python $PYTHONVERSION..."
    $PYTHON setup.py bdist_rpm --python $PYTHON --group "Applications/Internet"
    rename s/$PACKAGEVERSION-1\.noarch\.rpm/$PACKAGEVERSION-1-Python$PYTHONVERSION.noarch.rpm/ dist/*rpm
    rm dist/*src.rpm dist/*tar.gz
    echo "Done with rpm for Python $PYV.
"
}


_build_deb() {
    echo "
Building deb for Python $PYV..."
    $PYTHON setup.py bdist_dumb
    cd dist/

    PACKAGENAME="bittorrent_${PACKAGEVERSION}_python${PYTHONVERSION}"
    mkdir $PACKAGENAME
    DUMBDIST=`ls BitTorrent-$PACKAGEVERSION*.tar.gz`
    mv $DUMBDIST $PACKAGENAME
    cd $PACKAGENAME
    tar -xvzf $DUMBDIST
    rm $DUMBDIST
    cd ..
    INSTALLEDSIZE=`du -ks $PACKAGENAME | sed -e "s/$PACKAGENAME//"`
    mkdir $PACKAGENAME/DEBIAN
    sed -e "s/PACKAGEVERSION/$PACKAGEVERSION/g" ../debian/control |\
    sed -e "s/PYTHONVERSION/$PYTHONVERSION/g" |\
    sed -e "s/INSTALLEDSIZE/$INSTALLEDSIZE/g" \
    > $PACKAGENAME/DEBIAN/control
    dpkg-deb -b $PACKAGENAME
    rm -fr $PACKAGENAME

    cd ..
    echo "Done with deb for Python $PYV.
"
}


build_src() {
    echo "
Building source..."
    $PYTHON setup.py sdist
    echo "Done with source.
"
}


build_all() {
    echo "Building all..."
    build_pkg 'rpm'
    build_pkg 'deb'
    build_src
    echo "You may specify 'rpm', 'deb' or 'src' to build a specific package."
}


PYTHON='python'
PYTHONVERSION=`$PYTHON -c 'import sys; print sys.version[:3]'`
PACKAGEVERSION=`$PYTHON -c 'from BitTorrent import version; print version'`

case "$1" in
  rpm)
    build_pkg 'rpm'
    ;;

  deb)
    build_pkg 'deb'
    ;;

  src)
    build_src
    ;;

  *)
    build_all
    ;;

esac

