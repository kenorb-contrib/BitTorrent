#import <python2.2/Python.h>
@protocol Tstate
- (PyThreadState *)tstate;
- (void)setTstate:(PyThreadState *)nstate;
@end
