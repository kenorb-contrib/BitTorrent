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

def str_exc(e):
    try:
        # python 2.5 does this right!
        s = unicode(e)
    except:
        try:
            s = unicode(e.args[0])
        except:
            s = str(e)
    if ' : ' not in s:
        try:
            s = '%s : %s' % (e.__class__, s)
        except Exception, f:
            s = repr(e)
    return s    

def str_fault(e):
    if hasattr(e, 'faultString'):
        msg = e.faultString
    else:
        msg = str_exc(e)
    return msg

