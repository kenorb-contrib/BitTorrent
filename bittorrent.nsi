OutFile "BitTorrent-experimental-S-5.8.10-w32install.exe"
Name "BitTorrent S-5.8.10 (SHAD0W's Experimental)"
SetCompressor bzip2
InstallDir "$PROGRAMFILES\BitTorrent"
Icon "icon_bt.ico"
UninstallIcon "icon_done.ico"
InstallDirRegKey  HKLM "Software\Microsoft\Windows\CurrentVersion\App Paths\btdownloadgui.exe" ""
DirText "Setup will install BitTorrent S-5.8.10 (SHAD0W's Experimental) in the following folder.$\r$\n$\r$\nTo install in a different folder, click Browse and select another folder."
ShowInstDetails show
ShowUnInstDetails show

Section "MainGroup" SEC01
  SetOutPath "$INSTDIR"
  IfFileExists "$INSTDIR\_psyco.pyd" +1 +2
  delete "$INSTDIR\_psyco.pyd"
  SetOverwrite on
  File "btdownloadgui.exe"
  File "python23.dll"
  File "wxmsw24h.dll"
  File "_socket.pyd"
  File "_sre.pyd"
  File "_ssl.pyd"
  File "_winreg.pyd"
  File "select.pyd"
  File "wxc.pyd"
  File "zlib.pyd"
  File "icon_bt.ico"
  File "icon_done.ico"
  CreateDirectory "$SMPROGRAMS\BitTorrent (SHAD0W's Experimental)"
  CreateShortCut "$SMPROGRAMS\BitTorrent (SHAD0W's Experimental)\BitTorrent (SHAD0W's Experimental).lnk" "$INSTDIR\btdownloadgui.exe"
#  CreateShortCut "$DESKTOP\BitTorrent (SHAD0W's Experimental).lnk" "$INSTDIR\btdownloadgui.exe"
  CreateShortCut "$SMPROGRAMS\BitTorrent (SHAD0W's Experimental)\Uninstall.lnk" "$INSTDIR\uninst.exe"
  SetOverwrite off
  File "white.ico"
  File "black.ico"
  File "black1.ico"
  File "red.ico"
  File "yellow.ico"
  File "yellow1.ico"
  File "blue.ico"
  File "green.ico"
  File "green1.ico"
  File "alloc.gif"
SectionEnd

Section -Post
  WriteRegStr HKCR .torrent "" bittorrent
  WriteRegStr HKCR .torrent "Content Type" application/x-bittorrent
  WriteRegStr HKCR "MIME\Database\Content Type\application/x-bittorrent" Extension .torrent
  WriteRegStr HKCR bittorrent "" "TORRENT File"
  WriteRegBin HKCR bittorrent EditFlags 00000100
  WriteRegStr HKCR "bittorrent\shell" "" open
  WriteRegStr HKCR "bittorrent\shell\open\command" "" `"$INSTDIR\btdownloadgui.exe" --responsefile "%1"`

  WriteUninstaller "$INSTDIR\uninst.exe"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\App Paths\btdownloadgui.exe" "" "$INSTDIR\btdownloadgui.exe"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\BitTorrent (SHAD0W's Experimental)" "DisplayName" "BitTorrent S-5.8.10 (SHAD0W's Experimental)"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\BitTorrent (SHAD0W's Experimental)" "UninstallString" "$INSTDIR\uninst.exe"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\BitTorrent (SHAD0W's Experimental)" "DisplayIcon" "$INSTDIR\btdownloadgui.exe"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\BitTorrent (SHAD0W's Experimental)" "DisplayVersion" "S-5.8.10"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\BitTorrent (SHAD0W's Experimental)" "URLInfoAbout" "http://bt.degreez.net/"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\BitTorrent (SHAD0W's Experimental)" "Publisher" "John Hoffman"
SectionEnd


Function un.onUninstSuccess
  HideWindow
  MessageBox MB_ICONINFORMATION|MB_OK "BitTorrent S-5.8.10 (SHAD0W's Experimental) was successfully removed from your computer."
FunctionEnd

Function un.onInit
  MessageBox MB_ICONQUESTION|MB_YESNO|MB_DEFBUTTON2 "Are you sure you want to completely remove BitTorrent S-5.8.10 (SHAD0W's Experimental) and all of its components?" IDYES +2
  Abort
FunctionEnd

Section Uninstall
  Delete "$SMPROGRAMS\BitTorrent (SHAD0W's Experimental)\BitTorrent (SHAD0W's Experimental).lnk"
#  Delete "$DESKTOP\BitTorrent (SHAD0W's Experimental).lnk"
  Delete "$SMPROGRAMS\BitTorrent (SHAD0W's Experimental)\Uninstall.lnk"
  RMDir "$SMPROGRAMS\BitTorrent (SHAD0W's Experimental)"
  DeleteRegKey HKCU software\bittorrent

  push $1
  ReadRegStr $1 HKCR "bittorrent\shell\open\command" ""
  StrCmp $1 `"$INSTDIR\btdownloadgui.exe" --responsefile "%1"` 0 regnotempty
  DeleteRegKey HKCR bittorrent\shell\open
  DeleteRegKey /ifempty HKCR bittorrent\shell
  DeleteRegKey /ifempty HKCR bittorrent
  ReadRegStr $1 HKCR bittorrent\shell ""
  StrCmp $1 "" 0 regnotempty
  DeleteRegKey HKCR .torrent
  DeleteRegKey HKCR "MIME\Database\Content Type\application/x-bittorrent"
 regnotempty:
  pop $1
  RMDir /r "$INSTDIR"

  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\BitTorrent (SHAD0W's Experimental)"
  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\App Paths\btdownloadgui.exe"
  SetAutoClose true
SectionEnd

