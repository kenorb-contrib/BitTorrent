set PYTHON=Python24

copy windows_installer\winmakei18n.py .

c:\%PYTHON%\python.exe winmakei18n.py
@if errorlevel 1 goto error

del winmakei18n.py

cd locale
c:\%PYTHON%\python.exe ..\zipup.py *
cd ..

pscp -r -C locale\*.gz nami:/var/www/translations.bittorrent.com/

@goto done

:error
@echo -------------------------------------------------------------------------------
@echo Translation uploading failed.

:done