# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

#!/usr/bin/env python

import os
import sys

try:
    import distutils.core
    import distutils.command.build_ext
except ImportError:
    raise SystemExit, """\
You don't have the python development modules installed.  

If you have Debian you can install it by running
    apt-get install python-dev

If you have RedHat and know how to install this from an RPM please
email us so we can put instructions here.
"""

try:
    import twisted
except ImportError:
    raise SystemExit, """\
You don't have Twisted installed.

Twisted can be downloaded from 
    http://twistedmatrix.com/products/download

Anything later that version 1.0.3 should work
"""

try:
    import sqlite
except ImportError:
    raise SystemExit, """\
You don't have PySQLite installed.

PySQLite can be downloaded from 
    http://sourceforge.net/project/showfiles.php?group_id=54058&release_id=139482
"""

setup_args = {
    'name': 'khashmir',
    'author': 'Andrew Loewenstern',
    'author_email': 'burris@users.sourceforge.net',
    'licence': 'MIT',
    'package_dir': {'khashmir': '.'},
    'packages': [
        'khashmir', 
    ],
}

if hasattr(distutils.dist.DistributionMetadata, 'get_keywords'):
    setup_args['keywords'] = "internet tcp p2p"

if hasattr(distutils.dist.DistributionMetadata, 'get_platforms'):
    setup_args['platforms'] = "win32 posix"

if __name__ == '__main__':
    apply(distutils.core.setup, (), setup_args)
