/* BTAppController */

#import <Cocoa/Cocoa.h>

@interface BTAppController : NSObject
{
    IBOutlet NSTextField *url;
    IBOutlet NSWindow *urlWindow;
}
- (void)awakeFromNib;
- (IBAction)cancelUrl:(id)sender;
- (IBAction)openURL:(id)sender;
- (IBAction)takeUrl:(id)sender;
@end
