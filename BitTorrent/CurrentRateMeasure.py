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

# Written by Bram Cohen

from time import time


class Measure(object):

    def __init__(self, max_rate_period, fudge=5):
        self.max_rate_period = max_rate_period
        self.ratesince = time() - fudge
        self.last = self.ratesince
        self.rate = 0.0
        self.total = 0

    def update_rate(self, amount):
        self.total += amount
        t = time()
        self.rate = (self.rate * (self.last - self.ratesince) + 
            amount) / (t - self.ratesince)
        self.last = t
        if self.ratesince < t - self.max_rate_period:
            self.ratesince = t - self.max_rate_period

    def get_rate(self):
        self.update_rate(0)
        return self.rate

    def get_rate_noupdate(self):
        return self.rate

    def time_until_rate(self, newrate):
        if self.rate <= newrate:
            return 0
        t = time() - self.ratesince
        return ((self.rate * t) / newrate) - t

    def get_total(self):
        return self.total
