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

BitTorrent consists of two parts - tracker, which acts as a 
web server, and the downloader, which acts as a web helper app.

To run a tracker, execute the command bttrack.py Here is an 
example -

bttrack.py --port 8080 --ip 69.69.69.69 --file btstate \
    --dfile dstate --logfile logfile

You should substitute your own ip for 69.69.69.69. You can use 
a dns name instead of an ip number, although that results in clients 
having to do an extra dns lookup.

This command will read in previously generated files called btstate 
and dstate or generate new ones if they don't exist already. That's 
where persistent tracker information is kept.

The tracker won't give any immediate feedback. You can get a list 
of published files by doing an http request in it's base directory.

To publish, first run the publish script to let the tracker know about 
a file, then run a downloader which already has the complete file to 
make it available. Here's the publish command -

btpublish.py myfile.ext http://my.tracker/somename.ext

This command will take some time to scan over the file, then report 
the information to the tracker and return. It will report whether the 
tracker's response.

Next run a downloader, here's an example -

btdownloadheadless.py --url http://my.tracker/somename.ext --saveas \
    myfile.ext

Make sure the saveas argument points to the complete file.

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
