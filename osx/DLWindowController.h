/* DLWindowController */

#import <Cocoa/Cocoa.h>
#import <python2.2/Python.h>
#import "BTCallbacks.h"

@interface DLWindowController : NSWindowController <BTCallbacks>
{
    IBOutlet id dlRate;
    IBOutlet id downloadTo;
    IBOutlet id file;
    IBOutlet id percentCompleted;
    IBOutlet id progressBar;
    IBOutlet id timeRemaining;
    IBOutlet id ulRate;
    IBOutlet id cancelButton;
    IBOutlet id window;
    NSString *timeEst;
    float frac;
    PyObject *flag;
    int finished;
    NSConnection *conn;
}
- (IBAction)cancelDl:(id)sender;
- (id)init;
- (void)finished:(NSDictionary *)dict;
- (void)display:(NSDictionary *)dict;
- (NSString *)chooseFile:(NSString *)defaultFile size:(long)size isDirectory:(int)dir;
- (void)setFlag:(PyObject *)nflag;
- (void)setConnection:(NSConnection *)nc;
- (void)dealloc;
@end
