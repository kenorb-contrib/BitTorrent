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
    NSString *str, *urlstr;
    
    [urlWindow orderOut:self];
    [NSBundle loadNibNamed:@"DLWindow" owner:controller];
    
    PyEval_RestoreThread(tstate);
    urlstr = [url stringValue];
    str = [NSString localizedStringWithFormat:@"dlmgr.newDlWithUrl(%d, '%@')", dlid, urlstr];
    PyRun_SimpleString([str cString]);
    dlid++;
    tstate = PyEval_SaveThread();
}

@end
