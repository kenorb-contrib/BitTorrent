#import "BTAppController.h"
#import "DLWindowController.h"

static PyThreadState *tstate;

PyObject *bt_getProxy(NSPort *receivePort, NSPort *sendPort);

@implementation BTAppController

- (void)applicationDidFinishLaunching:(NSNotification *)note
{
    PyRun_SimpleString("from threading import Event;from BitTorrent.download import download");
    tstate = PyEval_SaveThread();

}

- (PyThreadState *)tstate
{
    return tstate;
}

- (void)setTstate:(PyThreadState *)nstate
{
    tstate = nstate;
}


- (IBAction)cancelUrl:(id)sender
{
    [urlWindow orderOut:self];
}

- (IBAction)openURL:(id)sender
{
    [urlWindow makeKeyAndOrderFront:self];
}

- (IBAction)openTrackerResponse:(id)sender;
{
    NSOpenPanel *panel = [NSOpenPanel openPanel];
    id controller;
    if([panel runModalForTypes:nil]) {
	controller = [[DLWindowController alloc] init];
	[NSBundle loadNibNamed:@"DLWindow" owner:controller];
	[self runWithStr:[NSString stringWithFormat:@"--responsefile=%@", [panel filename]] controller:controller];
    }
    
}
- (IBAction)takeUrl:(id)sender
{
    id controller = [[DLWindowController alloc] init];
    
    [urlWindow orderOut:self];
    [NSBundle loadNibNamed:@"DLWindow" owner:controller];
    
    [self runWithStr:[NSString stringWithFormat:@"--url=%@", [url stringValue]] controller:controller];

}

- (void)runWithStr:(NSString *)urlstr controller:(id)controller
{
    NSPort *left, *right;
    NSConnection *conn;
    NSMutableDictionary *dict = [NSMutableDictionary dictionaryWithCapacity:4];
    PyObject *flag;
    PyObject *mm, *md, *event;    
    left = [NSPort port];
    right = [NSPort port];
    
    // create UI side of the connection
    conn = [[NSConnection alloc] initWithReceivePort:left sendPort:right];
    // set the new DLWindowController to be the root
    [conn setRootObject:controller];
    [controller setConnection:conn];

    PyEval_RestoreThread(tstate);
    
    // get __main__
    mm = PyImport_ImportModule("__main__");
    md = PyModule_GetDict(mm);
    
    // create flag
    event = PyDict_GetItemString(md, "Event");
    flag = PyObject_CallObject(event, NULL);
    Py_INCREF(flag);
    [controller setFlag:flag]; // controller keeps this reference to flag
    
    [dict setObject:right forKey:@"receive"];
    [dict setObject:left forKey:@"send"];
    [dict setObject:[NSData dataWithBytes:&flag length:sizeof(PyObject *)] forKey:@"flag"];
    [dict setObject:urlstr forKey:@"str"];
    Py_DECREF(mm);
    tstate = PyEval_SaveThread();
    
    // fire off new thread
    [NSThread detachNewThreadSelector:@selector(runWithDict:) toTarget:[self class]  
	withObject:dict];
}

+ (void)runWithDict:(NSDictionary *)dict
{
    NSAutoreleasePool *pool;
    PyObject *proxy;
    NSString *str;
    PyObject *chooseFile, *finished, *display, *mm, *md, *dl, *flag;
    PyThreadState *ts;
    
    pool = [[NSAutoreleasePool alloc] init];
    
    ts = PyThreadState_New(tstate->interp);
    PyEval_RestoreThread(ts);    

    // get the download function
    mm = PyImport_ImportModule("__main__");
    md = PyModule_GetDict(mm);
    dl = PyDict_GetItemString(md, "download");
    
    // create proxy, which creates our side of connection
    proxy = (PyObject *)bt_getProxy([dict objectForKey:@"receive"], [dict objectForKey:@"send"]);
    
    // get args
    str = [dict objectForKey:@"str"];
    chooseFile = PyObject_GetAttrString(proxy, "chooseFile");
    display = PyObject_GetAttrString(proxy, "display");
    finished = PyObject_GetAttrString(proxy, "finished");
    [[dict objectForKey:@"flag"] getBytes:&flag];

    // do the download!
    PyObject_CallFunction(dl, "[s]OOOOi", [str cString], chooseFile, display, finished, flag, 80);
 
    // clean up
    Py_DECREF(mm);
    Py_DECREF(flag);
    Py_DECREF(proxy);
    [pool release];
    ts = PyEval_SaveThread();
}


- (BOOL)application:(NSApplication *)theApplication openFile:(NSString *)filename
{
    id controller = [[DLWindowController alloc] init];
    
    [NSBundle loadNibNamed:@"DLWindow" owner:controller];
    
    [self runWithStr:[NSString stringWithFormat:@"--responsefile=%@", filename] controller:controller];
    return TRUE;
}

- (NSNotificationCenter *)notificationCenter
{
    return [NSNotificationCenter defaultCenter];
}

@end
