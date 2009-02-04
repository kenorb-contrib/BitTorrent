import os
import sys
import glob
import tarfile

files = glob.glob(sys.argv[1])
for file in files:
    if not os.path.isdir(file):
        print "Skipping normal file:", file
        continue
    tarname = file + ".tar.gz"
    print "Writing:", tarname
    tar = tarfile.open(tarname, "w:gz")
    tar.add(file)
    
