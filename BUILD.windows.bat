@echo off
rem this assumes python and makensis are in the path
python winsetup.py py2exe --windows --icon icon_bt.ico
copy *.ico dist\btdownloadgui
copy *.gif dist\btdownloadgui
copy bittorrent.nsi dist\btdownloadgui
cd dist\btdownloadgui
makensis bittorrent.nsi
