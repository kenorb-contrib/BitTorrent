# Written by Bram Cohen
# see LICENSE.txt for license information

from binascii import b2a_hex, a2b_hex

def int_to_binary(numin, size):
    x = hex(numin)[2:]
    if x[-1] == 'L':
        x = x[:-1]
    if len(x) % 2 == 1:
        x = '0' + x
    x = a2b_hex(x)
    x = ('\000' * (size - len(x))) + x
    return x

def binary_to_int(s):
    return long(b2a_hex(s), 16)

def test():
    assert binary_to_int(chr(0)) == 0
    assert binary_to_int(chr(1)) == 1
    assert binary_to_int(chr(0) + chr(1)) == 1
    assert binary_to_int(chr(1) + chr(0)) == 256
    assert len(int_to_binary(0, 5)) == 5
    assert len(int_to_binary(1, 5)) == 5
    assert binary_to_int(int_to_binary(10 ** 8, 20)) == 10 ** 8
    assert int_to_binary(binary_to_int('abc'), 3) == 'abc'
    assert int_to_binary(binary_to_int('a' * 16), 16) == 'a' * 16

