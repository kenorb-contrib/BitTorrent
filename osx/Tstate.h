#import <Python/Python.h>
@protocol Tstate
- (PyThreadState *)tstate;
- (void)setTstate:(PyThreadState *)nstate;
@end
