# Written by Bram Cohen
# see LICENSE.txt for license information

from time import time
true = 1
false = 0

class Measure:
    def __init__(self, max_rate_period, max_pause, fudge = 1):
        self.max_rate_period = max_rate_period
        self.max_pause = max_pause
        self.ratesince = time() - fudge
        self.last = self.ratesince
        self.rate = 0.0
        self.total = 0l

    def update_rate(self, amount):
        self.total += amount
        t = time()
        self.rate = (self.rate * (self.last - self.ratesince) + 
            amount) / (t - self.ratesince)
        self.last = t
        if self.ratesince < t - self.max_rate_period:
            self.ratesince = t - self.max_rate_period

    def get_rate(self):
        if time() - self.last > self.max_pause:
            self.update_rate(0)
        return self.rate

    def get_total(self):
        return self.total
