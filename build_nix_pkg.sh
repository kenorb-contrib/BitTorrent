#!/bin/bash
# written by Matt Chisholm
# Who uses makefiles anyways these days?
cdv update
sh makei18n.sh

#PYTHON='python2.3'
#PYTHON='python2.4'
PYTHON='python'
PYTHONVERSION=`$PYTHON -c 'import sys; print sys.version[:3]'`
rm -fr build dist

build_rpm() {
    echo "
Building rpm..."
    $PYTHON setup.py bdist_rpm --spec-only
    $PYTHON setup.py bdist_rpm
    rename s/\.noarch\.rpm/-Python$PYTHONVERSION.noarch.rpm/ dist/*rpm
    rm dist/*src.rpm dist/*tar.gz dist/BitTorrent.spec
    echo "Done with rpm.
"
}

build_deb() {
    echo "
Building deb..."
    $PYTHON setup.py bdist_dumb
    cd dist
    fakeroot alien BitTorrent-*tar.gz
    rename s/all\.deb/all_python$PYTHONVERSION.deb/ *deb
    rm *tar.gz
    cd ..
    echo "Done with deb.
"
}

build_src() {
    echo "
Building source..."
    $PYTHON setup.py sdist
    echo "Done with source.
"
}

case "$1" in
  rpm)
    build_rpm
    ;;

  deb)
    build_deb
    ;;

  src)
    build_src
    ;;
  *)
    echo "Building all..."
    build_rpm
    build_deb
    build_src
    echo "You may specify 'rpm', 'deb' or 'src' to build a specific package."
    ;;
esac