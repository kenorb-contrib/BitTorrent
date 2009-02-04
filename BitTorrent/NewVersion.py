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

# written by Matt Chisholm, destroyed by Greg Hazel

DEBUG = False

from BitTorrent import version

version_host = 'http://version.bittorrent.com/'
download_url = 'http://www.bittorrent.com/download.html'

# based on Version() class from ShellTools package by Matt Chisholm,
# used with permission
class Version(list):
    def __str__(self):
        return '.'.join(map(str, self))

    def is_beta(self):
        return self[1] % 2 == 1

    def from_str(self, text):
        return Version( [int(t) for t in text.split('.')] )

    def name(self):
        if self.is_beta():
            return 'beta'
        else:
            return 'stable'
    
    from_str = classmethod(from_str)

currentversion = Version.from_str(version)

availableversion = None

