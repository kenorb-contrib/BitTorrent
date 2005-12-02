# The contents of this file are subject to the BitTorrent Open Source License
# Version 1.1 (the License).  You may not copy or use this file, in either
# source code or executable form, except in compliance with the License.  You
# may obtain a copy of the License at http://www.bittorrent.com/license/.
#
# Software distributed under the License is distributed on an AS IS basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied.  See the License
# for the specific language governing rights and limitations under the
# License.

# GetTorrent -- abstraction which can get a .torrent file from multiple
# sources: local file, url, etc.

# written by Matt Chisholm

import os
import re
import zurllib
from bencode import bdecode
from BitTorrent.platform import get_cache_dir

urlpat = re.compile('^\w+://')
urlpat_torrent = re.compile('^torrent://')
urlpat_bittorrent = re.compile('^bittorrent://')

def get_quietly(arg):
    (data, errors) = get(arg)
    # If there's an error opening a file from the IE cache,
    # act like we simply didn't get a file (because we didn't)
    if errors:
        cache = get_cache_dir()
        if (cache is not None) and (cache in arg):
            errors = []
    return data, errors

def get(arg):
    data = None
    errors = []
    if os.access(arg, os.F_OK):
        data, errors = get_file(arg)
    elif urlpat.match(arg):
        data, errors = get_url(arg)
    else:
        errors.append(_("Could not read %s") % arg)
    return data, errors


def get_url(url):
    data = None
    errors = []
    err_str = _("Could not download or open \n%s\n"
                "Try using a web browser to download the torrent file.") % url
    u = None

    # pending protocol changes, convert:
    #   torrent://http://path.to/file
    # and:
    #   bittorrent://http://path.to/file
    # to:
    #   http://path.to/file
    url = urlpat_torrent.sub('', url)
    url = urlpat_bittorrent.sub('', url)
    
    try:
        u = zurllib.urlopen(url)
        data = u.read()
        u.close()
        b = bdecode(data)
    except Exception, e:
        if u is not None:
            u.close()
        errors.append(err_str + "\n(%s)" % e)
        data = None
    else:
        if u is not None:
            u.close()

    return data, errors
    

def get_file(filename):
    data = None
    errors = []
    f = None
    try:
        f = file(filename, 'rb')
        data = f.read()
        f.close()
    except Exception, e:
        if f is not None:
            f.close()
        errors.append((_("Could not read %s") % filename) + (': %s' % str(e)))

    return data, errors
