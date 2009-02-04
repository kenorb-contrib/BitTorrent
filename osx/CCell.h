//
//  CCell.h
//  BitTorrent
//
//  Created by Drue Loewenstern on Sun Mar 28 2004.
//  Copyright (c) 2004 __MyCompanyName__. All rights reserved.
//

#import <Foundation/Foundation.h>


@interface CCell : NSCell {
    id controller;
    int resize;
}


- (void) dealloc;
- (id)copyWithZone:(NSZone *)zone;
- (void) setObjectValue:(id)val;
- (id) getController;
@end

@interface TimeCell : CCell {}
- (NSBox *)getCView;
@end
@interface FileCell : CCell {}
- (NSBox *)getCView;
@end
@interface XFerCell : CCell {}
- (NSBox *)getCView;
@end
