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

BitTorrent consists of three parts - tracker, which acts as a 
web server, publisher, which acts as an always-up peer, and the 
client portion which acts as a web helper app.

To run a tracker, execute the command bttrack.py Here is an 
example -

bttrack.py --port 8080 --ip 69.69.69.69 --file btstate --dfile dstate

You should substitute your own ip for 69.69.69.69. You can use 
a dns name instead of an ip number, although that results in clients 
having to do an extra dns lookup.

This command will read in previously generated files called btstate 
and dstate or generate new ones if they don't exist already. That's 
where persistent tracker information is kept.

The tracker won't give any immediate feedback because it's output 
is a weblog. You can get a list of published files by doing an http 
request in it's base directory (it will of course be an empty 
list at first)

To publish, execute the command btpublish.py Here is an example -

btpublish.py --ip 69.69.69.69 --port 5989 \
    --location http://69.69.69.69:8080/publish/ mymovie.mpeg

The ip argument is optional but autodetection doesn't work right if 
the tracker and publisher are on the same machine.

port can be any number you can bind to.

location is where you're running the tracker. The subdirectory 
has to be /publish/ including the trailing slash.

If you have any questions, try the web site or mailing list -

http://bitconjurer.org/BitTorrent/

http://groups.yahoo.com/group/BitTorrent
