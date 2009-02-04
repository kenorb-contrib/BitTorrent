Release Notes Version 4.4.1 2006/02/01
---------
Fixed kernel panics on OS X 10.3
Universal Plug and Play port forwarding is not yet supported on OS X 10.3.
Fixed the console log spew on OS X 10.4.

Release Notes Version 4.4.0 2006/02/01
---------
If you have problems with BT stalling and/or eating all of your CPU, please report to bugs@bittorrent.com

Release Notes Beta Version 4.3.6 2006/01/23
---------
Fixed the CPU problems of 4.3.5
Fixed the bug where having no global maximum upload rate then setting a per-torrent maximum would throw BT into an infinte loop
Progress bars now use the system tint

Release Notes Beta Version 4.3.5 2005/12/23
---------
Universal Plug and Play port forwarding support is the main new development for Mac users in 4.3/4.4

Release Notes Beta Version 4.1.7 2005/11/01
---------
Fixed memory leaks
Massive CPU savings by replacing Cocoa progress bars
many bug fixes

Release Notes Beta Version 4.1.2 2005/06/06
---------
many trackerless bug fixes

Release Notes Beta Version 4.1.1 2005/05/24
---------
please note that you may need to forward your UDP port as well as your
  TCP port for best results with the trackerless system

Release Notes Beta Version 4.1.0 2005/05/16
---------
FYI, odd minor versions, 4.1.0, 4.3.0, 4.5.0, etc... are beta versions, even minor versions are releases.
First release of "Trackerless" system.

Release Notes Version 4.0.2 2005/04/30
---------
Updated for Tiger
BT will now allow you to change the TCP port if it cannot bind at startup.
Fix problem where BT required location under an all ASCII pathname

Release Notes Version 4.0.1 2005/04/01
---------
Thank you to everyone who donated!  
Thanks to the many people who provided feedback and testing to make this version the best yet.
PyObjC is the best way to write software for the Mac:  http://pyobjc.sourceforge.net/
What's new:
  Latest BitTorrent engine - single port, no lengthy check when resuming torrents, global UL limiter
  Queuing - drag torrents around and they will be downloaded in order
  Revised UI
    Customizable toolbar
    Rearrangeable columns
    Colors to indicate torrent status
  Torrent File Inspector
  Controls for limiting number of peers
  Defeatable version check - uses DNS so you actually query your ISP, who caches the version number
  Less resource consumption
  Lots more!


Release Notes Version 3.4.2 2004/05/20
----------
Total rewrite in PyObjC;  thanks to Bill, Bob, Ronald, and everyone else who contributes to PyObjC! http://pyobjc.sourceforge.net/
All New UI
New Peer Detail Window - explanation of columns
  l/r - connection was initiated (L)ocally or (R)emotely - If you never see "r" in this column then you are probably behind a firewall/NAT.
  IP  - their IP address
  their interest - an "i" will appear if they are interested in any pieces we have
  ul rate - how fast we are uploading to them - grey means we are "choking" them and not currently sending them any data
  our interest - an "i" will appear in this column if we are interested in any pieces they have
  dl rate - how fast we are downloading from them - grey means they are "choking" or "snubbing" us and not sending us any data
Of course it contains the latest reference BitTorrent code


Release Notes Version 3.3a 2003/11/07
----------
Recompiled with XCode, works on Pathner


Release Notes Version 3.3 2003/10/10
----------
Latest BitTorrent:
  more hard drive friendly file allocation
  less CPU consumption
  many tweaks
Internationalization:
  Better handling of extended characters in filenames.
  Dutch translation contributed by Martijn Dekker
  Partial French translation contributed by ToShyO
Fixed Bugs:
  opened file descriptor limit
  removed illegal characters from Rendezvous advertisements, not compatible with 3.2!


Release Notes Version 3.2.2a 2003/05/31
----------
somehow a typo snuck in unnoticed

Release Notes Version 3.2.2  2003/05/30
----------
Latest BitTorrent
Fixed bug where opening multiple torrent files at once caused a deadlock
New Features:
  Preferences for minimum/maximum port and IP address
  Displays number of peers
  Displays total uploaded / downloaded
  Adjustable max upload rate and max uploads (not surprisingly, this was the most requested feature)
  Rendezvous tracking finds peers on the same side of the firewall and allows "trackerless" operation in the local domain
  Cancel button for torrent generation
    
  
Release Notes Version 3.1a
----------
Fixed a bug where torrents larger than about 2 gigabytes would fail.
These builds do not seem to work on 10.1, the cause is being investigated.  For now you need 10.2 "Jaguar"


Release Notes Version 3.1
----------
This release has the latest BitTorrent and also UI for generating torrent files.
Checking the "create a torrent file for each file/folder in this folder..." will create a torrent file only if one does not already exist.  Also, it only creates torrents for the files/foldes in the top level of the chosen folder.


Release Notes Version 3.0
----------
Initial Mac OS X release





Guide to Fast Downloads
-----------------------
The name of the game is connecting to as many peers as possible.  If you are behind a NAT or firewall, the single thing that will make the biggest difference in your download speed is to reconfigure your NAT/firewall to allow incoming connections on the ports that BT is listening to (it uses a new port for every download, starting at the minimum you specify.)  Then all the other peers behind a NAT or firewall will connect to you so that you can download from them.

BitTorrent uses "tit for tat" for deciding which peer to upload to.  In general terms, the client uploads to the peers that it is downloading from the fastest.  This is why there can be a delay after connecting to peers before downloading begins;  you have nothing to upload to other peers.  The torrent typically bursts to life once your client gets a complete piece or two.  If there is excess bandwidth available, perhaps because many peers left their window open, then you can get good download rates without uploading much.  If you are on a very fast connection and think you could be downloading faster, try increasing the maximum number of uploads;  by uploading to more peers you may end up downloading from more peers.  Give the client a few minutes to "settle" after tweaking it.  The client uses one upload "slot" to cycle through peers looking for fast downloads and only changes this slot every 30 seconds.

