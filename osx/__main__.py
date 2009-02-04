from PyObjCTools import AppHelper
from Foundation import NSProcessInfo, NSBundle

## bittorrent uses argv[0]
import sys
sys.argv = [NSBundle.mainBundle().bundlePath()]

# import classes required to start application
import BTAppController, LogController, ToolbarDelegate

# start the event loop
AppHelper.runEventLoop(argv=[])
