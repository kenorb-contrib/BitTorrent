
def str_exc(e):
    try:
        # python 2.5 does this right!
        s = unicode(e)
    except:
        try:
            s = unicode(e.args[0])
        except:
            s = str(e)
    if len(s) == 0:
        try:
            s = '%s : ' % e.__class__
        except Exception, f:
            s = repr(e)
    return s    


