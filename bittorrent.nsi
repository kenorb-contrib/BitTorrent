# Written by Bram Cohen
# see LICENSE.txt for license information

Outfile bittorrent.exe
Name BitTorrent
SilentInstall silent
InstallDir "$PROGRAMFILES\BitTorrent\"
Section "Install"
  WriteUninstaller "$INSTDIR\uninstall.exe"
  SetOutPath $INSTDIR
  File btdownloadprefetched.exe
  File *.pyd
  File *.dll
  WriteRegStr HKCR .torrent "" bittorrent
  WriteRegStr HKCR "MIME\Database\Content Type\application/x-bittorrent" Extension .torrent
  WriteRegStr HKCR bittorrent "" "TORRENT File"
  WriteRegBin HKCR bittorrent EditFlags 00000100
  WriteRegStr HKCR "bittorrent\shell" "" open
  WriteRegStr HKCR "bittorrent\shell\open\command" "" '$INSTDIR\btdownloadprefetched.exe "%1"'
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\BitTorrent" "DisplayName" "BitTorrent 2.9.4"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\BitTorrent" "UninstallString" '"$INSTDIR\uninstall.exe"'
  MessageBox MB_OK "Hyperlinks in Internet Explorer which use BitTorrent will now work!"
SectionEnd

Section "Uninstall"
  DeleteRegKey HKCR .torrent
  DeleteRegKey HKCR "MIME\Database\Content Type\application/x-bittorrent"
  DeleteRegKey HKCR BitTorrent.torrent
  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\BitTorrent"
  RMDir /r "$INSTDIR"
SectionEnd
