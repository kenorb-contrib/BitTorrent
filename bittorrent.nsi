# Written by Bram Cohen
# see LICENSE.txt for license information

Outfile bittorrent.exe
Name BitTorrent
SilentInstall silent
SetCompressor bzip2
InstallDir "$PROGRAMFILES\BitTorrent\"
Section "Install"
  WriteUninstaller "$INSTDIR\uninstall.exe"
  SetOutPath $INSTDIR
  File btdownloadgui.exe
  File *.pyd
  File *.dll
  WriteRegStr HKCR .torrent "" bittorrent
  WriteRegStr HKCR .torrent "Content Type" application/x-bittorrent
  WriteRegStr HKCR "MIME\Database\Content Type\application/x-bittorrent" Extension .torrent
  WriteRegStr HKCR bittorrent "" "TORRENT File"
  WriteRegBin HKCR bittorrent EditFlags 00000100
  WriteRegStr HKCR "bittorrent\shell" "" open
  WriteRegStr HKCR "bittorrent\shell\open\command" "" `"$INSTDIR\btdownloadgui.exe" --responsefile "%1"`
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\BitTorrent" "DisplayName" "BitTorrent 3.2.1"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\BitTorrent" "UninstallString" '"$INSTDIR\uninstall.exe"'
  NSISdl::download /TIMEOUT=30000 "http://bitconjurer.org/BitTorrent/donate.html" "$TEMP\donate.html"
  ExecShell open "$TEMP\donate.html"
  Sleep 600
  BringToFront
  MessageBox MB_OK "BitTorrent has been successfully installed!"
SectionEnd

Section "Uninstall"
  DeleteRegKey HKCR .torrent
  DeleteRegKey HKCR "MIME\Database\Content Type\application/x-bittorrent"
  DeleteRegKey HKCR bittorrent
  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\BitTorrent"
  RMDir /r "$INSTDIR"
SectionEnd
