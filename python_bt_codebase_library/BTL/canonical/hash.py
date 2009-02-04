#!/user/bin/env python
import re

_valid_sha1_re = re.compile(r'\A[0-9a-f]{40,40}\Z')

def canon_sha1(sha1):
    sha1 = sha1.lower()
    if not _valid_sha1_re.match(sha1):
        raise ValueError("SHA-1 hash must be 40 hexadecimal digits in normalized form (lower-case ASCII only)")
    return sha1
