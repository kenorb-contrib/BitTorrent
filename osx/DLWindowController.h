/* DLWindowController */

#import <Cocoa/Cocoa.h>
#import <python2.2/Python.h>
#import "BTCallbacks.h"

@interface DLWindowController : NSWindowController <BTCallbacks>
{
    IBOutlet id dlRate;
    IBOutlet id lastError;
    IBOutlet id file;
    IBOutlet id percentCompleted;
    IBOutlet id progressBar;
    IBOutlet id timeRemaining;
    IBOutlet id ulRate;
    NSString *timeEst;
    NSString *savepath;
    float frac;
    PyObject *flag, *chooseflag;
    double totalsize;
    NSConnection *conn;
    int done;
}
- (IBAction)cancelDl:(id)sender;
- (id)init;
- (void)finished;
- (void)error:(NSString *)str;
- (void)display:(NSDictionary *)dict;
- (void)pathUpdated:(NSString *)newPath;
- (void)chooseFile:(NSString *)defaultFile size:(double)size isDirectory:(int)dir;
- (NSString *)savePath;
- (void)dlExited;
- (void)setFlag:(PyObject *)nflag;
- (void)setChooseFlag:(PyObject *)nflag;
- (void)setConnection:(NSConnection *)nc;
- (void)dealloc;

- (void)savePanelDidEnd:(NSSavePanel *)sheet returnCode:(int)returnCode contextInfo:(void  *)contextInfo;
- (void)openPanelDidEnd:(NSOpenPanel *)sheet returnCode:(int)returnCode contextInfo:(void  *)contextInfo;

- (id)validRequestorForSendType:(NSString *)sendType returnType:(NSString *)returnType;
@end
