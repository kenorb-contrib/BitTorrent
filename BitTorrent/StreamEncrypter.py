# written by Bram Cohen
# this file is public domain

from _StreamEncrypter import make_encrypter

# everything below is for testing

def checkpoints(s, l):
    cm = make_encrypter('abcd' * 4)
    buf = ''
    for i in xrange(len(l) - 1):
        buf += cm(s[l[i]:l[i+1]])
    return buf

def test():
    p = ''.join([chr((3 * i) % 256) for i in xrange(500)])
    a = checkpoints(p, [0, 3, 11, 200, 350, 400, 500])
    b = checkpoints(p, [0, 0, 21, 27, 28, 29, 301, 500])
    assert a == b

from sha import sha

def test_lots():
    x = make_encrypter('abcdabcdefghefgh')
    y = sha(x('abc' * 1000000)).digest()
    assert y == 'nPd\366 \311\2649c\033\241\325S\230\352\210\0150<\365'
    y = sha(x('abc' * 1000000)).digest()
    assert y == '\242;\200\274\212c\341\347c\316A\300\004M\307\200\307d\372B'
