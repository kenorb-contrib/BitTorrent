#import "BTAppController.h"
#import "DLWindowController.h"

static PyThreadState *tstate;

PyObject *getCookie(NSPort *receivePort, NSPort *sendPort);

@implementation BTAppController

- (void)applicationDidFinishLaunching:(NSNotification *)note
{
    PyRun_SimpleString("import cocoa;from threading import Event");
    tstate = PyEval_SaveThread();

}

- (void)setCancelFlag:(PyObject *)flag
{
    PyEval_RestoreThread(tstate);
    PyObject_CallMethod(flag, "set", NULL);
    tstate = PyEval_SaveThread();
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
	[self runWithFile:[panel filename] controller:controller];
    }
    
}
- (IBAction)takeUrl:(id)sender
{
    id controller = [[DLWindowController alloc] init];
    
    [urlWindow orderOut:self];
    [NSBundle loadNibNamed:@"DLWindow" owner:controller];
    
    [self runWithUrl:[url stringValue] controller:controller];

}

- (void)runWithUrl:(NSString *)urlstr controller:(id)controller
{
    NSString *str;
    PyObject *mm, *md, *dict;
    PyObject *cookie, *flag, *event;
    NSPort *left, *right;
    NSConnection *conn;
    
    str = [NSString localizedStringWithFormat:@"cocoa.newDlWithUrl('%@', cookie, flag)", urlstr];
    left = [NSPort port];
    right = [NSPort port];
    conn = [[NSConnection alloc] initWithReceivePort:left sendPort:right];
    [conn setRootObject:controller];
    [controller setConnection:conn];

    PyEval_RestoreThread(tstate);
    mm = PyImport_ImportModule("__main__");
    md = PyModule_GetDict(mm);
    event = PyDict_GetItemString(md, "Event");
    flag = PyObject_CallObject(event, NULL);
    PyMapping_SetItemString(md, "flag", flag);
    [controller setFlag:flag];
    cookie = getCookie(right, left);
    PyMapping_SetItemString(md, "cookie", cookie);
    PyRun_SimpleString([str cString]);
    Py_DECREF(mm);
    Py_DECREF(cookie);
    tstate = PyEval_SaveThread();
}

- (void)runWithFile:(NSString *)filename controller:(id)controller
{
    NSString *str;
    PyObject *mm;
    PyObject *cookie;
    PyObject *flag;
    NSPort *left, *right;
    NSConnection *conn;
    
    str = [NSString localizedStringWithFormat:@"cocoa.newDlWithFile('%@', cookie, flag)", filename];

    left = [NSPort port];
    right = [NSPort port];
    conn = [[NSConnection alloc] initWithReceivePort:left sendPort:right];
    [conn setRootObject:controller];
    [controller setConnection:conn];

    PyEval_RestoreThread(tstate);
    PyRun_SimpleString("flag = Event()");
    mm = PyModule_GetDict(PyImport_ImportModule("__main__"));
    flag = PyDict_GetItemString(mm, "flag");
    [controller setFlag:flag];
    cookie = getCookie(right, left);
    PyMapping_SetItemString(mm, "cookie", cookie);
    PyRun_SimpleString([str cString]);
    Py_DECREF(mm);
    Py_DECREF(cookie);
    tstate = PyEval_SaveThread();
}
- (BOOL)application:(NSApplication *)theApplication openFile:(NSString *)filename
{
    id controller = [[DLWindowController alloc] init];
    
    [NSBundle loadNibNamed:@"DLWindow" owner:controller];
    
    [self runWithFile:filename controller:controller];
    return TRUE;
}

- (NSNotificationCenter *)notificationCenter
{
    return [NSNotificationCenter defaultCenter];
}

@end
