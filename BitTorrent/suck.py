from cStringIO import StringIO

def suck(h, amount):
    s = StringIO()
    while s.tell() < amount:
        n = h.read(amount - s.tell())
        if n == '':
            break
        s.write(n)
    return s.getvalue()

