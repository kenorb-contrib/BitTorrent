#import <Foundation/Foundation.h>

@protocol BTCallbacks
- (oneway void)finished:(in NSDictionary *)dict;
- (oneway void)display:(in NSDictionary *)dict;
- (NSString *)chooseFile:(in NSString *)defaultFile size:(long)size isDirectory:(int)dir;
@end
