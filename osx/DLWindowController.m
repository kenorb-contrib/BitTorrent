#import "DLWindowController.h"
#import "BTAppController.h"

@implementation DLWindowController

- (id)init
{ 
    [super init];
    timeEst = [@"" retain];
    conn = nil;
    done = 0;
    return self;
}

- (void)windowWillClose:(NSNotification *)aNotification
{
    [self cancelDl:self];
}

- (void)windowDidClose:(NSNotification *)aNotification
{
    [self autorelease];
}
- (IBAction)cancelDl:(id)sender
{
    PyEval_RestoreThread([[NSApp delegate] tstate]);
    PyObject_CallMethod(flag, "set", NULL);
    [[NSApp delegate] setTstate:PyEval_SaveThread()];
}

- (void)setFlag:(PyObject *)nflag
{
    flag = nflag;
    Py_INCREF(flag);
}

- (void)setConnection:(NSConnection *)nc
{
    if(conn)
    {
	[conn release];
    }
    conn = [nc retain];
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

- (NSString *)chooseFile:(NSString *)defaultFile size:(long)size isDirectory:(int)dir
{
    id panel;
    NSString *fname = nil;
    
    if(!dir) {
	panel = [NSSavePanel savePanel];
	[panel setTitle:@"Save, choose an existing file to resume."];
	if([panel runModalForDirectory:NSHomeDirectory() file:defaultFile]) {
	    fname = [panel filename];
	}
    }
    else {
	panel = [NSOpenPanel openPanel];
	[panel setCanChooseFiles:NO];
	[panel setCanChooseDirectories:YES];
	[panel setTitle:@"Choose directory, choose existing directory to resume."];
	[panel setPrompt:@"Save"];
	if([panel runModalForDirectory:NSHomeDirectory() file:defaultFile]) {
	    fname = [panel filename];
	}
    }
    if(fname) {
	[file setStringValue:[NSString stringWithFormat:@"%@ (%1.1f MB)", [fname lastPathComponent], size / 1048576.0]];
	[[self window] setTitleWithRepresentedFilename:fname];
	return fname;
    }
    // user cancelled
    [[self window] performClose:self];
    return nil;
}

- (void)display:(NSDictionary *)dict
{
    NSString *str, *activity;
    long est;
 
    if(!done) {   
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
	[progressBar setDoubleValue:frac];
	[timeRemaining setStringValue:timeEst];
    }
    [dlRate setStringValue:[NSString localizedStringWithFormat:@"%2.1f K/s", [[dict objectForKey:@"downRate"] floatValue] / 1024]];
    [ulRate setStringValue:[NSString localizedStringWithFormat:@"%2.1f K/s", [[dict objectForKey:@"upRate"] floatValue] / 1024]];
}

- (void)finished
{
    done = 1;
    [timeEst release];
    timeEst = [@"Download Succeeded." retain];
    [progressBar setDoubleValue:100.0];
    [timeRemaining setStringValue:timeEst];
    [percentCompleted setStringValue:@"100%"];
}

- (void)dlExited
{
    if(!done) {
	[progressBar setDoubleValue:0.0];
	[timeRemaining setStringValue:@"Download Failed!"];
	[dlRate setStringValue:@""];
	[ulRate setStringValue:@""];
	[percentCompleted setStringValue:@""];
    }
}

- (void)error:(NSString *)str
{
    [lastError setStringValue:str];
}
- (void)dealloc
{
    [conn release];
    conn = nil;
    [timeEst release];
    timeEst = nil;
    PyEval_RestoreThread([[NSApp delegate] tstate]);
    Py_DECREF(flag);
    [[NSApp delegate] setTstate:PyEval_SaveThread()];
    [super dealloc];
}
@end
