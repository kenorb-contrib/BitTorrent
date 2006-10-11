from BTL.ConvertedMetainfo import ConvertedMetainfo
from BTL.bencode import bencode, bdecode


def file_from_path(path):
    return open(path, 'rb').read()

def metainfo_from_file(f):
    metainfo = ConvertedMetainfo(bdecode(f))
    return metainfo

def infohash_from_path(path):
    return metainfo_from_file(file_from_path(path)).infohash

def parse_infohash(ihash):
    try:
        x = ihash.decode('hex')
    except ValueError:
        return None
    except TypeError:
        return None
    return x

def is_valid_infohash(x):
    if not len(x) == 40:
        return False
    return (parse_infohash(x) != None)

def infohash_from_infohash_or_path(x):
    if not len(x) == 40:
        return infohash_from_path(x)
    n = parse_infohash(x)
    if n:
        return n
    ## path happens to be 40 chars, or bad infohash
    return infohash_from_path(x)


if __name__ == "__main__":
    # Test is_valid_infohash()
   assert is_valid_infohash("") == False
   assert is_valid_infohash("12345") == False
   assert is_valid_infohash("12345678901234567890123456789012345678901") == False
   assert is_valid_infohash("abcdefghijklmnopqrstuvwxyzabcdefghijklmn") == False
   assert is_valid_infohash("1234567890123456789012345678901234567890") == True
   assert is_valid_infohash("deadbeefdeadbeefdeadbeefdeadbeefdeadbeef") == True 
    
