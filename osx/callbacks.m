//
//  callbacks.m
//  BitTorrent
//
//  Created by Dr. Burris T. Ewell on Tue Apr 30 2002.
//  Copyright (c) 2001 __MyCompanyName__. All rights reserved.
//

#import <Cocoa/Cocoa.h>

#import <python2.2/Python.h>
#import "DLWindowController.h"

#import "messages.h"


//  python type, this one to hold the ports for connecting the worker thread to it's DL window manager
staticforward PyTypeObject bt_CookieType;

typedef struct {
    PyObject_HEAD
    NSPort *receivePort;
    NSPort *sendPort;
} bt_CookieObject;

static void bt_cookie_dealloc(bt_CookieObject *this)
{
    [this->receivePort release];
    [this->sendPort release];
    PyObject_Del(this);
}

static PyTypeObject bt_CookieType = {
    PyObject_HEAD_INIT(NULL)
    0,
    "BT Cookie",
    sizeof(bt_CookieObject),
    0,
    (destructor) bt_cookie_dealloc, /*tp_dealloc*/
    0,          /*tp_print*/
    0,          /*tp_getattr*/
    0,          /*tp_setattr*/
    0,          /*tp_compare*/
    0,          /*tp_repr*/
    0,          /*tp_as_number*/
    0,          /*tp_as_sequence*/
    0,          /*tp_as_mapping*/
    0,          /*tp_hash */
};


typedef struct {
    PyObject_HEAD
    id dlController;
} bt_ProxyObject;


static PyObject *chooseFile(bt_ProxyObject *self, PyObject *args)
{
    NSAutoreleasePool *pool =[[NSAutoreleasePool alloc] init];
    char *def = "";
    long size;
    char *saveas = NULL;
    int dir;
    PyObject *res;
    NSString *str;
    if (!PyArg_ParseTuple(args, "slsi", &def, &size, &saveas, &dir))
	return NULL;
    
    Py_BEGIN_ALLOW_THREADS
    str = [self->dlController chooseFile:[NSString stringWithCString:def] size:size isDirectory:dir];
    res = PyString_FromString([str cString]);
    Py_END_ALLOW_THREADS
    [pool release];
    return res;
}

static PyObject *display(bt_ProxyObject *self, PyObject *args, PyObject *keywds)
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


    Py_BEGIN_ALLOW_THREADS
    [self->dlController display:dict];
    Py_END_ALLOW_THREADS
    [pool release];
    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject *finished(bt_ProxyObject *self, PyObject *args)
{
    int fin;
    char *errmsg = NULL;
    NSAutoreleasePool *pool =[[NSAutoreleasePool alloc] init];
    NSMutableDictionary *dict = [NSMutableDictionary dictionaryWithCapacity:2];

    if(!PyArg_ParseTuple(args, "iz", &fin, &errmsg))
	return NULL;
    if(errmsg)
	[dict setObject:[NSString stringWithCString:errmsg] forKey:@"errmsg"];
    else
	[dict setObject:@"" forKey:@"errmsg"];
    [dict setObject:[NSNumber numberWithInt:fin] forKey:@"fin"];

    Py_BEGIN_ALLOW_THREADS
    [self->dlController finished:dict];
    Py_END_ALLOW_THREADS
    [pool release];
    Py_INCREF(Py_None);
    return Py_None;
}


// first up is a PythonType to hold the proxy to the DL window

staticforward PyTypeObject bt_ProxyType;

static void bt_proxy_dealloc(bt_ProxyObject* self)
{
    [self->dlController release];
    PyObject_Del(self);
}

static struct PyMethodDef reg_methods[] = {
	{"display",	(PyCFunction)display, METH_VARARGS|METH_KEYWORDS},
	{"chooseFile",	(PyCFunction)chooseFile, METH_VARARGS},
	{"finished",	(PyCFunction)finished, METH_VARARGS},
	{NULL,		NULL}		/* sentinel */
};

PyObject *proxy_getattr(PyObject *prox, char *name)
{
	return Py_FindMethod(reg_methods, prox, name);
}

static PyTypeObject bt_ProxyType = {
    PyObject_HEAD_INIT(NULL)
    0,
    "BT Proxy",
    sizeof(bt_ProxyObject),
    0,
    (destructor)bt_proxy_dealloc, /*tp_dealloc*/
    0,          /*tp_print*/
    proxy_getattr,          /*tp_getattr*/
    0,          /*tp_setattr*/
    0,          /*tp_compare*/
    0,          /*tp_repr*/
    0,          /*tp_as_number*/
    0,          /*tp_as_sequence*/
    0,          /*tp_as_mapping*/
    0,          /*tp_hash */
};

// connect up to the DL controller and return the proxy object
// takes a "cookie" which has the send/receive ports...
static PyObject *getProxy(PyObject *self, PyObject *args)
{
    NSAutoreleasePool *pool =[[NSAutoreleasePool alloc] init];
    bt_CookieObject *cookie = nil;
    bt_ProxyObject *proxy = nil;
    id foo;
    if (!PyArg_UnpackTuple(args, "getProxy", 1, 1, &cookie))
	return NULL;
    proxy = PyObject_New(bt_ProxyObject, &bt_ProxyType);
    Py_BEGIN_ALLOW_THREADS
    foo = (id)[[NSConnection connectionWithReceivePort:cookie->receivePort
					sendPort:cookie->sendPort]
			    rootProxy];
    Py_END_ALLOW_THREADS
    [foo retain];
    proxy->dlController = foo;
    [pool release];
    return (PyObject *)proxy;
}

static PyMethodDef CallbackMethods[] = {
     {"getProxy", getProxy, METH_VARARGS, "getProxy"},
    {NULL, NULL, 0, NULL}
};

PyObject *getCookie(NSPort *receivePort, NSPort *sendPort)
{
    bt_CookieObject *cookie;
    cookie = PyObject_New(bt_CookieObject, &bt_CookieType);
    
    cookie->receivePort = [receivePort retain];
    cookie->sendPort = [sendPort retain];
    return (PyObject *)cookie;
}

void init_callbacks()
{
    Py_InitModule("callbacks", CallbackMethods);
}
