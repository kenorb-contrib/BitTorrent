del /F /S /Q build dist
c:\python23\python.exe winsetup.py py2exe --windows
"C:\Program Files\NSIS\makensis.exe" bittorrent.nsi
