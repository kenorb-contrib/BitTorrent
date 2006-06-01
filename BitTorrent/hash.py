# use the new fast hash functions if available

try:
    import hashlib
    sha = hashlib.sha1
except ImportError:
    import sha as shalib
    sha = shalib.sha
