BitTorrent is a tool for distributing files. It's extremely 
easy to use - downloads are started by clicking on hyperlinks.
Whenever more than one person is downloading at once 
they send pieces of the file(s) to each other, thus relieving 
the central server's bandwidth burden. Even with many 
simultaneous downloads, the upload burden on the central server 
remains quite small, since each new downloader introduces new 
upload capacity.

Windows web browser support is added by running an installer. 
Instructions for making the installer are in BUILD.windows.txt

Instructions for Unix installation are in INSTALL.unix.txt

BitTorrent consists of two parts - downloaders, which acts as 
a web helper app, and trackers, which coordinate between them.
You only need to run one tracker.

To run a tracker, execute the command bttrack.py Here is an 
example -

./bttrack.py --port 8080 --dfile dstate

dfile is where the information about current downloaders is saved 
periodically. An empty one will be created if it doesn't exist 
already.

The tracker outputs web logs to standard out. You can get information 
about the files it's currently serving by getting its index page. 

To generate a metainfo file, run the publish script and give it the 
file you want metainfo for and the url of the tracker

./btpublish.py myfile.ext http://my.tracker/announce

This command may take a while to scan over the whole file hashing it.

The /announce path is special and hard-coded into the tracker. 
Make sure to give the domain or ip your tracker is on instead of 
my.tracker.

This will generate a file called myfile.ext.torrent. Now you must 
associate the .torrent exension with mimetype application/x-bittorrent
on your web server and put the .torrent file on it. You can hyperlink 
to it like any other file.

Next you have to run a downloader which already has the complete file, 
so new downloaders have a place to get it from. Here's an example -

./btdownloadheadless.py --saveas myfile.ext --responsefile \
    myfile.ext.torrent

Make sure the saveas argument points to the already complete file.

BitTorrent defaults to port 6881. If it can't use 6881, (probably because 
another download is happening) it tries 6882, then 6883, etc. It gives up 
after 6889.

BitTorrent can also publish whole directories - simply point at the 
directory with files in it, they'll be published as one unit. All files 
in subdirectories will be included, although files and directories named 
'CVS' and 'core' are ignored.

If you have any questions, try the web site or mailing list -

http://bitconjurer.org/BitTorrent/

http://groups.yahoo.com/group/BitTorrent

You can also often find me, Bram, in #bittorrent of irc.openprojects.net
