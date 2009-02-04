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

from BTL.platform import bttime


class Measure(object):

    def __init__(self, max_rate_period, fudge=5):
        self.max_rate_period = max_rate_period
        self.ratesince = bttime() - fudge
        self.last = self.ratesince
        self.rate = 0.0
        self.total = 0
        self.when_next_expected = bttime() + fudge

    def update_rate(self, amount):
        self.total += amount
        t = bttime()
        if t < self.when_next_expected and amount == 0:
            return self.rate
        self.rate = (self.rate * (self.last - self.ratesince) +
                     amount) / (t - self.ratesince)
        self.last = t
        self.ratesince = max(self.ratesince, t - self.max_rate_period)
        self.when_next_expected = t + min((amount / max(self.rate, 0.0001)), 5)

    def get_rate(self):
        self.update_rate(0)
        return self.rate

    def get_rate_noupdate(self):
        return self.rate

    def time_until_rate(self, newrate):
        if self.rate <= newrate:
            return 0
        t = bttime() - self.ratesince
        # as long as the newrate is lower than rate, we wait
        # longer before throttling.
        return ((self.rate * t) / newrate) - t

    def get_total(self):
        return self.total
