# The contents of this file are subject to the BitTorrent Open Source License
# Version 1.0 (the License).  You may not copy or use this file, in either
# source code or executable form, except in compliance with the License.  You
# may obtain a copy of the License at http://www.bittorrent.com/license/.
#
# Software distributed under the License is distributed on an AS IS basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied.  See the License
# for the specific language governing rights and limitations under the
# License.

# Written by Bram Cohen and Matt Chisholm

!define VERSION "3.9.1-Beta"
!define APPNAME "BitTorrent"
Outfile ${APPNAME}-${VERSION}.exe
Name "${APPNAME}"
SilentInstall silent
SetCompressor lzma
InstallDir "$PROGRAMFILES\${APPNAME}\"

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
  ClearErrors
  ExecWait '$R0 _?=$INSTDIR' ;Do not copy the uninstaller to a temp file

  IfErrors no_remove_uninstaller
  no_remove_uninstaller:

done:

FunctionEnd

Section "Install"
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
SectionEnd

Section "Uninstall"
  DeleteRegKey HKCR .torrent
  DeleteRegKey HKCR "MIME\Database\Content Type\application/x-bittorrent"
  DeleteRegKey HKCR bittorrent
  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}"
  RMDir /r "$INSTDIR"
  RMDir /r "$STARTMENU\Programs\${APPNAME}"
SectionEnd
