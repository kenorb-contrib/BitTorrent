//
//  callbacks.m
//  BitTorrent
//
//  Created by Dr. Burris T. Ewell on Tue Apr 30 2002.
//  Copyright (c) 2001 __MyCompanyName__. All rights reserved.
//

#import <Cocoa/Cocoa.h>

#import <python2.2/Python.h>

#import "messages.h"


static PyObject *chooseFile(PyObject *self, PyObject *args)
{
    NSAutoreleasePool *pool =[[NSAutoreleasePool alloc] init];
    NSSavePanel *panel = [NSSavePanel savePanel];
    char *def = "";
    long size;
    char *saveas = NULL;
    int dir;
    char *res;
    NSString *path;
    
    if (!PyArg_ParseTuple(args, "slsi", &def, &size, &saveas, &dir))
	return NULL;
    path = [NSString stringWithCString:saveas];
    [panel runModalForDirectory:saveas ? path : NSHomeDirectory() file:[NSString stringWithCString:def]];
    res = [[panel filename] cString];
    [pool release];
    return PyString_FromString(res);
}

static PyObject *display(PyObject *self, PyObject *args, PyObject *keywds)
{
    float fractionDone = 0.0;
    float timeEst = 0.0;
    float upRate = 0.0;
    float downRate = 0.0;
    char *activity = "";
    NSAutoreleasePool *pool =[[NSAutoreleasePool alloc] init];
    NSMutableDictionary *dict = [NSMutableDictionary dictionaryWithCapacity:5];
    
    static char *kwlist[] = {"fractionDone", "timeEst", "upRate", "downRate", "activity", NULL};

     if (!PyArg_ParseTupleAndKeywords(args, keywds, "|ffffs", kwlist, 
					&fractionDone, &timeEst, &upRate, &downRate, &activity))
        return NULL;
	
    [dict setObject:[NSNumber numberWithFloat:fractionDone] forKey:@"fractionDone"];
    [dict setObject:[NSNumber numberWithFloat:timeEst] forKey:@"timeEst"];
    [dict setObject:[NSNumber numberWithFloat:upRate] forKey:@"upRate"];
    [dict setObject:[NSNumber numberWithFloat:downRate] forKey:@"downRate"];
    [dict setObject:[NSString stringWithCString:activity] forKey:@"activity"];

    [[NSNotificationCenter defaultCenter] postNotificationName:DISPLAY
							object:nil
							userInfo:dict];
    [pool release];
    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject *finished(PyObject *self, PyObject *args)
{
    Py_INCREF(Py_None);
    return Py_None;
}

static PyMethodDef CallbackMethods[] = {
     {"chooseFile", chooseFile, METH_VARARGS, "chooseFile callback"},
     {"display", (PyCFunction)display, METH_VARARGS|METH_KEYWORDS, "display callback"},
     {"finished", finished, METH_VARARGS, "finished callback"},
    {NULL, NULL, 0, NULL}
};

void init_callbacks()
{
    Py_InitModule("callbacks", CallbackMethods);
}
