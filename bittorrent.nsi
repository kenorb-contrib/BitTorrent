# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# Written by Bram Cohen and Matt Chisholm

!define VERSION "4.0.0"
!define APPNAME "BitTorrent"
Outfile ${APPNAME}-${VERSION}.exe
Name "${APPNAME}"
SilentInstall silent
SetCompressor lzma
InstallDir "$PROGRAMFILES\${APPNAME}\"

; This function ensures that you have administrator privileges
; it is copied from:
;http://nsis.sourceforge.net/archive/viewpage.php?pageid=275
Function IsUserAdmin
Push $R0
Push $R1
Push $R2

ClearErrors
UserInfo::GetName
IfErrors Win9x
Pop $R1
UserInfo::GetAccountType
Pop $R2

StrCmp $R2 "Admin" 0 Continue
StrCpy $R0 "true"
Goto Done

Continue:
StrCmp $R2 "" Win9x
StrCpy $R0 "false"
Goto Done

Win9x:
StrCpy $R0 "true"

Done:

Pop $R2
Pop $R1
Exch $R0
FunctionEnd

Function QuitIt
  checkforit:
    Processes::FindProcess "btdownloadgui.exe"
    StrCmp $R0 "1" foundit didntfindit

  foundit:
    MessageBox MB_OK "You must quit ${APPNAME} before installing this version.$\r$\nPlease quit it and press OK to continue."
    Sleep 2000
    Goto checkforit
  didntfindit:

  checkforit2:
    Processes::FindProcess "btmaketorrentgui.exe"
    StrCmp $R0 "1" foundit2 didntfindit2

  foundit2:
    MessageBox MB_OK "You must quit ${APPNAME} metafile creator before installing this version.$\r$\nPlease quit it and press OK to continue."
    Sleep 2000
    Goto checkforit2
  didntfindit2:

FunctionEnd

; This function is a copy of QuitIt because NSIS enforces weird namespace crap
Function un.QuitIt
  checkforit:
    Processes::FindProcess "btdownloadgui.exe"
    StrCmp $R0 "1" foundit didntfindit

  foundit:
    MessageBox MB_OK "You must quit ${APPNAME} before installing this version.$\r$\nPlease quit it and press OK to continue."
    Sleep 2000
    Goto checkforit
  didntfindit:

  checkforit2:
    Processes::FindProcess "btmaketorrentgui.exe"
    StrCmp $R0 "1" foundit2 didntfindit2

  foundit2:
    MessageBox MB_OK "You must quit ${APPNAME} Make Torrent before installing this version.$\r$\nPlease quit it and press OK to continue."
    Sleep 2000
    Goto checkforit2
  didntfindit2:

FunctionEnd


; This function automatically uninstalls older versions.
; It is largely copied from: 
; http://nsis.sourceforge.net/archive/viewpage.php?pageid=326
Function .onInit

  ReadRegStr $R0 HKLM \
  "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" \
  "UninstallString"
  StrCmp $R0 "" done

  MessageBox MB_OKCANCEL|MB_ICONEXCLAMATION \
  "Another version of ${APPNAME} is already installed. $\n$\nClick `OK` to \
  remove the already installed version and continue installing this version. \ 
  $\n$\nClick `Cancel` to cancel this installation." \
  IDOK uninst
  Abort
  
;Run the uninstaller
uninst:
  Call QuitIt

  ClearErrors
  ExecWait '$R0 _?=$INSTDIR' ;Do not copy the uninstaller to a temp file

  IfErrors no_remove_uninstaller
  no_remove_uninstaller:

done:

FunctionEnd

Section "Install"
  Call IsUserAdmin
  Pop $R0
  StrCmp $R0 "false" abortinstall continueinstall

  abortinstall:
  MessageBox MB_OK "You must have Administrator privileges to install ${APPNAME}." 
  Goto endofinstall

  continueinstall:

  SetOutPath $INSTDIR
  WriteUninstaller "$INSTDIR\uninstall.exe"
  File dist\*.exe
  File dist\*.pyd
  File dist\*.dll
  File dist\library.zip
  File /r dist\images
  File /r dist\lib
  File /r dist\etc
  File /r dist\share
  File redirdonate.html
  File credits.txt
  File LICENSE.txt
  File README.txt

  ; registry entries
  WriteRegStr HKCR .torrent "" bittorrent
  DeleteRegKey HKCR ".torrent\Content Type"
  WriteRegStr HKCR "MIME\Database\Content Type\application/x-bittorrent" Extension .torrent
  WriteRegStr HKCR bittorrent "" "TORRENT File"
  WriteRegBin HKCR bittorrent EditFlags 00000100
  WriteRegStr HKCR "bittorrent\shell" "" open
  WriteRegStr HKCR "bittorrent\shell\open\command" "" `"$INSTDIR\btdownloadgui.exe" --responsefile "%1"`
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "DisplayName" "${APPNAME} ${VERSION}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "UninstallString" '"$INSTDIR\uninstall.exe"'

  ; Add items to start menu
  CreateDirectory "$STARTMENU\Programs\${APPNAME}"
  CreateShortCut "$STARTMENU\Programs\${APPNAME}\Downloader.lnk"   "$INSTDIR\btdownloadgui.exe"
  CreateShortCut "$STARTMENU\Programs\${APPNAME}\Make Torrent.lnk" "$INSTDIR\btmaketorrentgui.exe"
  CreateShortCut "$STARTMENU\Programs\${APPNAME}\Donate.lnk"       "$INSTDIR\redirdonate.html"

  ExecShell open "$INSTDIR\redirdonate.html"
  Sleep 2000
  MessageBox MB_OK "${APPNAME} has been successfully installed!$\r$\n$\r$\nTo use ${APPNAME}, visit a web site which uses it and click on a link."
  BringToFront
  endofinstall:
SectionEnd

Section "Uninstall"
  Call un.QuitIt
  DeleteRegKey HKCR .torrent
  DeleteRegKey HKCR "MIME\Database\Content Type\application/x-bittorrent"
  DeleteRegKey HKCR bittorrent
  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}"
  RMDir /r "$INSTDIR"
  RMDir /r "$STARTMENU\Programs\${APPNAME}"
SectionEnd
