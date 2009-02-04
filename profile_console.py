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

import sys
from BTL.ebencode import ebdecode

class ConsoleStats(object):

    def __init__(self, filename):
        data = open(filename, 'rb').read()
        self.data = ebdecode(data)
        
    def console_print(self):
        self.data.reverse()
        for node in self.data:
            label = ' - '.join([ str(x) for x in node['l'] ])
            print label
            for c in node['c']:
                label = ' - '.join([ str(x) for x in c ])
                print '\t', label                

if __name__ == '__main__':
    ConsoleStats(sys.argv[1]).console_print()