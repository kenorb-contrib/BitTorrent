//
//  ICHelper.m
//  BitTorrent
//
//  Created by Dr. Burris T. Ewell on Sat Jul 27 2002.
//  Copyright (c) 2001 __MyCompanyName__. All rights reserved.
//

#import "ICHelper.h"


#define EXTENSION "\ptorrent"
#define APP "\pBitTorrent"
#define MIMETYPE "\papplication/x-bittorrent"


@implementation ICHelper

- (id) installICHandler:sender
{
    OSStatus err;
    Handle handle = NewHandle(0);
    ICAttr attr;
    ICMapEntry map;
    
    err = ICStart(&ici, 'BTBC');
    if(!err) {
	err = ICFindPrefHandle(ici, "\pMapping", &attr, handle);
	err = ICMapEntriesFilename(ici, handle, "\pfoo.torrent", 
                                &map);
	if (err == icPrefNotFoundErr) {
	    map.totalLength = kICMapFixedLength + PLstrlen(EXTENSION) + PLstrlen(APP) * 3 + PLstrlen(MIMETYPE);
	    map.fixedLength = kICMapFixedLength;
	    map.version = 3;
	    map.fileType = 'BTMF';
	    map.fileCreator = 'BTBC';
	    map.postCreator = 'BTBC';
	    map.flags = kICMapBinaryMask |  kICMapDataForkMask | kICMapPostMask;
	    PLstrcpy(map.extension, EXTENSION);
	    PLstrcpy(map.creatorAppName, APP);
	    PLstrcpy(map.postAppName, APP);
	    PLstrcpy(map.MIMEType, MIMETYPE);
	    PLstrcpy(map.entryName, APP);
	    	    
	    err = ICBegin(ici, icReadWritePerm);
	    err = ICAddMapEntry(ici, handle, &map);
	    err = ICSetPrefHandle(ici, "\pMapping", attr, handle);
	    err = ICEnd(ici);
	}
	err = ICStop(ici);
    }
    return self;
}

@end
