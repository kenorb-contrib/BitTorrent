/* BTAppController */

#import <Cocoa/Cocoa.h>
#import <Python/Python.h>

@interface BTAppController : NSObject
{
    IBOutlet NSTextField *url, *versField;
    IBOutlet NSWindow *urlWindow, *aboutWindow;
    NSMutableArray *dlControllers;
    NSString *version;
    NSPoint lastPoint;
    id generator;
}
- (IBAction)cancelUrl:(id)sender;
- (IBAction)openURL:(id)sender;
- (IBAction)openTrackerResponse:(id)sender;
- (IBAction)openAbout:(id)sender;
- (IBAction)takeUrl:(id)sender;
- (void)runWithStr:(NSString *)url controller:(id)controller;
+ (void)runWithDict:(NSDictionary *)dict;
// application delegate messages
- (BOOL)application:(NSApplication *)theApplication openFile:(NSString *)filename;
- init;
- (NSNotificationCenter *)notificationCenter;
- (PyThreadState *)tstate;
- (void)setTstate:(PyThreadState *)nstate;
- (IBAction)openGenerator:(id)sender;
@end
