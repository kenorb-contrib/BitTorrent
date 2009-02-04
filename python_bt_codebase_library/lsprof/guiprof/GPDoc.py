import objc
from Foundation import *
from AppKit import *
from PyObjCTools import NibClassBuilder, AppHelper
import cPickle

NibClassBuilder.extractClasses("GPDoc")

import sys

sys.path.append('/Users/mwh/Source/lsprof')

import lsprof


WRAPPED={}
class Wrapper (NSObject):
    """
    NSOutlineView doesn't retain values, which means we cannot use normal
    python values as values in an outline view.
    """
    def init_(self, value):
        self.value = value
        return self

    def __str__(self):
        return '<Wrapper for %s>'%self.value

    def description(self):
        return str(self)

def wrap_object(obj):
    if WRAPPED.has_key(id(obj)):
        return WRAPPED[id(obj)]
    else:
        WRAPPED[id(obj)] = Wrapper.alloc().init_(obj)
        return WRAPPED[id(obj)]

def unwrap_object(obj):
    if obj is None:
        return obj
    return obj.value

# class defined in GPDoc.nib
class GPDoc(NibClassBuilder.AutoBaseClass):
    # the actual base class is NSDocument
    # The following outlets are added to the class:
    # outlineView

    def init(self):
        self = super(GPDoc, self).init()
        self.stats = lsprof.Stats([])
        return self

    def windowNibName(self):
        return "GPDoc"

    def readFromFile_ofType_(self, path, tp):
        self.stats = cPickle.load(open(path))
        return True

    def outlineView_child_ofItem_(self, ov, child, item):
        item = unwrap_object(item)
        if item is None:
            return wrap_object(self.stats.data[child])
        else:
            return wrap_object(item.calls[child])

    def outlineView_isItemExpandable_(self, ov, item):
        item = unwrap_object(item)
        return getattr(item, 'calls', None) is not None

    def outlineView_numberOfChildrenOfItem_(self, ov, item):
        item = unwrap_object(item)
        if item is None:
            return len(self.stats.data)
        else:
            return len(item.calls)

    def outlineView_objectValueForTableColumn_byItem_(self, ov, column, item):
        item = unwrap_object(item)
        return str(getattr(item, column.identifier()))

    def outlineView_didClickTableColumn_(self, ov, col):
        #print 'hello', ov, col
        self.stats.sort(col.identifier())
        self.outlineView.reloadData()


if __name__ == "__main__":
    AppHelper.runEventLoop()
