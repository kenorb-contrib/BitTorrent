@echo off
rem this assumes python and makensis are in the path
python winsetup.py py2exe
copy icon*.ico dist
copy *.gif dist
copy bittorrent.nsi dist
cd dist
makensis bittorrent.nsi
