#import "Generate.h"
#import "Tstate.h"

@protocol GCallbacks
- (void)endGenerate;
@end

@implementation Generate

#define THOSTKEY @"TrackerHost"
#define TPORTKEY @"TrackerPort"
#define GWINKEY @"GenerateFrame"

- init {
    NSUserDefaults *defaults; 
    NSMutableDictionary *appDefaults;

    [super init];
    [NSBundle loadNibNamed:@"Metainfo" owner:self];
    [gWindow registerForDraggedTypes:[NSArray arrayWithObjects:NSFilenamesPboardType, nil]];

    defaults = [NSUserDefaults standardUserDefaults];
    appDefaults = [NSMutableDictionary
        dictionaryWithObject:@"" forKey:THOSTKEY];
    [appDefaults setObject:@"" forKey:TPORTKEY];
    [appDefaults setObject:[gWindow stringWithSavedFrame] forKey:GWINKEY];
    [defaults registerDefaults:appDefaults];

    [gWindow setFrameAutosaveName:GWINKEY];
    [gWindow setFrameUsingName:GWINKEY];
    [[portField cell] setEntryType:NSPositiveIntType];
    [[[portField cell] formatter] setHasThousandSeparators:NO];
    [hostField setStringValue:[defaults objectForKey:THOSTKEY]];
    [portField setStringValue:[defaults objectForKey:TPORTKEY]];
    
    return self;
}
- (IBAction)generate:(id)sender
{
    NSSavePanel *panel =  [NSSavePanel savePanel];
    NSArray *a;
    NSRange range;
    NSUserDefaults *defaults = [NSUserDefaults standardUserDefaults];

    // do a bunch of checking
    // put up alert sheet if error
    
    [portField validateEditing];
    
    if([[hostField stringValue] compare:@""] == NSOrderedSame) {
	NSBeginAlertSheet(NSLocalizedString(@"Invalid Host Name", @""), nil, nil, nil, gWindow, nil, nil, nil, nil, NSLocalizedString(@"You must enter the host name of a tracker.", @""));
    }
    else if([[portField stringValue] compare:@""] == NSOrderedSame) {
	NSBeginAlertSheet(NSLocalizedString(@"Invalid Port Number", @""), nil, nil, nil, gWindow, nil, nil, nil, nil, NSLocalizedString(@"You must enter the port number of a tracker.", @""));
    }
    else if (fname == nil) {
    	NSBeginAlertSheet(NSLocalizedString(@"Invalid File", @"invalid file chose fo generate"), nil, nil, nil, gWindow, nil, nil, nil, nil, NSLocalizedString(@"You must drag a file or folder into the generate window first.", @"empty file for generate"));
    }
    else {
	[defaults setObject:[hostField stringValue] forKey:THOSTKEY];
	[defaults setObject:[portField stringValue] forKey:TPORTKEY];
	a = [fname pathComponents];
	range.location = 0;
	range.length = [a count] -1;
	[panel beginSheetForDirectory:[NSString pathWithComponents:[a subarrayWithRange:range]] file:[[a objectAtIndex:[a count] -1] stringByAppendingString:@".torrent"] modalForWindow:gWindow modalDelegate:self
	    didEndSelector:@selector(savePanelDidEnd:returnCode:contextInfo:) contextInfo:panel];
    }
    
}

- (void)savePanelDidEnd:(NSWindow *)sheet returnCode:(int)returnCode contextInfo:(void  *)contextInfo {
    NSSavePanel *panel = (NSSavePanel *)contextInfo;
    NSString *f = [panel filename];
    NSString *url;
    NSConnection *conn;
    NSMutableDictionary *dict = [NSMutableDictionary dictionaryWithCapacity:5];
    NSPort *left, *right;

    if(returnCode == 1) {
    	left = [NSPort port];
	right = [NSPort port];
	conn = [[NSConnection alloc] initWithReceivePort:left sendPort:right];
	[conn setRootObject:self];
	url = [NSString stringWithFormat:@"http://%@:%@/announce", [hostField stringValue], [portField stringValue]];
	[dict setObject:right forKey:@"receive"];
	[dict setObject:left forKey:@"send"];
	[dict setObject:f forKey:@"f"];
	[dict setObject:fname forKey:@"fname"];
	[dict setObject:url forKey:@"url"];
	[gButton setEnabled:NO];
	[progress startAnimation:self];
	[gWindow unregisterDraggedTypes];
	[NSThread detachNewThreadSelector:@selector(doGenerate:) toTarget:[self class]  
	withObject:dict];
    }
}

- (void)endGenerate {
    [progress stopAnimation:self];
    [gWindow registerForDraggedTypes:[NSArray arrayWithObjects:NSFilenamesPboardType, nil]];
    [gButton setEnabled:YES];
}

+ (void)doGenerate:(NSDictionary *)dict
{
    PyObject *mm, *md;
    PyObject *mmf, *res, *enc, *be;
    FILE *desc;
    NSString *f, *url, *filename;
    PyThreadState *ts;
    NSAutoreleasePool *pool = [[NSAutoreleasePool alloc] init];
    id foo;
    ts = PyThreadState_New([[NSApp delegate] tstate]->interp);
    PyEval_RestoreThread(ts);    

    f = [dict objectForKey:@"f"];
    filename = [dict objectForKey:@"fname"];
    url = [dict objectForKey:@"url"];
    
    mm = PyImport_ImportModule("btmakemetafile");
    md = PyModule_GetDict(mm);
    mmf = PyDict_GetItemString(md, "makeinfo");
    mm = PyImport_ImportModule("BitTorrent.bencode");
    md = PyModule_GetDict(mm);
    be = PyDict_GetItemString(md, "bencode");

    res = PyObject_CallFunction(mmf, "si", [filename cString],  1048576);
    if(res)
	enc = PyObject_CallFunction(be, "{s:O,s:s}", "info", res, "announce", [url cString]);
    if(PyErr_Occurred())
	PyErr_Print();
    else {
	desc = fopen([f cString], "w");
	fwrite(PyString_AsString(enc), sizeof(char), PyString_Size(enc), desc);
	fclose(desc);	
    }	
    if(res) {
	Py_DECREF(res);
    }
    if(enc) {
	Py_DECREF(enc);
    }
    ts = PyEval_SaveThread();
    foo = (id)[[NSConnection connectionWithReceivePort:[dict objectForKey:@"receive"]
				    sendPort:[dict objectForKey:@"send"]]
			rootProxy];
    [foo setProtocolForProxy:@protocol(GCallbacks)];
    [foo endGenerate];
    [pool release];
}

- (void)open
{
    [gWindow makeKeyAndOrderFront:self];
}

- (void)displayFile:(NSString *)f
{
    NSImage *icon;
    // lookup + display icon
    icon = [[NSWorkspace sharedWorkspace] iconForFile:f];
    [iconWell setImage:icon];
    // set path field
    [fileField setStringValue:f];

}


// drag protocol methods
- (NSDragOperation)draggingEntered:(id <NSDraggingInfo>)sender
{
    NSString *f;
    NSPasteboard *board;
    NSArray *names;
    
    // get path off pasteboard
    board = [sender draggingPasteboard];
    names = [board propertyListForType:@"NSFilenamesPboardType"];
    if ([names count] > 0) {
	f = [names objectAtIndex:0];
	[self displayFile:f];
	return NSDragOperationGeneric;
    }
    return NSDragOperationNone;
}

- (void)draggingExited:(id <NSDraggingInfo>)sender
{
    if (fname == nil) {
	[iconWell setImage:nil];
	[fileField setStringValue:@""];
    }
    else {
	[self displayFile:fname];
    }
}

- (BOOL)performDragOperation:(id <NSDraggingInfo>)sender
{
    if(fname != nil) {
	[fname release];
    }
    fname = [[fileField stringValue] retain];
    return YES;
}
@end
