To build -

    Untar or unzip the distribution, like this -

    tar -xzvf BitTorrent-02-00-00.tar.gz

    Change directories to the one containing all the .py files -

    cd BitTorrent-02-01-00
    
    If you're using Windows, copy the prebuilt crypto into the 
    current directory and you're done, otherwise continue. You 
    can get the prebuilt crypto at 
    http://bitconjurer.org/BitTorrent/_StreamEncrypter.pyd

    Run setup.py and give it the command 'build'.
    
    ./setup.py build
   
    A subdirectory named 'build' will be created. In a subdirectory of 
    'build' will be a file called '_StreamEncrypter.so', move it into 
    the current directory -
   
    mv build/lib.linux-i686-2.0/_StreamEncrypter.so .

Now you probably want to try downloading, use this command -

    ./download.py http://64.81.72.218:8080/MercyMercyMercy.mp3 MercyMercyMercy.mp3

    That will download a large track by Medesky, Martin, and Wood.
   
    The general syntax of download is that it takes a url to download from, and 
    a filename to save as.

To publish content -

    Give the publisher the location of a publicist and a list of files to publish there

    There is currently a publicist running on Bram's machine -

    ./publish.py -location=http://64.81.72.218:8080/publish/ bigfile1.mpg bigfile2.mpg bigfile3.mpg

    After this, you will be able to download from http://64.81.72.218:8080/bigfile1.mpg

You can run your own publicist using publicize.py

If you have any questions, subscribe to the mailing list by sending mail to

BitTorrent-subscribe@yahoogroups.com

