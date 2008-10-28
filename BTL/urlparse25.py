try:
    from urlparse import ParseResult
except ImportError, e:
    from _urlparse25 import *
else:
    from urlparse import *
