to install under UNIX -

    install Python, version 2.0 or later - http://python.org/
    
    install wxPython - http://wxpython.org/

    untar or unzip and cd to the root BitTorrent directory and 
    enter the command
    
    ./setup.py install

    now in Mozilla go to edit->preferences->navigator->helper applications
    and add in a new type with the following info -
    
    MIME Type: application/x-bittorrent
    
    Application: btdownloadprefetched.py

    and web browse! You can start with this page - 
    
    http://bitconjurer.org/BitTorrent/demo.html

to build under windows -

    install Python, version 2.0 or later - http://python.org/
    
    install wxPython - http://wxpython.org/

    install the nullsoft installer - http://www.nullsoft.com/free/nsis/

    Copy the prebuilt crypto into root BitTorrent directory.
    You can get the prebuilt crypto at 
    http://bitconjurer.org/BitTorrent/_StreamEncrypter.pyd

    Run setup.py and give it the command 'py2exe'.
    
    python setup.py py2exe

    change to the newly created subdirectory dist\btdownloadprefetched 
    and run nsis on bittorrent.nsi
    
    c:\progra~1\nsis\makensis.exe ..\..\bittorrent.nsi
    
    this will create a file called bittorrent.exe. you've made 
    an installer!

To publish content -

    Give the publisher the location of a tracker and a list of files 
    to publish there

    There is currently a publicist running on Bram's machine -

    ./btpublish.py --ip=your.ip.is.required \
        --location=http://64.81.72.218:8080/publish/ \
        bigfile1.mpg bigfile2.mpg bigfile3.mpg

    After this, you'll be able to download from 
    http://64.81.72.218:8080/bigfile1.mpg

You can run your own publicist using publicize.py

    ./bttrack.py --ip=your.ip.is.required --port=8000
    
    this will appear to hang - it's working, just waiting for publications 
    and downloads

If you have any questions, subscribe to the mailing list -

http://groups.yahoo.com/group/BitTorrent
