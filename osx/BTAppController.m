#import "BTAppController.h"
#import "DLWindowController.h"
#import <python2.2/Python.h>

static PyThreadState *tstate;

@implementation BTAppController

- (void)awakeFromNib
{
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
    id controller = [[DLWindowController alloc] init];
    NSString *str, *urlstr;
    
    [urlWindow orderOut:self];
    [NSBundle loadNibNamed:@"DLWindow" owner:controller];
    
    PyEval_RestoreThread(tstate);
    PyRun_SimpleString("from callbacks import *");
    PyRun_SimpleString("from BitTorrent.download import download");
    PyRun_SimpleString("from threading import Event");
    PyRun_SimpleString("from thread import start_new_thread");
    urlstr = [url stringValue];
    str = [NSString localizedStringWithFormat:@"start_new_thread(download, (['--url=%@'], chooseFile, display, finished, Event(), 80))", urlstr];
    PyRun_SimpleString([str cString]);
    tstate = PyEval_SaveThread();

}

@end
