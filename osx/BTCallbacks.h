#import <Foundation/Foundation.h>

@protocol BTCallbacks
- (oneway void)finished;
- (oneway void)error:(in NSString *)str;
- (oneway void)display:(in NSDictionary *)dict;
- (NSString *)chooseFile:(in NSString *)defaultFile size:(long)size isDirectory:(int)dir;
- (oneway void)dlExited;
@end
