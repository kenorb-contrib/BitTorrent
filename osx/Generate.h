/* Generate */

#import <Cocoa/Cocoa.h>
#import <python2.2/Python.h>

@interface Generate : NSObject
{
    IBOutlet id fileField;
    IBOutlet id gWindow;
    IBOutlet id hostField;
    IBOutlet id iconWell;
    IBOutlet id portField;
    IBOutlet id gButton;
    IBOutlet id progress;
    NSString *fname;
}
- (IBAction)generate:(id)sender;
- (void)open;
- (void)displayFile:(NSString *)f;
- (void)savePanelDidEnd:(NSWindow *)sheet returnCode:(int)returnCode contextInfo:(void  *)contextInfo;
// drag protocol
- (NSDragOperation)draggingEntered:(id <NSDraggingInfo>)sender;
- (void)draggingExited:(id <NSDraggingInfo>)sender;
- (BOOL)performDragOperation:(id <NSDraggingInfo>)sender;

@end
