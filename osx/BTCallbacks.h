#import <Foundation/Foundation.h>

@protocol BTCallbacks
- (oneway void)finished;
- (oneway void)error:(in NSString *)str;
- (oneway void)display:(in NSDictionary *)dict;
- (NSString *)chooseFile:(in NSString *)defaultFile size:(in double)size isDirectory:(in int)dir;
- (oneway void)dlExited;
- (oneway void)pathUpdated:(in NSString *)newPath;
@end

@protocol MetaGenerateCallbacks
- (oneway void)progress:(in float)val;
- (oneway void)progressFname:(in NSString *)fname;
@end