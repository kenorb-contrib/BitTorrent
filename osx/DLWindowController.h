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
    IBOutlet id cancelButton;
    NSString *timeEst;
    float frac;
    NSNumber *dlid;
    int finished;
}
- (IBAction)cancelDl:(id)sender;
- (id)initWithDlId:(int)nid;
@end
