/* DLWindowController */

#import <Cocoa/Cocoa.h>

@interface DLWindowController : NSWindowController
{
    IBOutlet id dlRate;
    IBOutlet id downloadTo;
    IBOutlet id file;
    IBOutlet id percentCompleted;
    IBOutlet id progressBar;
    IBOutlet id timeRemaining;
    IBOutlet id ulRate;
    NSString *timeEst;
    float frac;
    NSNumber *dlid;
}
- (id)initWithDlId:(int)nid;
@end
