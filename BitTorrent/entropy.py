# Written by Bram Cohen
# this file is public domain

from StreamEncrypter import make_encrypter
from sha import sha
from sys import version, path, argv
from time import time
import os

try:
    h = open('/dev/random', 'rb')
    k = h.read(16)
    h.close()
    del h
except IOError:
    s = sha(version + str(path) + str(argv) + str(time()))
    for key, func in os.__dict__.items():
        if key[:3] == 'get' and key != 'getenv':
            s.update(' ' + `func()`)
    k = s.digest()[:16]
    del s

entropy = lambda amount, f = make_encrypter(k): f('a' * amount)
del k
