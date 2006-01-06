@rem The contents of this file are subject to the BitTorrent Open Source License
@rem Version 1.0 (the License).  You may not copy or use this file, in either
@rem code or executable form, except in compliance with the License.  You
@rem may obtain a copy of the License at http://www.bittorrent.com/license/.
@rem
@rem Software distributed under the License is distributed on an AS IS basis,
@rem WITHOUT WARRANTY OF ANY KIND, either express or implied.  See the License
@rem for the specific language governing rights and limitations under the
@rem License.

@rem For Python 2.3:
@rem set PYTHON=python23
@rem For Python 2.4:
set PYTHON=Python24

@rem For GTK 2.4:
@rem set WIMP_DIR_NAME=wimp
@rem For GTK 2.6 and 2.8:
set WIMP_DIR_NAME=MS-Windows

@rem copy the important files to the root, so we don't have to hardcode paths
@rem all over the place

@if exist "windows_installer\build.bat" goto continue
@echo You must run build.bat from within the root directory
:continue

cd windows_installer

copy winsetup.py ..
copy winmakei18n.py ..
copy installer.directory.ini ..
copy installer.upgrade.ini ..
copy installer.warning.rtf ..

cd ..

del /F /S /Q build dist 
c:\%PYTHON%\python.exe winmakei18n.py
@if errorlevel 1 goto error
c:\%PYTHON%\python.exe winsetup.py py2exe
@if errorlevel 1 goto error

copy %GTK_BASEPATH%\bin\libpng12.dll dist\
@if errorlevel 1 goto error
copy %GTK_BASEPATH%\bin\zlib1.dll dist\
@if errorlevel 1 goto error
copy %GTK_BASEPATH%\bin\libpangoft2-1.0-0.dll dist\
@if errorlevel 1 goto error
@rem I don't think this is needed:
@rem copy %GTK_BASEPATH%\bin\libxml2.dll dist\

mkdir dist\etc\pango
copy %GTK_BASEPATH%\etc\pango dist\etc\pango
@if errorlevel 1 goto error

mkdir dist\etc\gtk-2.0\
copy %GTK_BASEPATH%\etc\gtk-2.0\gdk-pixbuf.loaders dist\etc\gtk-2.0
@if errorlevel 1 goto error

mkdir dist\lib\gtk-2.0\2.4.0\loaders
copy %GTK_BASEPATH%\lib\gtk-2.0\2.4.0\loaders\libpixbufloader-png.dll dist\lib\gtk-2.0\2.4.0\loaders
@if errorlevel 1 goto error
copy %GTK_BASEPATH%\lib\gtk-2.0\2.4.0\loaders\libpixbufloader-xpm.dll dist\lib\gtk-2.0\2.4.0\loaders
@if errorlevel 1 goto error
copy %GTK_BASEPATH%\lib\gtk-2.0\2.4.0\loaders\libpixbufloader-ico.dll dist\lib\gtk-2.0\2.4.0\loaders
@if errorlevel 1 goto error

mkdir dist\lib\pango\1.4.0\modules
copy %GTK_BASEPATH%\lib\pango\1.4.0\modules\pango-basic-win32.dll dist\lib\pango\1.4.0\modules\
@if errorlevel 1 goto error
copy %GTK_BASEPATH%\lib\pango\1.4.0\modules\pango-basic-fc.dll dist\lib\pango\1.4.0\modules\
@if errorlevel 1 goto error

@rem This never could have been working. 'copy' does not recurse subdirectories
@rem I think the task this is supposed to accomplish is in winsetup.py
@rem copy %GTK_BASEPATH%\lib\locale dist\lib\
@rem @if errorlevel 1 goto error

copy %GTK_BASEPATH%\etc\gtk-2.0\gtkrc dist\etc\gtk-2.0
@if errorlevel 1 goto error
mkdir dist\lib\gtk-2.0\2.4.0\engines
copy %GTK_BASEPATH%\lib\gtk-2.0\2.4.0\engines\libwimp.dll dist\lib\gtk-2.0\2.4.0\engines
@if errorlevel 1 goto error

mkdir dist\share\themes\%WIMP_DIR_NAME%\gtk-2.0
copy %GTK_BASEPATH%\share\themes\%WIMP_DIR_NAME%\gtk-2.0\gtkrc dist\share\themes\%WIMP_DIR_NAME%\gtk-2.0
@if errorlevel 1 goto error

c:\%PYTHON%\python.exe windows_installer\winprepnsi.py windows_installer\installer.nsi installer.temp.nsi
@if errorlevel 1 goto error
"C:\Program Files\NSIS\makensis.exe" installer.temp.nsi
@if errorlevel 1 goto error
del installer.temp.nsi
@if errorlevel 1 goto error

@rem cleanup
del winsetup.py
del winmakei18n.py
del installer.directory.ini
del installer.upgrade.ini
del installer.warning.rtf


@goto done

:error
@echo -------------------------------------------------------------------------------
@echo Build failed.

:done