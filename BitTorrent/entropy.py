# Written by Bram Cohen
# this file is public domain

"""
A PRNG kernel which behaves properly - only reseeds when enough 
entropy has been collected in the pool and blocks when not enough 
entropy has been collected initially, and never again after that.

Pool size is 128 bits
"""

from StreamEncrypter import make_encrypter
from sha import sha
from threading import Event, Lock

so_far = 0
pool = sha()
generater = None
f = Event()
l = Lock()

def add(random_string, entropy_estimate):
    """
    random_string is a random string
    
    entropy_estimate is an estimate of the number of 'true' bits
    of entropy in random_string - that is, log base 2 of the 
    smallest average number of wrong guesses needed to guess the 
    entire string that someone else in the universe could 
    theoretically pull off
    """
    assert entropy_estimate >= 0
    assert entropy_estimate <= len(random_string) * 8
    global pool
    global so_far
    global generater
    try:
        l.acquire()
        pool.update(random_string)
        so_far += entropy_estimate
        if so_far >= 128:
            if generater is None:
                generater = make_encrypter(pool.digest()[:16])
                f.set()
            else:
                generater = make_encrypter(generater(
                    pool.digest()[:16]))
            pool = sha()
            so_far = 0
    finally:
        l.release()

def entropy(amount):
    """
    returns a random string of length amount
    
    blocks prior to the first seeding, never again after that
    """
    f.wait()
    return generater('a' * amount)

from sys import version, path, argv
from time import time
import os

try:
    h = open('/dev/random', 'rb')
    add(h.read(16), 128)
    h.close()
    del h
except IOError:
    s = version + str(path) + str(argv) + str(time())
    for key, func in os.__dict__.items():
        if key[:3] == 'get' and key != 'getenv':
            s += ' ' + `func()`
    add(s, 128)
    del s
