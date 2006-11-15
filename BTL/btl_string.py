
# author: David Harrison

def split( s, c, quote='"', keep_quote = True):
    """analogous to str.split() except it supports quoted strings.
       A quoted string is not split even if it contains character c.
       Iff keep_quote is true then quote characters are left
       in the strings in the returned list.""" 
    l = []
    sub = []
    quoted = False
    for i in s:
        if i == quote:
            quoted = not quoted
            if keep_quote:
                sub.append(i)
        elif i != c:
            sub.append(i)
        elif quoted:
            sub.append(i) 
        else:
            l.append("".join(sub))
            sub = []
    if sub:
        l.append("".join(sub))
    return l


def remove(s,c):
  l = [i for i in s if i != c]
  return "".join(l)

# make a string printable.  Converts all non-printable ascii characters and all
# non-space whitespace to periods.  This keeps a string to a fixed width when
# printing it.  This is not meant for canonicalization.  It is far more
# restrictive since it removes many things that might be representable.
# It is appropriate for generating debug output binary strings that might
# contain ascii substrings, like peer-id's.  It explicitly excludes quotes
# and double quotes so that the string can be enclosed in quotes.
def printable(s):
    """If hex then non-printable characters are replaced wi..."""
    l = []
    for c in s:
        if ord(c) >= 0x20 and ord(c) < 0x7F and c != '"' and c != "'":
            l.append(c)
        else:
            l.append('.')
    return "".join(l)




