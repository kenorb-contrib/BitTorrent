rem This program is free software: you can redistribute it and/or modify
rem it under the terms of the GNU General Public License as published by
rem the Free Software Foundation, either version 3 of the License, or
rem (at your option) any later version.
rem
rem This program is distributed in the hope that it will be useful,
rem but WITHOUT ANY WARRANTY; without even the implied warranty of
rem MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
rem GNU General Public License for more details.
rem
rem You should have received a copy of the GNU General Public License
rem along with this program.  If not, see <http://www.gnu.org/licenses/>.


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
