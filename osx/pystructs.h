#import <Python/Python.h>

// this is the proxy object that has the callbacks for each DL
// encapsulates a connection to the it's DL Window controller
typedef struct {
    PyObject_HEAD
    id dlController;  // NSProxy connection
} bt_ProxyObject;
