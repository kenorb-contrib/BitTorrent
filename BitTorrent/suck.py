from cStringIO import StringIO

def suck(h, amount):
    n = h.read(amount)
    if len(n) == amount:
        return n
    s = StringIO()
    s.write(n)
    while s.tell() < amount:
        n = h.read(amount - s.tell())
        if n == '':
            break
        s.write(n)
    return s.getvalue()

