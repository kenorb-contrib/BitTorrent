#import "DLWindowController.h"
#import "BTAppController.h"
#import "messages.h"

@implementation DLWindowController

- (id)initWithDlId:(int)nid
{
    id not = [NSNotificationCenter defaultCenter];
 
    [super init];
    dlid = [[NSNumber numberWithInt:nid] retain];
    finished = 0;
    [not addObserver:self selector:@selector(chooseFile:) name:CHOOSE object:nil];
    [not addObserver:self selector:@selector(display:) name:DISPLAY object:nil];
    [not addObserver:self selector:@selector(finished:) name:FINISHED object:nil];
    timeEst = [@"" retain];
    return self;
}

- (void)windowWillClose:(NSNotification *)aNotification
{
    [self cancelDl:self];
}

- (IBAction)cancelDl:(id)sender
{
    id not = [NSNotificationCenter defaultCenter];
    if(!finished) {
	[timeRemaining setStringValue:@"Download cancelled!"];
    }
    [cancelButton setEnabled:NO];
    [[NSApp delegate] cancelDlWithId:dlid];
    [not removeObserver:self];
}
- (void)chooseFile:(NSNotification *)notification
{
}

- (NSString *)hours:(long) n
{
    long h, r, m, sec;
    
    if (n == -1)
	return @"<unknown>";
    if (n == 0)
	return @"Complete!";
    h = n / (60 * 60);
    r = n % (60 * 60);
    
    m = r / 60;
    sec = r % 60;
    
    if (h > 1000000)
	return @"<unknown>";
    if (h > 0)
	return [NSString stringWithFormat:@"%d hour(s) %2d min(s) %2d sec(s)", h, m, sec];
    else
	return [NSString stringWithFormat:@"%2d min(s) %2d sec(s)", m, sec]; 
}

- (void)display:(NSNotification *)notification
{
    NSDictionary *dict = [notification userInfo];
    NSString *str, *activity;
    long est;
    
    if(![[dict objectForKey:@"dlid"] isEqualToNumber:dlid])
	return;
    
    activity = [dict objectForKey:@"activity"];
    if ([[dict objectForKey:@"fractionDone"] floatValue] != 0.0) {
	frac = [[dict objectForKey:@"fractionDone"] floatValue];
    }

    // format dict timeEst here and put in ivar timeEst
    est = [[dict objectForKey:@"timeEst"] longValue];
    if(est > 0) {
	[timeEst release];
	timeEst = [[self hours:est] retain];
    }
    if(![activity isEqualToString:@""]) {
	[timeEst release];
	timeEst = [activity retain];
    }
    str = [NSString localizedStringWithFormat:@"%2.1f%%", frac * 100];

    [percentCompleted setStringValue:str];
    [dlRate setStringValue:[NSString localizedStringWithFormat:@"%2.1f K/s", [[dict objectForKey:@"downRate"] floatValue] / 1024]];
    [ulRate setStringValue:[NSString localizedStringWithFormat:@"%2.1f K/s", [[dict objectForKey:@"upRate"] floatValue] / 1024]];
    [progressBar setDoubleValue:frac];
    [timeRemaining setStringValue:timeEst];
}

- (void)finished:(NSNotification *)notification
{
    NSDictionary *dict = [notification userInfo];
    NSNumber *fin;
    NSString *errmsg;
    
    if(![[dict objectForKey:@"dlid"] isEqualToNumber:dlid])
    return;

    finished = 1;
    [cancelButton setEnabled:NO];
    fin = [dict objectForKey:@"fin"];
    errmsg = [dict objectForKey:@"errmsg"];
    
    [timeEst release];
    if([fin intValue]) {
	frac = 1.0;
	timeEst = [@"Download Succeeded." retain];
    }
    else {
	if([errmsg isEqualToString:@""])
	    timeEst = [@"Download Failed!" retain];
	else
	    timeEst = [[NSString stringWithFormat:@"Download failed - %@", errmsg] retain];
    }
    [timeRemaining setStringValue:timeEst];
    [percentCompleted setStringValue:[NSString localizedStringWithFormat:@"%2.1f%%", frac * 100]];
}

@end
