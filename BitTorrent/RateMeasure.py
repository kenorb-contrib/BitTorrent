# Written by Bram Cohen
# see LICENSE.txt for license information

from time import time
true = 1
false = 0

class RateMeasure:
    def __init__(self, left):
        self.start = time()
        self.last = self.start
        self.rate = 0
        self.remaining = None
        self.left = left
        self.broke = false

    def data_came_in(self, amount):
        self.update(time(), amount)

    def get_time_left(self):
        t = time()
        if t - self.last > 15:
            self.update(t, 0)
        return self.remaining

    def update(self, t, amount):
        self.left -= amount
        self.rate = ((self.rate * (self.last - self.start)) + amount) / (t - self.start)
        self.last = t
        try:
            self.remaining = self.left / self.rate
            if self.start < self.last - self.remaining:
                self.start = self.last - self.remaining
        except ZeroDivisionError:
            self.remaining = None
        if self.broke and self.last - self.start < 20:
            self.start = self.last - 20
        if self.last - self.start > 20:
            self.broke = true
