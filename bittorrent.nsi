# Written by Bram Cohen
# see LICENSE.txt for license information

Outfile bittorrent.exe
Name BitTorrent
SilentInstall silent
InstallDir "$PROGRAMFILES\BitTorrent\"
Section "Install"
  SetOutPath $INSTDIR
  File _socket.pyd
  File _sre.pyd
  File _StreamEncrypter.pyd
  File _winreg.pyd
  File btdownloadprefetched.exe
  File python21.dll
  File PyWinTypes21.dll
  File select.pyd
  File utilsc.pyd
  File win32api.pyd
  File wx23_1.dll
  File wxc.pyd
  WriteRegStr HKCR .torrent "" BitTorrent.torrent
  WriteRegStr HKCR "MIME\Database\Content Type\application/x-bittorrent" Extension .torrent
  WriteRegStr HKCR BitTorrent.torrent "" "TORRENT File"
  WriteRegBin HKCR BitTorrent.torrent EditFlags 00000100
  WriteRegStr HKCR "BitTorrent.torrent\shell" "" open
  WriteRegStr HKCR "BitTorrent.torrent\shell\open\command" "" '$INSTDIR\btdownloadprefetched.exe "%1"'
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\BitTorrent" "DisplayName" "BitTorrent 2.6"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\BitTorrent" "UninstallString" '"$INSTDIR\uninstall.exe"'
  MessageBox MB_OK "Hyperlinks in Internet Explorer which use BitTorrent will now work!"
SectionEnd

UninstallExeName "uninstall.exe"

Section "Uninstall"
  DeleteRegKey HKCR .torrent
  DeleteRegKey HKCR "MIME\Database\Content Type\application/x-bittorrent"
  DeleteRegKey HKCR BitTorrent.torrent
  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\BitTorrent"
  RMDir /r "$INSTDIR"
SectionEnd
