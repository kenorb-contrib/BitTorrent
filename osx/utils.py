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

from Foundation import *

# we're using binary units because that's what the Finder uses
# of course, the Finder uses SI labels, but we want the numbers to be the same
KIBI = 2**10.0
MEBI = 2**20.0
GIBI = 2**30.0
TEBI = 2**40.0
PEBI = 2**50.0

defaults = NSUserDefaults.standardUserDefaults()

SEP = defaults.objectForKey_(NSDecimalSeparator)

#lame but easy
def subSep(n):
    return n.replace('.', SEP)

def formSize(n, r=0):
    return subSep(_formSize(n, r))

def _formSize(n, r):
    if n >= PEBI:
        s = n / PEBI
        if s >=100:
            return NSLocalizedString("%.0f PiB", "100 or more pebibytes") % s
        return NSLocalizedString("%.1f PiB", "less than 100 pebibytes") % round(s, 1)
    elif n >= TEBI:
        s = n / TEBI
        if s >=100:
            return NSLocalizedString("%.0f TiB", "100 or more tebibytes") % s
        return NSLocalizedString("%.1f TiB", "less than 100 tebibytes") % round(s, 1)
    elif n >= GIBI:
        s = n / GIBI
        if s >=100:
            return NSLocalizedString("%.0f GiB", "100 or more gibibytes") % s
        elif s >= 10:
            return NSLocalizedString("%.1f GiB", "10 to 100 gibibytes") % round(s, 1)
        return NSLocalizedString("%.2f GiB", "less than 10 gibibytes") % round(s, 2)
    elif n >= MEBI:
        s = n / MEBI
        if s >=100:
            return NSLocalizedString("%.0f MiB", "over 100 mebibytes") % s
        return NSLocalizedString("%.1f MiB", "less than 100 mebibytes") % round(s, 1)
    elif n >= 1024:
        s = n / KIBI
        if s >=10:
            return NSLocalizedString("%.0f KiB", "greater than 100 kibibytes") % round(s)
        return NSLocalizedString("%.1f KiB", "less than 100 kibibytes") % s
    return NSLocalizedString("%.1f KiB", "bytes") % (n/KIBI)
    
def formRate(n, r = 0):
    return formSize(n, r) + '/s'

def formTimeLeft(n):
    if n == -1:
        return NSLocalizedString("<unknown>", "unknown amount of time left")
    if n == 0:
        return NSLocalizedString("Complete!", "complete")
        
    h = n / (60 * 60)
    r = n % (60 * 60)
    
    m = r / 60
    sec = r % 60
    
    if h > 1000000:
        return NSLocalizedString("<unknown>", "unknown amount of time left")
    elif h >= 48:
        return NSLocalizedString("%d days", "more than two days left") % (h / 24)
    elif h > 9:
        return NSLocalizedString("%d hours", "10 hours or more time left ") % h
    elif h >= 1:
        return NSLocalizedString("%d h, %2d m", "hour or more time left ") % (h, m)
    else:
        if m > 5:
            return NSLocalizedString("%d minutes", "less than an hour") % m
        elif m >= 1:
            return NSLocalizedString("%d m, %2d s", "less than an 5 minutes left") % (m, sec)
        else:
            return NSLocalizedString("%d s", "less than a minute left") % sec
