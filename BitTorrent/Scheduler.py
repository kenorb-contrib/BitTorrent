# Written by Bram Cohen
# this file is public domain

from time import time, sleep
from threading import Thread, Condition
from bisect import insort
from traceback import print_exc
true = 1
false = 0

class Scheduler:
    def __init__(self, lock, noisy = true):
        self.lock = lock
        self.noisy = noisy
        self.funcs = []
        self.running = true
        Thread(target = self.execute_forever).start()

    def shutdown(self):
        try:
            self.lock.acquire()
            self.running = false
            self.lock.notify()
        finally:
            self.lock.release()

    def add_task(self, func, delay, args = []):
        try:
            self.lock.acquire()
            insort(self.funcs, (time() + delay, func, args))
            self.lock.notify()
        finally:
            self.lock.release()

    def execute_forever(self):
        try:
            self.lock.acquire()
            try:
                while self.running:
                    if len(self.funcs) == 0:
                        self.lock.wait()
                    else:
                        self.lock.wait(self.funcs[0][0] - time())
                    while len(self.funcs) > 0 and self.funcs[0][0] <= time():
                        garbage, func, args = self.funcs[0]
                        del self.funcs[0]
                        try:
                            func(*args)
                        except KeyboardInterrupt:
                            raise
                        except:
                            if self.noisy:
                                print_exc()
            except KeyboardInterrupt:
                pass
        finally:
            self.lock.release()

def test_normal():
    l = []
    lock = Condition()
    s = Scheduler(lock)
    s.add_task(lambda l = l: l.append('b'), 2)
    s.add_task(lambda l = l: l.append('a'), 1)
    s.add_task(lambda l = l: l.append('d'), 4)
    sleep(1.5)
    s.add_task(lambda l = l: l.append('c'), 1.5)
    sleep(3)
    assert l == ['a', 'b', 'c', 'd']

def test_args():
    l = []
    def func(a, l = l):
        l.append(a)
    lock = Condition()
    s = Scheduler(lock)
    s.add_task(lambda a, l = l: l.append(a), 1, [3])
    sleep(1.5)
    assert l == [3]

def test_catch_exception():
    l = []
    lock = Condition()
    s = Scheduler(lock, false)
    s.add_task(lambda l = l: l.append('b'), 2)
    s.add_task(lambda: 4/0, 1)
    sleep(3)
    assert l == ['b']
