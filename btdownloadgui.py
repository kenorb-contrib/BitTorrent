#!/usr/bin/env python

# Written by Bram Cohen
# this file is public domain

from BitTorrent.download import download, downloadurl
from BitTorrent.parseargs import parseargs
from threading import Event, Thread
from Tkinter import Tk, Label, Button
from tkFileDialog import asksaveasfilename
from sys import argv, version
assert version >= '2', "Install Python 2.0 or greater"

from btdownloadheadless import configDefinitions

def run(configDictionary, files, prefetched = None):
    root = Tk()
    root.withdraw()
    root.title('BitTorrent')
    def getname(default, root = root):
        result = asksaveasfilename(initialfile = default)
        return result
    l = Label(root, text = "initializing...")
    l.pack()
    doneflag = Event()
    def shutdown(root = root, doneflag = doneflag):
        doneflag.set()
        root.destroy()
    quit_button = Button(root, text = 'Cancel', width=28, height=1, 
        command = shutdown)
    quit_button.pack(side = 'bottom')
    def displayfunc(a, b, root = root, l = l, button = quit_button):
        root.deiconify()
        l.config(text = a)
        button.config(text = b)
    Thread(target = root.mainloop).start()
    if prefetched is None:
        downloadurl(files[0], getname, displayfunc, doneflag, configDictionary)
    else:
        download(prefetched, getname, displayfunc, doneflag, configDictionary)

if __name__ == '__main__':
    config, files = parseargs(argv[1:], configDefinitions, 1, 1) 
    run(config, files)
