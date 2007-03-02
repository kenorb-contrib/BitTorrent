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
VAR TORRENTURL


Function RunBitTorrent
  # chdir
  SetOutPath $INSTDIR
  StrCmp $TORRENTURL "" notorrent
  Exec '"$INSTDIR\${EXENAME}" "$TORRENTURL"'
  Goto end
  notorrent:
  Exec '"$INSTDIR\${EXENAME}"'
  end:
FunctionEnd


# ACHTUNG: Fancy!
# Pull the magic torrent URL out of the end of the installer exe.  If
# it's non-empty, don't offer the option to not run BT on FINISHPAGE,
# and set $TORRENTURL so that RunBitTorrent will pass it on to BT
Function FinishPre
  Call GetExeName
  IfFileExists "$R0" ok

  StrCpy $R0 $CMDLINE
  IfFileExists "$R0" ok
  
  StrCpy $R0 "$EXEDIR\${APPNAME}-${VERSION}.exe"
  IfFileExists "$R0" ok

  Goto notfound

ok:
  ClearErrors
  FileOpen $0 "$R0" r
  IfErrors notfound
  FileSeek $0 -2048 END
  StrCpy $3 ""

loop:
  FileReadByte $0 $1
  StrCmp $1 "" done
  ; space padded
  StrCmp $1 "32" done
  IntFmt $2 "%c" $1
  StrCpy $3 "$3$2"
  goto loop
done:
  StrCpy $TORRENTURL "$3"

  StrCmp $TORRENTURL "" notfound
  
!insertmacro MUI_INSTALLOPTIONS_WRITE "ioSpecial.ini" "Field 4" "State" "1"
!insertmacro MUI_INSTALLOPTIONS_WRITE "ioSpecial.ini" "Field 4" "Type" "Label"
!insertmacro MUI_INSTALLOPTIONS_WRITE "ioSpecial.ini" "Field 4" "Text" "BitTorrent will run automatically when you click 'Finish'."

notfound:
FunctionEnd


!define MUI_ICON "images\bittorrent.ico"
!define MUI_UNICON "images\bittorrent.ico"

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
!define MUI_FINISHPAGE_RUN
!define MUI_FINISHPAGE_RUN_FUNCTION "RunBitTorrent"
; this is an opt-in url, we want to make it opt-out
!define MUI_FINISHPAGE_LINK "&Visit BitTorrent.com to search for torrents!"
!define MUI_FINISHPGE_LINK_LOCATION http://www.bittorrent.com
; so we hi-jack the readme option
!define MUI_FINISHPAGE_SHOWREADME
!define MUI_FINISHPAGE_SHOWREADME_TEXT "Create a &shortcut to BitTorrent on the Desktop"
!define MUI_FINISHPAGE_SHOWREADME_FUNCTION "desktop_shortcut"

!define MUI_FINISHPAGE_NOREBOOTSUPPORT
!define MUI_PAGE_CUSTOMFUNCTION_PRE "FinishPre"
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


Function desktop_shortcut
    ; Create desktop link
    SetShellVarContext all
    CreateShortCut "$DESKTOP\${APPNAME}.lnk"                    "$INSTDIR\${EXENAME}"
FunctionEnd

Function uninstall

    ;; IMPORTANT: We cannot ever run any old installers, because they
    ;; might delete the old installation directory, including any data
    ;; the user might have stored there.  Newer uninstallers play
    ;; nice, but we cannot tell them apart.

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


!macro EnhancedFindWindow UN
Function ${UN}EnhancedFindWindow
  ; input, save variables
  Exch  $0   # part of the wt to search for
  Exch
  Exch  $1   # the wcn
  Push  $2   # length of $0
  Push  $3   # return code
  Push  $4   # window handle
  Push  $5   # returned window name
  Push  $6   # max length of 5

  ; set up the variables
  SetPluginUnload  alwaysoff     # recommended, if u're using the \
                                   system plugin
  StrCpy  $4  0                  # FindWindow wouldn't work without
;  StrCpy  $2  ${NSIS_MAX_STRLEN} # the max length of string variables
  StrLen  $2  $0
  StrLen  $5  $4                 # it's length

 ; loop to search for open windows
 search_loop:
  FindWindow  $4  ""  ""  0  $4
   IntCmp  $4  0  search_failed
    IsWindow  $4  0  search_failed

     System::Call  \
      'user32.dll::GetClassName(i, t, *i) i(r4r4, .r5, r6r6) .r3'
       IntCmp  $3  0  search_loop
       StrCmp $5 $1 0 search_loop

         System::Call  \
           'user32.dll::GetWindowText(i, t, *i) i(r4r4, .r5, r6r6) .r3'
         IntCmp  $3  0  search_loop
           StrCpy  $3  $5
           StrCpy  $5  $5  $2  0
           StrCmp  $0  $5 search_end search_loop

 ; no matching class-name found, return "failed"
 search_failed:
  StrCpy  $0  "failed"
  StrCpy  $1  "failed"

 ; search ended, output and restore variables
 search_end:
  SetPluginUnload  manual  # the system-plugin can now unload itself
  System::Free  0          # free the memory

  StrCpy $0 $4
  StrCpy $1 $5

  Pop  $6
  Pop  $5
  Pop  $4
  Pop  $3
  Pop  $2
  Exch  $1
  Exch
  Exch  $0
FunctionEnd
!macroend


; CloseBitTorrent: this will in a loop send the BitTorrent window the WM_CLOSE
; message until it does not find a valid BitTorrent window
;
!macro CloseBitTorrent UN
Function ${UN}CloseBitTorrent
  Push $0

  IntFmt $R4 "%u" 0

  goto skip
  killloop:
    DetailPrint "Killing BitTorrent"
    KillProcDLL::KillProc "bittorrent.exe"
  loop:     
    Sleep 1000
    IntOp $R4 $R4 + 1
    IntCmp $R4 5 done
  skip:
    DetailPrint "Looking for running copies of BitTorrent"

    Push "wxWindowClassNR"   # the wcn
    Push "BitTorrent"   # the known part of the wt
    Call ${UN}EnhancedFindWindow
    Pop  $0   # will contain the window's handle
    Pop  $1   # will containg the full wcn
              # both will containg "failed", if no matching wcn was found

    StrCmp $0 "failed" done
    StrCmp $0 "0" done
    DetailPrint "Stopping BitTorrent"
    SendMessage $0 16 0 0 # WM_CLOSE == 16
    Goto loop
  done:

  IntFmt $R4 "%u" 0
  Processes::FindProcess "bittorrent.exe"
  StrCmp $R0 "1" killloop reallydone

  reallydone:
  Pop $0
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

    # try nicely first
    Call ${UN}CloseBitTorrent

    # kill all the old ones    
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

!macro MozillaPluginDir
 
  Push $R0
  Push $R1
  Push $R2
 
  !define Index 'Line${__LINE__}'
  StrCpy $R1 "0"
  StrCpy $R2 "no mozilla"
 
  "${Index}-Loop:"
 
  ; Check for Key
  EnumRegKey $R0 HKLM "SOFTWARE\Mozilla" "$R1"
  StrCmp $R0 "" "${Index}-End"
  IntOp $R1 $R1 + 1
  ReadRegStr $R2 HKLM "SOFTWARE\Mozilla\$R0\Extensions" "Plugins"
  StrCmp $R2 "" "${Index}-Loop" "${Index}-End"
 
  "${Index}-End:"
 
  !undef Index
 
  Push $R2
  Exch 1
  Pop $R2
  Exch 1
  Pop $R1
  Exch 1
  Pop $R0
 
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
  
  ; unregister the MSIE plugin
  UnRegDLL "$R0\BitTorrentIE.1.dll"
  UnRegDLL "$R0\BitTorrentIE.2.dll"

  ; remove the mozilla plugin
  !insertmacro MozillaPluginDir
  Pop $R1
  StrCmp $R1 "no mozilla" no_mozilla
      Delete "$R1\npbittorrent.dll"
  no_mozilla:

  ; some users like to store important data in our directory
  ; be nice to them
  ;RMDir /r "$R0"

  Delete "$R0\*.exe"
  Delete "$R0\*.manifest"
  Delete "$R0\*.pyd"
  Delete "$R0\*.dll"
  Delete "$R0\library.zip"
  RMDir /r "$R0\images"
  RMDir /r "$R0\lib"
  RMDir /r "$R0\locale"
  Delete "$R0\redirdonate.html"
  Delete "$R0\credits.txt"
  Delete "$R0\LICENSE.txt"
  Delete "$R0\README.txt"
  Delete "$R0\TRACKERLESS.txt"
  Delete "$R0\public.key"

  ClearErrors
  RMDir "$R0"
  
  IfErrors 0 dontwarn
  ; no need for a warning, it is just annoying
  ;MessageBox MB_OK "Not deleting $R0,$\r$\nbecause there are extra files or directories in it, or it is in use."   
 dontwarn:  
  
  ;SetShellVarContext current
  SetShellVarContext all
  Delete "$SMSTARTUP\${APPNAME}.lnk"

  SetShellVarContext all
  Delete "$DESKTOP\${APPNAME}.lnk"
  RMDir /r "$SMPROGRAMS\${APPNAME}"
  
FunctionEnd
!macroend

;awesome voodoo
!insertmacro EnhancedFindWindow ""
!insertmacro EnhancedFindWindow "un."

!insertmacro CloseBitTorrent ""
!insertmacro CloseBitTorrent "un."

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

Function GetExeName
   StrLen $R3 $CMDLINE
   
   ;Check for quote or space
   StrCpy $R0 $CMDLINE 1
   StrCmp $R0 '"' 0 +3
     StrCpy $R1 '"'
     Goto loop
   StrCpy $R1 " "

   StrCpy $R2 0

  
   loop:
     IntOp $R2 $R2 + 1
     StrCpy $R0 $CMDLINE 1 $R2
     StrCmp $R0 $R1 get
     StrCmp $R2 $R3 get
     Goto loop
   
   get:   
     IntOp $R1 $R3 - $R2
     IntOp $R1 $R1 - 1
     StrCpy $R0 $CMDLINE $R2 $R1
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

  ; unregister any existing MSIE plugins, just in case
  UnRegDLL "$INSTDIR\BitTorrentIE.1.dll"
  UnRegDLL "$INSTDIR\BitTorrentIE.2.dll"

  goto skip
 files:     
  IntOp $0 $0 + 1
  IntCmp $0 30 ohcrap
  Sleep 1000
 skip:

  ; just in case
  ClearErrors

  File plugins\IE\plugin.inf
  IfErrors files

  ; this one could fail. who cares.
  File plugins\BitTorrentIE.2.dll
  ClearErrors

  File dist\*.exe
  IfErrors files
  File dist\*.manifest
  IfErrors files
  File dist\*.pyd
  IfErrors files

  ; can't do this anymore due to a fucked MSIE plugin version that could be
  ; using mfc71.dll or in some rare cases MSVCR71.dll (see below)
  ;File dist\*.dll
  ;IfErrors files
  
  ; these could fail. who cares.
  File dist\mfc71.dll
  ClearErrors
  File dist\MSVCR71.dll
  ClearErrors

  File dist\pythoncom24.dll
  IfErrors files
  File dist\wxmsw26uh_gizmos_vc.dll
  IfErrors files
  File dist\pywintypes24.dll
  IfErrors files
  File dist\wxmsw26uh_stc_vc.dll
  IfErrors files
  File dist\python24.dll
  IfErrors files
  File dist\unicows.dll
  IfErrors files
  File dist\wxmsw26uh_vc.dll
  IfErrors files

  File dist\library.zip
  IfErrors files
  File /r dist\images
  IfErrors files
  File redirdonate.html
  IfErrors files
  File credits.txt
  IfErrors files
  File LICENSE.txt
  IfErrors files
  File README.txt
  IfErrors files
  File TRACKERLESS.txt
  IfErrors files
  File public.key
  IfErrors files
  File addrmap.dat
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
  WriteRegStr HKCR "Applications\${EXENAME}\shell\open\command" "" `"$INSTDIR\${EXENAME}" "%1"`
  
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
  WriteRegStr HKCR "bittorrent\shell\open\command" "" `"$INSTDIR\${EXENAME}" "%1"`

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
  
  WriteRegStr HKCR "torrent\shell\open\command" "" `"$INSTDIR\${EXENAME}" "%1"`

  ;; Automagically register with the Windows Firewall
  WriteRegStr HKLM "SYSTEM\CurrentControlSet\Services\SharedAccess\Parameters\FirewallPolicy\StandardProfile\AuthorizedApplications\List" "$INSTDIR\${EXENAME}" `$INSTDIR\${EXENAME}:*:Enabled:${APPNAME}`

  ;; Tell MSIE 7+ that it's okay to run the Microsoft DRM ActiveX control
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Ext\PreApproved\{760C4B83-E211-11D2-BF3E-00805FBE84A6}" "" ""

  ;; Info about install/uninstall 
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "DisplayName" "${APPNAME} ${VERSION}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "UninstallString" '"$INSTDIR\uninstall.exe"'

  ; SHCNE_ASSOCCHANGED == 0x8000000
  ; prevents a reboot where it would be needed in rare cases otherwise
  System::Call 'Shell32::SHChangeNotify(i 0x8000000, i 0, i 0, i 0)'

  ; Add items to start menu

  ; newer versions of BT use the registry 'run' section
  SetShellVarContext current
  Delete "$SMSTARTUP\${APPNAME}.lnk"

  SetShellVarContext all
  ;CreateShortCut "$SMSTARTUP\${APPNAME}.lnk"                  "$INSTDIR\${EXENAME}"

  CreateDirectory "$SMPROGRAMS\${APPNAME}"
  CreateShortCut "$SMPROGRAMS\${APPNAME}\BitTorrent.lnk"      "$INSTDIR\${EXENAME}"
  CreateShortCut "$SMPROGRAMS\${APPNAME}\Make Torrent.lnk"    "$INSTDIR\maketorrent.exe"
  CreateShortCut "$SMPROGRAMS\${APPNAME}\Donate.lnk"          "$INSTDIR\redirdonate.html"
  CreateShortCut "$SMPROGRAMS\${APPNAME}\Choose Language.lnk" "$INSTDIR\choose_language.exe"

  IfSilent launch_anyway not_silent
  launch_anyway:
  ExecShell open "$INSTDIR\${EXENAME}"
  not_silent:


  !insertmacro MozillaPluginDir
  Pop $R0
  StrCmp $R0 "no mozilla" no_mozilla
  StrCpy $R1 $R0

  SetOutPath $R0
  File plugins\npbittorrent.dll

  Processes::FindProcess "firefox.exe"
  StrCmp $R0 "1" firefox check_for_mozilla

  firefox:
  ClearErrors
  Exec '"$R1..\firefox.exe" "about:plugins"'
  IfErrors warn_ff
  Goto check_for_mozilla
  warn_ff:
  MessageBox  MB_OK "You will need to restart FireFox for the changes to take effect."
  BringToFront

  check_for_mozilla:
  Processes::FindProcess "mozilla.exe"
  StrCmp $R0 "1" mozilla didntfindit  

  mozilla:
  ClearErrors
  Exec '"$R1..\mozilla.exe" "about:plugins"'
  IfErrors warn_moz
  Goto didntfindit
  warn_moz:
  MessageBox  MB_OK "You will need to restart Mozilla for the changes to take effect."
  BringToFront
      
  didntfindit:
  no_mozilla:

  RegDLL "$INSTDIR\BitTorrentIE.2.dll"
  ExecWait '$SYSDIR\rundll32.exe setupapi,InstallHinfSection DefaultInstall 132 $INSTDIR\plugin.inf'
  
  BringToFront

  endofinstall:

  # chdir
  SetOutPath $INSTDIR
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
