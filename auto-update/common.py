import sys
import os.path

sig_ext = '.sign'

key_ext = '.key'
pub_key = 'public'
pri_key = 'private'
key_path = os.path.split(os.path.split(os.path.realpath(sys.argv[0]))[0])[0]

pub_key_path = os.path.join(key_path, pub_key + key_ext)
pri_key_path = os.path.join(key_path, pri_key + key_ext)

