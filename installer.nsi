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

!define VERSION "4.1.4-Beta"
!define APPNAME "BitTorrent"
Outfile ${APPNAME}-${VERSION}.exe
Name "${APPNAME}"
SilentInstall silent
SetCompressor lzma
InstallDir "$PROGRAMFILES\${APPNAME}\"
; " this fixes syntax highlighting in xemacs :)

VAR EXENAME
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

Function CheckForIt
	checkforit:
		Processes::FindProcess $EXENAME
		StrCmp $R0 "1" foundit didntfindit

	waitforit:
		Sleep 2000
		Goto checkforit
 
	foundit:
		MessageBox MB_OKCANCEL "You must quit ${APPNAME} ($EXENAME) \
		before installing this version.$\r$\nPlease quit it and press \
		OK to continue." IDOK waitforit 
		Abort 
	didntfindit:

	KillProcDLL::KillProc $EXENAME
FunctionEnd
	
Function QuitIt
	StrCpy $EXENAME "btdownloadgui.exe"
	Call CheckForIt
	StrCpy $EXENAME "bittorrent.exe"
	Call CheckForIt
 	StrCpy $EXENAME "btmaketorrentgui.exe"
	Call CheckForIt
	StrCpy $EXENAME "maketorrent.exe"
	Call CheckForIt
	StrCpy $EXENAME ""
FunctionEnd

; These functions are copies because NSIS enforces weird namespace crap
Function un.CheckForIt
	checkforit:
		Processes::FindProcess $EXENAME
		StrCmp $R0 "1" foundit didntfindit

	waitforit:
		Sleep 2000
		Goto checkforit
 
	foundit:
		MessageBox MB_OKCANCEL "You must quit ${APPNAME} ($EXENAME) \
		before uninstalling it.$\r$\nPlease quit it and press \
		OK to continue." IDOK waitforit 
		Abort 
	didntfindit:

	KillProcDLL::KillProc $EXENAME
FunctionEnd
	
Function un.QuitIt
	StrCpy $EXENAME "btdownloadgui.exe"
	Call un.CheckForIt
	StrCpy $EXENAME "bittorrent.exe"
	Call un.CheckForIt
 	StrCpy $EXENAME "btmaketorrentgui.exe"
	Call un.CheckForIt
	StrCpy $EXENAME "maketorrent.exe"
	Call un.CheckForIt
	StrCpy $EXENAME ""
FunctionEnd

; This function automatically uninstalls older versions.
; It is partly copied from: 
; http://nsis.sourceforge.net/archive/viewpage.php?pageid=326
Function .onInit
	Call QuitIt
	ClearErrors

	ReadRegStr $R0 HKLM \
	"Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" \
	"UninstallString"
	StrCmp $R0 "" endofuninst

	MessageBox MB_OKCANCEL|MB_ICONEXCLAMATION "${APPNAME} is already \
	installed. $\n$\nClick `OK` to upgrade to ${APPNAME} ${VERSION}." \
	IDOK uninst
	Abort
	
	;Run the uninstaller
	uninst:
		;Do not copy the uninstaller to a temp file
		ExecWait '$R0 _?=$INSTDIR /S' 
		IfErrors no_remove_uninstaller
		Goto endofuninst
	no_remove_uninstaller: 
		MessageBox MB_OK "Uninstallation failed. Aborting."
		Abort
	endofuninst:

	MessageBox MB_OKCANCEL "${APPNAME} is 100% FREE, and it always will be. $\n$\n\
	Some malicious websites are charging money for ${APPNAME}, committing credit card$\n\
	fraud, and infecting computers with malicious software. If you did not download$\n\
	this copy of ${APPNAME} from http://www.bittorrent.com/, PROTECT YOURSELF NOW!$\n\
	* Check your computer for malicious software.$\n\
	* Check your credit card bill for unauthorized charges.$\n\
	* Cancel the installation NOW and download ${APPNAME} for free from $\n\
	http://www.bittorrent.com/\
	" IDOK done

	Abort
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
  File /r dist\locale
  File redirdonate.html
  File credits.txt
  File credits-l10n.txt
  File LICENSE.txt
  File README.txt
  File public.key

  ; registry entries
  ;; make us the default handler for BT files
  WriteRegStr HKCR .torrent "" bittorrent
  DeleteRegKey HKCR ".torrent\Content Type"
  ;; This line might make it so that BT sticks around as an option 
  ;; after installing some other default handler for torrent files
  ;WriteRegStr HKCR ".Torrent\OpenWithProgids" "bittorrent" 

  ;; Add a mime type
  WriteRegStr HKCR "MIME\Database\Content Type\application/x-bittorrent" Extension .torrent

  ;; Add a shell command to match the 'bittorrent' handler described above
  WriteRegStr HKCR bittorrent "" "TORRENT File"
  WriteRegBin HKCR bittorrent EditFlags 00000100
  WriteRegStr HKCR "bittorrent\shell" "" open
  WriteRegStr HKCR "bittorrent\shell\open\command" "" `"$INSTDIR\bittorrent.exe" --responsefile "%1"`

  ;; Info about install/uninstall 
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "DisplayName" "${APPNAME} ${VERSION}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "UninstallString" '"$INSTDIR\uninstall.exe"'

  ; Add items to start menu
  SetShellVarContext all
  CreateDirectory "$SMPROGRAMS\${APPNAME}"
  CreateShortCut "$SMPROGRAMS\${APPNAME}\${APPNAME}.lnk"   "$INSTDIR\bittorrent.exe"
  CreateShortCut "$SMPROGRAMS\${APPNAME}\Make Torrent.lnk" "$INSTDIR\maketorrent.exe"
  CreateShortCut "$SMPROGRAMS\${APPNAME}\Donate.lnk"       "$INSTDIR\redirdonate.html"

  ExecShell open "$INSTDIR\redirdonate.html"
  Sleep 2000
  MessageBox MB_OK "${APPNAME} has been successfully installed!$\r$\n$\r$\nVisit http://search.bittorrent.com/ to download torrent files."
  BringToFront
  ExecShell open "$INSTDIR\bittorrent.exe"
  endofinstall:
SectionEnd

Section "Uninstall"
  Call un.QuitIt
  DeleteRegKey HKCR .torrent
  DeleteRegKey HKCR "MIME\Database\Content Type\application/x-bittorrent"
  DeleteRegKey HKCR bittorrent
  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}"
  RMDir /r "$INSTDIR"
  SetShellVarContext all
  RMDir /r "$SMPROGRAMS\${APPNAME}"
SectionEnd
