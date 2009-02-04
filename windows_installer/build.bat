@rem This program is free software: you can redistribute it and/or modify
@rem it under the terms of the GNU General Public License as published by
@rem the Free Software Foundation, either version 3 of the License, or
@rem (at your option) any later version.
@rem
@rem This program is distributed in the hope that it will be useful,
@rem but WITHOUT ANY WARRANTY; without even the implied warranty of
@rem MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
@rem GNU General Public License for more details.
@rem
@rem You should have received a copy of the GNU General Public License
@rem along with this program.  If not, see <http://www.gnu.org/licenses/>.

set PYTHON=Python24

@rem copy the important files to the root, so we don't have to hardcode paths
@rem all over the place

@if exist "windows_installer\build.bat" goto continue
@echo You must run build.bat from within the root directory
:continue

cd windows_installer

copy winsetup.py ..
copy installer.directory.ini ..
copy installer.upgrade.ini ..
copy installer.warning.rtf ..
copy winprepnsi.py ..
copy win-append-url.py ..

cd ..

del /F /S /Q build dist 
c:\%PYTHON%\python.exe -OO winsetup.py py2exe
@if errorlevel 1 goto error

c:\%PYTHON%\python.exe winprepnsi.py windows_installer\installer.nsi installer.temp.nsi
@if errorlevel 1 goto error
copy c:\%PYTHON%\python.exe.manifest dist\bittorrent.exe.manifest
@if errorlevel 1 goto error
copy c:\%PYTHON%\python.exe.manifest dist\maketorrent.exe.manifest
@if errorlevel 1 goto error
copy c:\%PYTHON%\python.exe.manifest dist\choose_language.exe.manifest
@if errorlevel 1 goto error
"C:\Program Files\NSIS\makensis.exe" installer.temp.nsi
@if errorlevel 1 goto error
del installer.temp.nsi
@if errorlevel 1 goto error

c:\%PYTHON%\python.exe win-append-url.py

@rem cleanup
del winsetup.py
del installer.directory.ini
del installer.upgrade.ini
del installer.warning.rtf
del winprepnsi.py


@goto done

:error
@echo -------------------------------------------------------------------------------
@echo Build failed.

:done