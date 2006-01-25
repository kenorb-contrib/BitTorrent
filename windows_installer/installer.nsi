# The contents of this file are subject to the BitTorrent Open Source License
# Version 1.0 (the License).  You may not copy or use this file, in either
# source code or executable form, except in compliance with the License.  You
# may obtain a copy of the License at http://www.bittorrent.com/license/.
#
# Software distributed under the License is distributed on an AS IS basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied.  See the License
# for the specific language governing rights and limitations under the
# License.

# Written by Bram Cohen, Matt Chisholm and Greg Hazel


;--------------------------------
;Include Modern UI

!include "MUI.nsh"


; replaced by winprepnsi.py
!define VERSION "%VERSION%"
!define APPNAME "%APP_NAME%"

Outfile ${APPNAME}-${VERSION}.exe
Name "${APPNAME}"

;SilentInstall silent

; automatically close the installer when done.
;AutoCloseWindow true

CRCCheck on

SetCompressor /SOLID lzma

; adds xp style support
XPStyle on

InstProgressFlags smooth    
InstallDir "$PROGRAMFILES\${APPNAME}\"
; " this fixes syntax highlighting in xemacs :)

!define EXENAME "bittorrent.exe"
VAR KILLEXENAME
VAR UPGRADE

!define MUI_ICON "images\bittorrent.ico"
;!define MUI_UNICON "images\bittorrent.ico"

!define MUI_LANGDLL_ALWAYSSHOW
!define MUI_LANGDLL_REGISTRY_ROOT HKCU
!define MUI_LANGDLL_REGISTRY_KEY "Software\BitTorrent"
!define MUI_LANGDLL_REGISTRY_VALUENAME "Language"

;--------------------------------
;Pages

  Page custom installer.upgrade
  Page custom uninstall

!define MUI_PAGE_CUSTOMFUNCTION_SHOW  disableBackButton
!define MUI_PAGE_HEADER_TEXT "Warning"
!define MUI_PAGE_HEADER_SUBTEXT "From ${APPNAME}"
!define MUI_LICENSEPAGE_TEXT_TOP "${APPNAME} is 100% FREE, and it always will be."
!define MUI_LICENSEPAGE_BUTTON "$(^NextBtn)"
!define MUI_LICENSEPAGE_TEXT_BOTTOM " "
  !insertmacro MUI_PAGE_LICENSE "installer.warning.rtf"

  Page custom installer.directory installer.directory.leave

  !define MUI_INSTFILESPAGE_FINISHHEADER_SUBTEXT "${APPNAME} has been successfully installed!"
  !insertmacro MUI_PAGE_INSTFILES

!define MUI_FINISHPAGE_TITLE  "${APPNAME} Setup Complete"
!define MUI_FINISHPAGE_RUN "$INSTDIR\bittorrent.exe"
; this is an opt-in url, we want to make it opt-out
;!define MUI_FINISHPAGE_LINK "http://search.bittorrent.com"
;!define MUI_FINISHPAGE_LINK_LOCATION http://search.bittorrent.com
; so we hi-jack the readme option
!define MUI_FINISHPAGE_SHOWREADME_TEXT "&Visit http://search.bittorrent.com to search for torrents!"
!define MUI_FINISHPAGE_SHOWREADME http://search.bittorrent.com

!define MUI_FINISHPAGE_NOREBOOTSUPPORT
  !insertmacro MUI_PAGE_FINISH  

  !insertmacro MUI_UNPAGE_CONFIRM
  !insertmacro MUI_UNPAGE_INSTFILES

;--------------------------------
;Languages
%LANG_MACROS%

; example:
;LangString TEXT_FOO ${LANG_ENGLISH} "Foo thing in English" 


;--------------------------------
;Reserve Files
  
  ;Things that need to be extracted on first (keep these lines before any File command!)
  ;Only for BZIP2 compression
  
  ReserveFile "installer.upgrade.ini"
  ReserveFile "installer.directory.ini"
  !insertmacro MUI_RESERVEFILE_INSTALLOPTIONS

Var HWND
Var DLGITEM

Function uninstall

    ;; IMPORTANT: We cannot ever run any old installers, because they might delete the
    ;; old installation directory, including any data the user might have stored there.
    ;; Newer uninstallers play nice, but we cannot tell them apart.

    ; check here too, since this page is run either way
    ;Call GetUninstallString
    ;Pop $R0

    ;StrCmp $R0 "" nextuninst

    ;;Run the uninstaller
    ;;Do not copy the uninstaller to a temp file
    ;ExecWait '$R0 /S'
    ;IfErrors 0 nextuninst
    ;ExecWait '$R0 /S'
    ;Sleep 2000
    ;IfErrors no_remove_uninstaller
    ;Goto nextuninst
    ;no_remove_uninstaller:
    ;    Call MagicUninstall

    nextuninst:
        Call QuitIt
        ClearErrors
        Delete $INSTDIR\btdownloadgui.exe
        IfErrors deleteerror    
        Delete $INSTDIR\btmaketorrentgui.exe
        IfErrors deleteerror
        Delete $INSTDIR\bittorrent.exe
        IfErrors deleteerror    
        Delete $INSTDIR\maketorrent.exe
        IfErrors deleteerror
        Delete $INSTDIR\choose_language.exe
        IfErrors deleteerror
        goto endofdelete
        deleteerror:    
            MessageBox MB_OK "Removing old BitTorrent exe files failed. You must quit BitTorrent and uninstall it before installing this version."
            Abort
    endofdelete:    

    Call MagicUninstall

    endofuninst:
FunctionEnd

Function installer.upgrade
    !insertmacro MUI_HEADER_TEXT "Upgrade" "${APPNAME} ${VERSION}"

    !insertmacro MUI_INSTALLOPTIONS_INITDIALOG "installer.upgrade.ini"
    Pop $HWND ;HWND of dialog
    
    GetDlgItem $DLGITEM $HWND 1200 ;1200 + Field number - 1
    SendMessage $DLGITEM ${WM_SETTEXT} 0 "STR:A version of ${APPNAME} is already installed."

    GetDlgItem $DLGITEM $HWND 1201 ;1200 + Field number - 1
    SendMessage $DLGITEM ${WM_SETTEXT} 0 "STR:This installer will upgrade to ${APPNAME} ${VERSION}."

    !insertmacro MUI_INSTALLOPTIONS_SHOW
FunctionEnd

Function installer.directory

    StrCmp $UPGRADE "no" OK
    Abort
    
  OK:

    !insertmacro MUI_HEADER_TEXT "Choose Install Location" "Choose the folder in which to install ${APPNAME}"

    StrCpy $4 $INSTDIR
    StrCpy $5 ${APPNAME}

    InstallOptionsEx::initDialog /NOUNLOAD "$PLUGINSDIR\installer.directory.ini"

    Pop $hwnd ;HWND of dialog

    !insertmacro MUI_INSTALLOPTIONS_READ $0 "installer.directory.ini" "Field 3" "State"
    StrCmp $0 "Default Install" 0 show
    GetDlgItem $DLGITEM $hwnd 1204
    EnableWindow $DLGITEM 0
    GetDlgItem $DLGITEM $hwnd 1205
    EnableWindow $DLGITEM 0

  show:    
    InstallOptionsEx::show
    Pop $R0
FunctionEnd

Function installer.directory.leave
  ; At this point the user has either pressed Next or one of our custom buttons
  ; We find out which by reading from the INI file
  !insertmacro MUI_INSTALLOPTIONS_READ $0 "installer.directory.ini" "Settings" "State"
  StrCmp $0 0 page
  StrCmp $0 3 droplist
  Abort ; Return to the page

droplist:
  ; Make the DirRequest field depend on the droplist
  !insertmacro MUI_INSTALLOPTIONS_READ $0 "installer.directory.ini" "Field 3" "State"
  StrCmp $0 "Custom Location" +3
    StrCpy $0 0
  Goto +2
    StrCpy $0 1
  GetDlgItem $1 $hwnd 1204 ; DirRequest control
  EnableWindow $1 $0
  GetDlgItem $1 $hwnd 1205 ; button (the following control)
  EnableWindow $1 $0
  Abort ; Return to the page

page:
  !insertmacro MUI_INSTALLOPTIONS_READ $0 "installer.directory.ini" "Settings" "Notify"
  StrCmp $0 "ONNEXT" save
  Abort

save:  
  ; At this point we know the Next button was pressed, so perform any validation and reading
  !insertmacro MUI_INSTALLOPTIONS_READ $INSTDIR "installer.directory.ini" "Field 5" "State"

FunctionEnd

Function disableBackButton
    FindWindow $0 "#32770" "" $HWNDPARENT
    GetDlgItem $1 $HWNDPARENT 3 ; back button
    ShowWindow $1 ${SW_HIDE}
FunctionEnd

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

!macro GetUninstallString UN
Function ${UN}GetUninstallString
    ReadRegStr $R0 HKLM \
    "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" \
    "UninstallString"
    Push $R0
FunctionEnd
!macroend

!macro GetOldPath UN
Function ${UN}GetOldPath
    Call ${UN}GetUninstallString
    
    Pop $0
    
    StrCpy $1 $0 1 0 ; get firstchar
    StrCmp $1 '"' "" getparent
      ; if first char is ", let's remove "s first.
      StrCpy $0 $0 "" 1
      StrCpy $1 0
      rqloop:
        StrCpy $2 $0 1 $1
        StrCmp $2 '"' rqdone
        StrCmp $2 "" rqdone
        IntOp $1 $1 + 1
        Goto rqloop
      rqdone:
      StrCpy $0 $0 $1
    getparent:
    ; the uninstall string goes to an EXE, lets get the directory.
    StrCpy $1 -1
    gploop:
      StrCpy $2 $0 1 $1
      StrCmp $2 "" gpexit
      StrCmp $2 "\" gpexit
      #"emacs
      IntOp $1 $1 - 1
      Goto gploop
    gpexit:
    StrCpy $0 $0 $1

    Push $0

FunctionEnd
!macroend

!macro CheckForIt UN
Function ${UN}CheckForIt

    Processes::FindProcess $KILLEXENAME
    StrCmp $R0 "1" foundit didntfindit

  foundit:
    MessageBox MB_OKCANCEL "You must quit ${APPNAME} ($KILLEXENAME) \
    before installing this version.$\r$\nPlease quit it and press \
    OK to continue." IDOK tryagain
    Abort

  tryagain:
        
    Sleep 2000
    Processes::FindProcess $KILLEXENAME
    StrCmp $R0 "1" stillthere didntfindit

  stillthere:
    MessageBox MB_OKCANCEL "There is still a copy of ${APPNAME} \
    ($KILLEXENAME) running.$\r$\nPress OK to force-quit the application, \
    or Cancel to exit." IDOK killit
    Abort

  killit:
    KillProcDLL::KillProc $KILLEXENAME
    Sleep 1000

  didntfindit:

FunctionEnd
!macroend

!macro QuitIt UN
Function ${UN}QuitIt
    StrCpy $KILLEXENAME "btdownloadgui.exe"
    Call ${UN}CheckForIt
    StrCpy $KILLEXENAME "bittorrent.exe"
    Call ${UN}CheckForIt
    StrCpy $KILLEXENAME "btmaketorrentgui.exe"
    Call ${UN}CheckForIt
    StrCpy $KILLEXENAME "maketorrent.exe"
    Call ${UN}CheckForIt
    StrCpy $KILLEXENAME "choose_language.exe"
    Call ${UN}CheckForIt
    StrCpy $KILLEXENAME ""
FunctionEnd
!macroend

!macro MagicUninstall UN
Function ${UN}MagicUninstall
  ;; this would remove other associations / context menu items too
  ; DeleteRegKey HKCR .torrent
  ; DeleteRegKey HKCR "MIME\Database\Content Type\application/x-bittorrent"

  ;; disassociate our missing Application manually, windows takes care of the rest
  DeleteRegKey HKCR "Applications\${EXENAME}.exe"
  DeleteRegKey HKLM "Software\Classes\Applications\${EXENAME}.exe"
  ; just in case
  DeleteRegKey HKCR "Applications\btdownloadgui.exe"
  DeleteRegKey HKLM "Software\Classes\Applications\btdownloadgui.exe"

  ;; be nice and put back what we removed
  ReadRegStr $R1 HKCR "bittorrent\shell\open\command" "backup"
  StrCmp $R1 "" delete restore
 restore:
  WriteRegStr HKCR "bittorrent\shell\open\command" "" $R1
  goto continue
 delete:
  DeleteRegKey HKCR bittorrent
 continue:
  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}"

  ;; we do not currently restore backups on torrent:// stuff
  DeleteRegKey HKCR torrent
  
  Call ${UN}GetOldPath
  Pop $R0
  StrCmp $R0 "" 0 remove
  StrCpy $R0 $INSTDIR
 remove:
     

  ; some users like to store important data in our directory
  ; be nice to them
  ;RMDir /r "$R0"

  Delete "$R0\*.exe"
  Delete "$R0\*.pyd"
  Delete "$R0\*.dll"
  Delete "$R0\library.zip"
  RMDir /r "$R0\images"
  RMDir /r "$R0\lib"
  RMDir /r "$R0\etc"
  RMDir /r "$R0\share"
  RMDir /r "$R0\locale"
  Delete "$R0\redirdonate.html"
  Delete "$R0\credits.txt"
  Delete "$R0\credits-l10n.txt"
  Delete "$R0\LICENSE.txt"
  Delete "$R0\README.txt"
  Delete "$R0\TRACKERLESS.txt"
  Delete "$R0\public.key"

  ClearErrors
  RMDir "$R0"
  
  IfErrors 0 dontwarn
  MessageBox MB_OK "Not deleting $R0,$\r$\nbecause there are extra files or directories in it, or it is in use."   
 dontwarn:  
  
  SetShellVarContext current
  Delete "$SMSTARTUP\${APPNAME}.lnk"

  SetShellVarContext all
  Delete "$DESKTOP\${APPNAME}.lnk"
  RMDir /r "$SMPROGRAMS\${APPNAME}"
  
FunctionEnd
!macroend

;awesome voodoo
!insertmacro CheckForIt ""
!insertmacro CheckForIt "un."

!insertmacro QuitIt ""
!insertmacro QuitIt "un." 

!insertmacro GetUninstallString ""
!insertmacro GetUninstallString "un."

!insertmacro GetOldPath ""
!insertmacro GetOldPath "un." 

!insertmacro MagicUninstall ""
!insertmacro MagicUninstall "un." 

Function .onInit
    BringToFront

	;Language selection dialog
    !insertmacro MUI_LANGDLL_DISPLAY

    Call QuitIt
    ClearErrors

    !insertmacro MUI_INSTALLOPTIONS_EXTRACT "installer.directory.ini"  

    ; check for an installed copy, and add the upgrade page if needed
    Call GetOldPath
    Pop $R0
    StrCmp $R0 "" notupgrading
    StrCpy $UPGRADE "yes"
    StrCpy $INSTDIR $R0

    !insertmacro MUI_INSTALLOPTIONS_EXTRACT "installer.upgrade.ini"

    Goto done
  notupgrading:
    StrCpy $UPGRADE "no"
  done:
FunctionEnd

Section "Install" SecInstall
  SectionIn 1 2

  Call IsUserAdmin
  Pop $R0
  StrCmp $R0 "false" abortinstall continueinstall

  abortinstall:
  MessageBox MB_OK "You must have Administrator privileges to install ${APPNAME}." 
  Goto endofinstall

  continueinstall:

  SetOverwrite try
  
  SetOutPath $INSTDIR
  WriteUninstaller "$INSTDIR\uninstall.exe"

  IntFmt $0 "%u" 0

  goto skip
 files:     
  IntOp $0 $0 + 1
  IntCmp $0 30 ohcrap
  Sleep 1000
 skip:

  File dist\*.exe
  IfErrors files
  File dist\*.pyd
  IfErrors files
  File dist\*.dll
  IfErrors files
  File dist\library.zip
  IfErrors files
  File /r dist\images
  IfErrors files
  File /r dist\lib
  IfErrors files
  File /r dist\etc
  IfErrors files
  File /r dist\share
  IfErrors files
  File /r dist\locale
  IfErrors files
  File redirdonate.html
  IfErrors files
  File credits.txt
  IfErrors files
  File credits-l10n.txt
  IfErrors files
  File LICENSE.txt
  IfErrors files
  File README.txt
  IfErrors files
  File TRACKERLESS.txt
  IfErrors files
  File public.key
  IfErrors files

  goto success
 ohcrap:
  MessageBox MB_OK "While installing BitTorrent, a critical timeout occured. Please reboot, and retry the installer."
  Abort
 success:

  ; registry entries

  ; in super old versions of BitTorrent (2.x) some Bad Things were done.
  ; if we don not clean them up before installing, users get "Invalid Menu Handle"
  ; after upgrading.
  DeleteRegKey HKCR "torrent_auto_file"
  DeleteRegValue HKCU "Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\.torrent\" "ProgId"

  ; this guards against a reinstallation to a different directory  (like d:\...) causing Invalid Menu Handle
  DeleteRegKey HKCR "Applications\btdownloadgui.exe"
  DeleteRegKey HKCR "Applications\bittorrent.exe"
  DeleteRegKey HKCR "Applications\${EXENAME}"
  DeleteRegKey HKLM "Software\Classes\Applications\btdownloadgui.exe"
  DeleteRegKey HKLM "Software\Classes\Applications\bittorrent.exe"
  DeleteRegKey HKLM "Software\Classes\Applications\${EXENAME}"
  
  ;; make us the default handler for BT files
  WriteRegStr HKCR .torrent "" bittorrent
  DeleteRegKey HKCR ".torrent\Content Type"
  ;; This line maks it so that BT sticks around as an option 
  ;; after installing some other default handler for torrent files
  WriteRegStr HKCR ".torrent\OpenWithProgids" "bittorrent" ""

  ; this prevents user-preference from generating "Invalid Menu Handle" by looking for an app
  ; that no longer exists, and instead points it at us.
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\.torrent\" Application "${EXENAME}"
  WriteRegStr HKCR "Applications\${EXENAME}\shell" "" open
  WriteRegStr HKCR "Applications\${EXENAME}\shell\open\command" "" `"$INSTDIR\${EXENAME}" --responsefile "%1"`
  
  ;; Add a mime type
  WriteRegStr HKCR "MIME\Database\Content Type\application/x-bittorrent" Extension .torrent

  ;; Add a shell command to match the 'bittorrent' handler described above
  WriteRegStr HKCR bittorrent "" "TORRENT File"
  WriteRegBin HKCR bittorrent EditFlags 00000100
  ;; make us the default handler for bittorrent://
  WriteRegBin HKCR bittorrent "URL Protocol" 0
  WriteRegStr HKCR "bittorrent\Content Type" "" "application/x-bittorrent"
  WriteRegStr HKCR "bittorrent\DefaultIcon" "" "$INSTDIR\${EXENAME},0"
  WriteRegStr HKCR "bittorrent\shell" "" open

  ReadRegStr $R1 HKCR "bittorrent\shell\open\command" ""
  StrCmp $R1 "" continue

  WriteRegStr HKCR "bittorrent\shell\open\command" "backup" $R1

continue:
  WriteRegStr HKCR "bittorrent\shell\open\command" "" `"$INSTDIR\${EXENAME}" --responsefile "%1"`

  ;; Add a shell command to handle torrent:// stuff
  WriteRegStr HKCR torrent "" "TORRENT File"
  WriteRegBin HKCR torrent EditFlags 00000100
  ;; make us the default handler for torrent://
  WriteRegBin HKCR torrent "URL Protocol" 0
  WriteRegStr HKCR "torrent\Content Type" "" "application/x-bittorrent"
  WriteRegStr HKCR "torrent\DefaultIcon" "" "$INSTDIR\${EXENAME},0"
  WriteRegStr HKCR "torrent\shell" "" open

  ReadRegStr $R1 HKCR "torrent\shell\open\command" ""
  WriteRegStr HKCR "torrent\shell\open\command" "backup" $R1
  
  WriteRegStr HKCR "torrent\shell\open\command" "" `"$INSTDIR\${EXENAME}" --responsefile "%1"`

  ;; Automagically register with the Windows Firewall
  WriteRegStr HKLM "SYSTEM\CurrentControlSet\Services\SharedAccess\Parameters\FirewallPolicy\StandardProfile\AuthorizedApplications\List" "$INSTDIR\${EXENAME}" `$INSTDIR\${EXENAME}:*:Enabled:${APPNAME}`

  ;; Info about install/uninstall 
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "DisplayName" "${APPNAME} ${VERSION}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "UninstallString" '"$INSTDIR\uninstall.exe"'

  ; Add items to start menu
  SetShellVarContext current
  CreateShortCut "$SMSTARTUP\${APPNAME}.lnk"                  "$INSTDIR\${EXENAME}"

  ; Create desktop link
  SetShellVarContext all
  CreateShortCut "$DESKTOP\${APPNAME}.lnk"                    "$INSTDIR\${EXENAME}"

  CreateDirectory "$SMPROGRAMS\${APPNAME}"
  CreateShortCut "$SMPROGRAMS\${APPNAME}\Downloader.lnk"      "$INSTDIR\${EXENAME}"
  CreateShortCut "$SMPROGRAMS\${APPNAME}\Make Torrent.lnk"    "$INSTDIR\maketorrent.exe"
  CreateShortCut "$SMPROGRAMS\${APPNAME}\Donate.lnk"          "$INSTDIR\redirdonate.html"
  CreateShortCut "$SMPROGRAMS\${APPNAME}\Choose Language.lnk" "$INSTDIR\choose_language.exe"

  IfSilent launch_anyway not_silent
  launch_anyway:
  ExecShell open "$INSTDIR\${EXENAME}"
  not_silent:

  BringToFront
  endofinstall:
SectionEnd

Function un.onInit
  ;; gets the stored language from install
  !insertmacro MUI_UNGETLANGUAGE
FunctionEnd

Section "Uninstall"
  Call un.QuitIt
  ; this should not go in MagicUninstall
  ; because we want to keep the preference between upgrades
  DeleteRegKey HKCU "Software\BitTorrent\Language"
  Call un.MagicUninstall
SectionEnd
