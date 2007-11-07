@rem The contents of this file are subject to the BitTorrent Open Source License
@rem Version 1.0 (the License).  You may not copy or use this file, in either
@rem code or executable form, except in compliance with the License.  You
@rem may obtain a copy of the License at http://www.bittorrent.com/license/.
@rem
@rem Software distributed under the License is distributed on an AS IS basis,
@rem WITHOUT WARRANTY OF ANY KIND, either express or implied.  See the License
@rem for the specific language governing rights and limitations under the
@rem License.

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