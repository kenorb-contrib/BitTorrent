#import "DLWindowController.h"
#import "messages.h"

@implementation DLWindowController

- (id)init
{
    id not = [NSNotificationCenter defaultCenter];
 
    [super init];   
    [not addObserver:self selector:@selector(chooseFile:) name:CHOOSE object:nil];
    [not addObserver:self selector:@selector(display:) name:DISPLAY object:nil];
    [not addObserver:self selector:@selector(finished:) name:FINISHED object:nil];
    return self;
}

- (void)chooseFile:(NSNotification *)notification
{
}

- (void)display:(NSNotification *)notification
{
    NSDictionary *dict = [notification userInfo];
    [percentCompleted setStringValue:[NSString localizedStringWithFormat:@"%@ (%@)", [dict objectForKey:@"fractionDone"], [dict objectForKey:@"activity"]]];
    [dlRate setFloatValue:[[dict objectForKey:@"downRate"] floatValue]];
    [ulRate setFloatValue:[[dict objectForKey:@"upRate"] floatValue]];
    [progressBar setDoubleValue:[[dict objectForKey:@"fractionDone"] doubleValue]];
    [timeRemaining setFloatValue:[[dict objectForKey:@"timeEst"] floatValue]];
}

- (void)finished:(NSNotification *)notification
{
}

@end
