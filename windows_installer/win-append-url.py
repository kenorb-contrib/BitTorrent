import sys
import os
app_name = "BitTorrent"
from BitTorrent import version
from BitTorrent.NewVersion import Version

currentversion = Version.from_str(version)
version_str = version
if currentversion.is_beta():
    version_str = version_str + '-Beta'

max_url_len = 2048
default_url = ""
filename = "%s-%s.exe" % (app_name, version_str)

if len(sys.argv) > 1:
    default_url = sys.argv[1]

f = open(filename, 'ab')
try:
    f.write(default_url)
    f.write(' ' * (max_url_len - len(default_url)))
finally:
    f.close()
