#import "ICHelper.h"
#import "BTAppController.h"
#import "DLWindowController.h"
#import "Generate.h"
#import "pystructs.h"

static PyThreadState *tstate;

bt_ProxyObject *bt_getProxy(NSPort *receivePort, NSPort *sendPort);

@implementation BTAppController

- init
{
    PyObject *mm, *md, *vers;    
    [super init];
    
    PyRun_SimpleString("from threading import Event;from BitTorrent.download import download");
    mm = PyImport_ImportModule("BitTorrent");
    md = PyModule_GetDict(mm);
    vers = PyDict_GetItemString(md, "version");
    version = [[NSString stringWithCString:PyString_AsString(vers)] retain];
    tstate = PyEval_SaveThread();
    [[[[ICHelper alloc] init] installICHandler:self] autorelease];
    
    lastPoint.x = 0.0;
    lastPoint.y = 0.0;
    return self;
}

- (id)loadDLWindow
{
    id controller = [[DLWindowController alloc] init];
    [NSBundle loadNibNamed:@"DLWindow" owner:controller];
    
    if(lastPoint.x == 0.0 && lastPoint.y == 0.0) {
	lastPoint.x = NSMinX([[controller window] frame]);
	lastPoint.y = NSMaxY([[controller window] frame]);
    }
    lastPoint = [[controller window] cascadeTopLeftFromPoint:lastPoint];

    [controller showWindow:self];
    return controller;
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
    if([panel runModalForTypes:[NSArray arrayWithObjects:@"torrent", nil]]) {
	controller = [self loadDLWindow];
	[self runWithStr:[NSString stringWithFormat:@"--responsefile=%@", [panel filename]] controller:controller];
    }
    
}
- (IBAction)takeUrl:(id)sender
{
    id controller;     
    [urlWindow orderOut:self];
    controller = [self loadDLWindow];
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
    
    [NSThread detachNewThreadSelector:@selector(runWithDict:) toTarget:[self class]  
	withObject:dict];
}

+ (void)runWithDict:(NSDictionary *)dict
{
    NSAutoreleasePool *pool;
    bt_ProxyObject *proxy;
    NSString *str;
    PyObject *chooseFile, *finished, *display, *nerror, *mm, *md, *dl, *flag, *ret;
    PyThreadState *ts;
    
    pool = [[NSAutoreleasePool alloc] init];
    
    ts = PyThreadState_New(tstate->interp);
    PyEval_RestoreThread(ts);    

    // get the download function
    mm = PyImport_ImportModule("__main__");
    md = PyModule_GetDict(mm);
    dl = PyDict_GetItemString(md, "download");
    
    // create proxy, which creates our side of connection
    proxy = (bt_ProxyObject *)bt_getProxy([dict objectForKey:@"receive"], [dict objectForKey:@"send"]);
    
    // get callbacks and other args
    str = [dict objectForKey:@"str"];
    chooseFile = PyObject_GetAttrString((PyObject *)proxy, "chooseFile");
    display = PyObject_GetAttrString((PyObject *)proxy, "display");
    finished = PyObject_GetAttrString((PyObject *)proxy, "finished");
    nerror = PyObject_GetAttrString((PyObject *)proxy, "nerror");
    [[dict objectForKey:@"flag"] getBytes:&flag];

    // do the download!
    ret = PyObject_CallFunction(dl, "[ss]OOOOOi", [str cString], "--display_interval=1.5", 
				chooseFile, display, finished, nerror, flag, 80);
    [proxy->dlController dlExited];
    
    // clean up
    Py_DECREF(mm);
    Py_DECREF(flag);
    Py_DECREF(proxy);
    [pool release];
    ts = PyEval_SaveThread();
}

- (IBAction)openAbout:(id)sender
{
    [versField setStringValue:version];
    [aboutWindow makeKeyAndOrderFront:self];
}

- (BOOL)application:(NSApplication *)theApplication openFile:(NSString *)filename
{
    id controller = [self loadDLWindow];
    
    [self runWithStr:[NSString stringWithFormat:@"--responsefile=%@", filename] controller:controller];
    return TRUE;
}

- (NSNotificationCenter *)notificationCenter
{
    return [NSNotificationCenter defaultCenter];
}

- (IBAction)openGenerator:(id)sender
{
    if (!generator) {
	generator = [[Generate alloc] init];
    }
    [generator open];
}


@end
