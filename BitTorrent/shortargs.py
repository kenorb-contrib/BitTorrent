
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

# Written by David Harrison

shortforms = { "-p" : "--port",
               "-u" : "--use_factory_defaults",
               "-h" : "--help",
               "-?" : "--help",
               "--usage" : "--help"
             }

def convert_from_shortforms(argv):
    """
       Converts short-form arguments onto the corresponding long-form, e.g.,
       -p becomes --port.
    """
    assert type(argv)==list
    newargv = []
    for arg in argv:
      if arg in shortforms:
          newargv.append(shortforms[arg])
      else:
          newargv.append(arg)
    return newargv
