#import "DLWindowController.h"
#import "Tstate.h"

@implementation DLWindowController

#define LASTDIR @"LastSaveDir"

- (id)init
{ 
    NSUserDefaults *defaults; 
    NSMutableDictionary *appDefaults;
    
    [super init];
    timeEst = [@"" retain];
    conn = nil;
    done = 0;
    
    defaults = [NSUserDefaults standardUserDefaults];
    appDefaults = [NSMutableDictionary
    dictionaryWithObject:NSHomeDirectory() forKey:LASTDIR];
    [defaults registerDefaults:appDefaults];

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

- (NSString *)chooseFile:(NSString *)defaultFile size:(double)size isDirectory:(int)dir
{
    id panel;
    NSString *fname = nil;
    
    if(!dir) {
        panel = [NSSavePanel savePanel];
        [panel setTitle:NSLocalizedString(@"Save, choose an existing file to resume.", @"save instructions")];
        if([panel runModalForDirectory:[[NSUserDefaults standardUserDefaults] objectForKey:LASTDIR] file:defaultFile]) {
            fname = [panel filename];
        }
    }
    else {
        panel = [NSOpenPanel openPanel];
        [panel setCanChooseFiles:YES];
        [panel setCanChooseDirectories:YES];
        [panel setTitle:NSLocalizedString(@"Choose directory, choose existing directory to resume.", @"save directory instructions")];
        [panel setPrompt:NSLocalizedString(@"Save", @"save directory prompt")];
        if([panel runModalForDirectory:[[NSUserDefaults standardUserDefaults] objectForKey:LASTDIR] file:defaultFile]) {
            fname = [panel filename];
        }
    }
    if(fname) {
        [file setStringValue:[NSString stringWithFormat:NSLocalizedString(@"(%1.1f MB) %@ ", @"size and filename for dl window tite") , size, fname]];
        [[self window] setTitleWithRepresentedFilename:fname];
        [[NSUserDefaults standardUserDefaults] setObject:[panel directory] forKey:LASTDIR];
        totalsize = size;
        savepath = [fname retain];
        return fname;
    }
    // user cancelled
    [[self window] performClose:self];
    return nil;
}

- (void)pathUpdated:(NSString *)newPath
{
    [file setStringValue:[NSString stringWithFormat:NSLocalizedString(@"(%1.1f MB) %@ ", @"size and filename for dl window tite") , totalsize, newPath]];
    [[self window] setTitleWithRepresentedFilename:newPath];
    [savepath release];
    savepath = [newPath retain];
}

- (void)display:(NSDictionary *)dict
{
    NSString *str, *activity;
    long est;

    if(!done) {   
        activity = [dict objectForKey:@"activity"];
        frac = [[dict objectForKey:@"fractionDone"] floatValue];
        
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
        str = [NSString stringWithFormat:NSLocalizedString(@"%2.1f%%", @"percent dl completed"), frac * 100];
    
        [percentCompleted setStringValue:str];
        [progressBar setDoubleValue:frac];
        [timeRemaining setStringValue:timeEst];
    }
    [dlRate setStringValue:[NSString stringWithFormat:NSLocalizedString(@"%2.1f K/s",@"transfer rate"), [[dict objectForKey:@"downRate"] floatValue] / 1024]];
    [ulRate setStringValue:[NSString stringWithFormat:NSLocalizedString(@"%2.1f K/s", @"transfer rate"), [[dict objectForKey:@"upRate"] floatValue] / 1024]];
}

- (void)finished
{
    done = 1;
    [timeEst release];
    timeEst = [NSLocalizedString(@"Download Succeeded.", @"download completed successfully") retain];
    [progressBar setDoubleValue:100.0];
    [timeRemaining setStringValue:timeEst];
    [percentCompleted setStringValue:NSLocalizedString(@"100%", @"one hundred percent")];
}

- (void)dlExited
{
    if(!done) {
        [progressBar setDoubleValue:0.0];
        [timeRemaining setStringValue:NSLocalizedString(@"Download Failed!", @"download failed")];
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

// Services stuff...
- (id)validRequestorForSendType:(NSString *)sendType returnType:(NSString *)returnType {
    if (returnType == nil && ([sendType isEqualToString:NSFilenamesPboardType] ||[sendType isEqualToString:NSStringPboardType])) {
        return self;
    }
    return nil;
}

- (BOOL)writeSelectionToPasteboard:(NSPasteboard *)pboard types:(NSArray *)types
{

    if ([types containsObject:NSFilenamesPboardType] == NO && [types containsObject:NSStringPboardType] == NO) {
        return NO;
    }

    [pboard declareTypes:[NSArray arrayWithObjects:NSStringPboardType, nil] owner:nil];
    [pboard setPropertyList:[NSArray arrayWithObjects:savepath, nil] forType:NSFilenamesPboardType];
    [pboard setString:savepath forType:NSStringPboardType];
    return YES;
}

@end
