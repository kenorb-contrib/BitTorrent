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

INTERVAL = 60
PERIODS = 5

class Hammerlock:
    def __init__(self, rate, call_later):
        self.rate = rate
        self.call_later = call_later
        self.curr = 0
        self.buckets = [{} for x in range(PERIODS)]
        self.call_later(INTERVAL, self._cycle)
        
    def _cycle(self):
        self.curr = (self.curr + 1) % PERIODS
        self.buckets[self.curr] = {}
        self.call_later(INTERVAL, self._cycle)

    def check(self, addr):
        x = self.buckets[self.curr].get(addr, 0) + 1
        self.buckets[self.curr][addr] = x
        x = 0
        for bucket in self.buckets:
            x += bucket.get(addr, 0) 
        if x >= self.rate:
            return False
        else:
            return True
    
