rem The contents of this file are subject to the BitTorrent Open Source Licenserem Version 1.0 (the License).  You may not copy or use this file, in either
rem source code or executable form, except in compliance with the License.  You
rem may obtain a copy of the License at http://www.bittorrent.com/license/.
rem
rem Software distributed under the License is distributed on an AS IS basis,
rem WITHOUT WARRANTY OF ANY KIND, either express or implied.  See the License
rem for the specific language governing rights and limitations under the
rem License.


del /F /S /Q build dist 
c:\python23\python.exe winsetup.py py2exe

copy %GTK_BASEPATH%\bin\libpng12.dll dist\
copy %GTK_BASEPATH%\bin\zlib1.dll dist\
copy %GTK_BASEPATH%\bin\libpangoft2-1.0-0.dll dist\
rem I don't think this is needed:
rem copy %GTK_BASEPATH%\bin\libxml2.dll dist\

mkdir dist\etc\pango
copy %GTK_BASEPATH%\etc\pango dist\etc\pango

mkdir dist\etc\gtk-2.0\
copy %GTK_BASEPATH%\etc\gtk-2.0\gdk-pixbuf.loaders dist\etc\gtk-2.0

mkdir dist\lib\gtk-2.0\2.4.0\loaders
copy %GTK_BASEPATH%\lib\gtk-2.0\2.4.0\loaders\libpixbufloader-png.dll dist\lib\gtk-2.0\2.4.0\loaders
copy %GTK_BASEPATH%\lib\gtk-2.0\2.4.0\loaders\libpixbufloader-xpm.dll dist\lib\gtk-2.0\2.4.0\loaders
copy %GTK_BASEPATH%\lib\gtk-2.0\2.4.0\loaders\libpixbufloader-ico.dll dist\lib\gtk-2.0\2.4.0\loaders

mkdir dist\lib\pango\1.4.0\modules
copy %GTK_BASEPATH%\lib\pango\1.4.0\modules\pango-basic-win32.dll dist\lib\pango\1.4.0\modules\
copy %GTK_BASEPATH%\lib\pango\1.4.0\modules\pango-basic-fc.dll dist\lib\pango\1.4.0\modules\

copy %GTK_BASEPATH%\lib\locale dist\lib\

copy %GTK_BASEPATH%\etc\gtk-2.0\gtkrc dist\etc\gtk-2.0
mkdir dist\lib\gtk-2.0\2.4.0\engines
copy %GTK_BASEPATH%\lib\gtk-2.0\2.4.0\engines\libwimp.dll dist\lib\gtk-2.0\2.4.0\engines
mkdir dist\share\themes\wimp\gtk-2.0
copy %GTK_BASEPATH%\share\themes\wimp\gtk-2.0\gtkrc dist\share\themes\wimp\gtk-2.0

"C:\Program Files\NSIS\makensis.exe" bittorrent.nsi