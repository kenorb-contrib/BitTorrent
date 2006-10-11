# usage:
#
# o.method = decorate_func(somefunc, o.method)

def decorate_func(new, old):
    def runner(*a, **kw):
        new(*a, **kw)
        return old(*a, **kw)
    return runner
