#import "BTAppController.h"
#import "DLWindowController.h"
#import <python2.2/Python.h>

static PyThreadState *tstate;

@implementation BTAppController

- (void)awakeFromNib
{
    dlid = 0;
    PyRun_SimpleString("import cocoa");
    PyRun_SimpleString("dlmgr = cocoa.DLManager()");
    tstate = PyEval_SaveThread();
}

- (IBAction)cancelUrl:(id)sender
{
}

- (IBAction)openURL:(id)sender
{
    [urlWindow makeKeyAndOrderFront:self];
}

- (IBAction)takeUrl:(id)sender
{
    id controller = [[DLWindowController alloc] initWithDlId:dlid];
    
    [urlWindow orderOut:self];
    [NSBundle loadNibNamed:@"DLWindow" owner:controller];
    
    [self runWithUrl:[url stringValue]];
    dlid++;

}

- (void)runWithUrl:(NSString *)urlstr
{
    NSString *str;
    str = [NSString localizedStringWithFormat:@"dlmgr.newDlWithUrl(%d, '%@')", dlid, urlstr];
    PyEval_RestoreThread(tstate);
    PyRun_SimpleString([str cString]);
    tstate = PyEval_SaveThread();
}

- (void)runWithFile:(NSString *)filename
{
    NSString *str;
    str = [NSString localizedStringWithFormat:@"dlmgr.newDlWithFile(%d, '%@')", dlid, filename];
    PyEval_RestoreThread(tstate);
    PyRun_SimpleString([str cString]);
    tstate = PyEval_SaveThread();
}

- (void)cancelDlWithId:(NSNumber *)nid
{
    PyEval_RestoreThread(tstate);
    PyRun_SimpleString([[NSString stringWithFormat:@"dlmgr.cancelDlWithId(%@)", nid] cString]);
    tstate = PyEval_SaveThread();
}

- (BOOL)application:(NSApplication *)theApplication openFile:(NSString *)filename
{
    id controller = [[DLWindowController alloc] initWithDlId:dlid];
    
    [NSBundle loadNibNamed:@"DLWindow" owner:controller];
    
    [self runWithFile:filename];
    dlid++;
    return TRUE;
}
@end
