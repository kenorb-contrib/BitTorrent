import sys
from BitTorrent import version, app_name

version_str = version
if int(version_str[2]) % 2:
    version_str = version_str + '-Beta'

f = open(sys.argv[1])
b = f.read()
f.close()
b = b.replace("%VERSION%", version_str)
b = b.replace("%APP_NAME%", app_name)

f = open(sys.argv[2], "w")
f.write(b)
f.close()

