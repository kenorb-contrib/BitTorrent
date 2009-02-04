//
//  CCell.m
//  BitTorrent
//
//  Created by Drue Loewenstern on Sun Mar 28 2004.
//  Copyright (c) 2004 __MyCompanyName__. All rights reserved.
//

#import "CCell.h"

@protocol btresized
- (id) getTimeView;
- (id) getFileView;
- (id) getXFerView;
- (NSNumber *)resized;
- (BOOL) isInColumnReorder;
@end

@implementation CCell

- (void) dealloc 
{
    if(controller != nil) {
        [controller release];
    }
    [super dealloc];
}
- (id)copyWithZone:(NSZone *)zone {
    CCell *c;
    c = [super copyWithZone:zone];
    if (controller != nil) {
        c->controller = [controller retain];
    }
    return c;
}

- (void) setObjectValue:(id)val
{
    if (controller != nil) {
        [controller release];
    }
    controller = [val retain];
}

- (NSBox *)getCView {
  return nil;
}

- (id)getController {
  return controller;
}


- (void)delete:(id)sender {
  NSLog(@">>> delete");
}
@end

@implementation TimeCell
- (NSBox *)getCView {
  return [controller getTimeView];
}
@end

@implementation FileCell
- (NSBox *)getCView {
  return [controller getFileView];
}
@end

@implementation XFerCell
- (NSBox *)getCView {
  return [controller getXFerView];
}
@end
