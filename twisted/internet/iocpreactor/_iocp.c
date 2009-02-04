#include <Python.h>
#include <winsock2.h>
#include <mswsock.h>
#include <windows.h>
#include "structmember.h"

//#define SPEW

static int g_imallocs, g_ifrees, g_amallocs, g_afrees;
static int g_incobj, g_decobj, g_incarg, g_decarg;
static PyObject *callWithLogger;
static PyObject *socket_gaierror;
static PyObject *socket_error;

/* include Python's addrinfo.h unless it causes trouble */
#if defined(_MSC_VER) && _MSC_VER>1200
  /* Do not include addrinfo.h for MSVC7 or greater. 'addrinfo' and
   * EAI_* constants are defined in (the already included) ws2tcpip.h.
   */
#  include <ws2tcpip.h>
#  define HAVE_GETNAMEINFO
#else
#  include "addrinfo.h"
#endif

#if !defined(HAVE_GETNAMEINFO)
#define getnameinfo fake_getnameinfo
#include "getnameinfo.c"
#endif

/*
 * Constants for getnameinfo()
 */
#if !defined(NI_MAXHOST)
#define NI_MAXHOST 1025
#endif
#if !defined(NI_MAXSERV)
#define NI_MAXSERV 32
#endif


// compensate for mingw's (and MSVC6's) lack of recent Windows headers
#ifndef WSAID_CONNECTEX
#define WSAID_CONNECTEX {0x25a207b9,0xddf3,0x4660,{0x8e,0xe9,0x76,0xe5,0x8c,0x74,0x06,0x3e}}
#define WSAID_ACCEPTEX {0xb5367df1,0xcbac,0x11cf,{0x95,0xca,0x00,0x80,0x5f,0x48,0xa1,0x92}}
#define WSAID_GETACCEPTEXSOCKADDRS {0xb5367df2,0xcbac,0x11cf,{0x95,0xca,0x00,0x80,0x5f,0x48,0xa1,0x92}}


typedef
BOOL
(PASCAL FAR * LPFN_CONNECTEX) (
    IN SOCKET s,
    IN const struct sockaddr FAR *name,
    IN int namelen,
    IN PVOID lpSendBuffer OPTIONAL,
    IN DWORD dwSendDataLength,
    OUT LPDWORD lpdwBytesSent,
    IN LPOVERLAPPED lpOverlapped
    );

typedef
BOOL
(PASCAL FAR * LPFN_ACCEPTEX)(
    IN SOCKET sListenSocket,
    IN SOCKET sAcceptSocket,
    IN PVOID lpOutputBuffer,
    IN DWORD dwReceiveDataLength,
    IN DWORD dwLocalAddressLength,
    IN DWORD dwRemoteAddressLength,
    OUT LPDWORD lpdwBytesReceived,
    IN LPOVERLAPPED lpOverlapped
    );

typedef
VOID
(PASCAL FAR * LPFN_GETACCEPTEXSOCKADDRS)(
    IN PVOID lpOutputBuffer,
    IN DWORD dwReceiveDataLength,
    IN DWORD dwLocalAddressLength,
    IN DWORD dwRemoteAddressLength,
    OUT struct sockaddr **LocalSockaddr,
    OUT LPINT LocalSockaddrLength,
    OUT struct sockaddr **RemoteSockaddr,
    OUT LPINT RemoteSockaddrLength
    );
#endif

typedef struct {
    int size;
    char buffer[0];
} AddrBuffer;

LPFN_CONNECTEX gConnectEx;
LPFN_ACCEPTEX gAcceptEx;
LPFN_GETACCEPTEXSOCKADDRS gGetAcceptExSockaddrs;

typedef struct {
    OVERLAPPED ov;
    PyObject *callback;
    PyObject *callback_arg;
} MyOVERLAPPED;

typedef struct {
    PyObject_HEAD
//    PyObject *cur_ops;
    HANDLE iocp;
} iocpcore;

void CALLBACK dummy_completion(DWORD err, DWORD bytes, OVERLAPPED *ov, DWORD flags) {
}

static void
iocpcore_dealloc(iocpcore *self)
{
//    PyDict_Clear(self->cur_ops);
//    Py_DECREF(self->cur_ops);
    CloseHandle(self->iocp);
    self->ob_type->tp_free((PyObject*)self);
}

/*
static PyObject *
iocpcore_getattr(iocpcore *self, char *name) {
    if(!strcmp(name, "have_connectex
}
*/

static PyObject *
iocpcore_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
    iocpcore *self;

    self = (iocpcore *)type->tp_alloc(type, 0);
    if(self != NULL) {
#ifdef SPEW
        printf("calling CreateIoCompletionPort(%d, 0x%p, %d, %d)\n", INVALID_HANDLE_VALUE, NULL, 0, 1);
#endif
        self->iocp = CreateIoCompletionPort(INVALID_HANDLE_VALUE, NULL, 0, 1);
#ifdef SPEW
        printf("    ciocp returned %p, err ignored\n", self->iocp );
#endif
        if(!self->iocp) {
            Py_DECREF(self);
            return PyErr_SetFromWindowsErr(0);
        }
//        self->cur_ops = PyDict_New();
//        if(!self->cur_ops) {
//            CloseHandle(self->iocp);
//            Py_DECREF(self);
//            return NULL;
//        }
    }
    return (PyObject *)self;
}

static PyObject *iocpcore_doIteration(iocpcore* self, PyObject *args) {
    long timeout;
    double ftimeout;
    PyObject *tm, *ret, *object, *object_arg;
    DWORD bytes;
    unsigned long key;
    MyOVERLAPPED *ov;
    int res, err;
    if(!PyArg_ParseTuple(args, "d", &ftimeout)) {
        PyErr_Clear();
        if(!PyArg_ParseTuple(args, "O", &tm)) {
            return NULL;
        }
        if(tm == Py_None) {
            // Default to 0.1 like other reactors do.
            timeout = (int)(0.1 * 1000);
        } else {
            PyErr_SetString(PyExc_TypeError, "Wrong timeout argument");
            return NULL;
        }
    } else {
        timeout = (int)(ftimeout * 1000);
    }
    Py_BEGIN_ALLOW_THREADS;
    res = GetQueuedCompletionStatus(self->iocp, &bytes, &key, (OVERLAPPED**)&ov, timeout);
    Py_END_ALLOW_THREADS;
#ifdef SPEW
    printf("gqcs returned res %d, ov 0x%p\n", res, ov);
#endif
    err = GetLastError();
#ifdef SPEW
    printf("    GLE returned %d\n", err);
#endif
    if(!res) {
        if(!ov) {
#ifdef SPEW
            printf("gqcs returned NULL ov\n");
#endif
            if(err != WAIT_TIMEOUT) {
                return PyErr_SetFromWindowsErr(err);
            } else {
                return Py_BuildValue("");
            }
        }
    }
    // At this point, ov is non-NULL
    // steal its reference, then clobber it to death! I mean free it!
    object = ov->callback;
    object_arg = ov->callback_arg;
    if(object) {
        // this is retarded. GQCS only sets error value if it wasn't succesful
        // (what about forth case, when handle is closed?)
        if(res) {
            err = 0;
        }
#ifdef SPEW
        printf("calling callback with err %d, bytes %ld\n", err, bytes);
#endif
        /* def callWithLogger(logger, func, *args, **kw) */
        ret = PyObject_CallFunction(callWithLogger, "OOllO",
            self, object, err, bytes, object_arg);

        if(!ret) {
            Py_DECREF(object);
            g_decobj++;
            PyMem_Free(ov);
            g_ifrees++;
            return NULL;
        }
        Py_DECREF(ret);
        Py_DECREF(object);
        g_decobj++;
        Py_DECREF(object_arg);
        g_decarg++;
    }
    PyMem_Free(ov);
    g_ifrees++;
    return Py_BuildValue("");
}

static PyObject *iocpcore_WriteFile(iocpcore* self, PyObject *args) {
    HANDLE handle;
    char *buf;
    LARGE_INTEGER offset;
    int buflen, res;
    DWORD err, bytes;
    PyObject *object, *object_arg;
    MyOVERLAPPED *ov;
//    LARGE_INTEGER time, time_after;
//    QueryPerformanceCounter(&time);
    if(!PyArg_ParseTuple(args, "lLt#OO", &handle, &offset, &buf, &buflen, &object, &object_arg)) {
        return NULL;
    }
    if(buflen <= 0) {
        PyErr_SetString(PyExc_ValueError, "Invalid length specified");
        return NULL;
    }
    if(!PyCallable_Check(object)) {
        PyErr_SetString(PyExc_TypeError, "Callback must be callable");
        return NULL;
    }
    ov = PyMem_Malloc(sizeof(MyOVERLAPPED));
    g_imallocs++;
    if(!ov) {
        PyErr_NoMemory();
        return NULL;
    }
    memset(ov, 0, sizeof(MyOVERLAPPED));
    Py_INCREF(object);
    g_incobj++;
    Py_INCREF(object_arg);
    g_incarg++;
    ov->ov.Offset = offset.LowPart;
    ov->ov.OffsetHigh = offset.HighPart;
    ov->callback = object;
    ov->callback_arg = object_arg;
    CreateIoCompletionPort(handle, self->iocp, 0, 1); // sloppy!
#ifdef SPEW
    printf("calling WriteFile(%d, 0x%p, %d, 0x%p, 0x%p)\n", handle, buf, buflen, &bytes, ov);
#endif
    Py_BEGIN_ALLOW_THREADS;
    res = WriteFile(handle, buf, buflen, &bytes, (OVERLAPPED *)ov);
    Py_END_ALLOW_THREADS;
    err = GetLastError();
#ifdef SPEW
    printf("    wf returned %d, err %ld\n", res, err);
#endif
    if(!res && err != ERROR_IO_PENDING) {
        Py_DECREF(object);
        g_decobj++;
        Py_DECREF(object_arg);
        g_decarg++;
        PyMem_Free(ov);
        g_ifrees++;
        return PyErr_SetFromWindowsErr(err);
    }
    if(res) {
        err = 0;
    }
//    QueryPerformanceCounter(&time_after);
//    printf("wf total ticks is %ld", time_after.LowPart - time.LowPart);
    return Py_BuildValue("ll", err, bytes);
}

static PyObject *iocpcore_ReadFile(iocpcore* self, PyObject *args) {
    HANDLE handle;
    char *buf;
    LARGE_INTEGER offset;
    int buflen, res;
    DWORD err, bytes;
    PyObject *object, *object_arg;
    MyOVERLAPPED *ov;
//    LARGE_INTEGER time, time_after;
//    QueryPerformanceCounter(&time);
    if(!PyArg_ParseTuple(args, "lLw#OO", &handle, &offset, &buf, &buflen, &object, &object_arg)) {
        return NULL;
    }
    if(buflen <= 0) {
        PyErr_SetString(PyExc_ValueError, "Invalid length specified");
        return NULL;
    }
    if(!PyCallable_Check(object)) {
        PyErr_SetString(PyExc_TypeError, "Callback must be callable");
        return NULL;
    }
    ov = PyMem_Malloc(sizeof(MyOVERLAPPED));
    g_imallocs++;
    if(!ov) {
        PyErr_NoMemory();
        return NULL;
    }
    memset(ov, 0, sizeof(MyOVERLAPPED));
    Py_INCREF(object);
    g_incobj++;
    Py_INCREF(object_arg);
    g_incarg++;
    ov->ov.Offset = offset.LowPart;
    ov->ov.OffsetHigh = offset.HighPart;
    ov->callback = object;
    ov->callback_arg = object_arg;
    CreateIoCompletionPort(handle, self->iocp, 0, 1); // sloppy!
#ifdef SPEW
    printf("calling ReadFile(%d, 0x%p, %d, 0x%p, 0x%p)\n", handle, buf, buflen, &bytes, ov);
#endif
    Py_BEGIN_ALLOW_THREADS;
    res = ReadFile(handle, buf, buflen, &bytes, (OVERLAPPED *)ov);
    Py_END_ALLOW_THREADS;
    err = GetLastError();
#ifdef SPEW
    printf("    rf returned %d, err %ld\n", res, err);
#endif
    if(!res && err != ERROR_IO_PENDING) {
        Py_DECREF(object);
        g_decobj++;
        Py_DECREF(object_arg);
        g_decarg++;
        PyMem_Free(ov);
        g_ifrees++;
        return PyErr_SetFromWindowsErr(err);
    }
    if(res) {
        err = 0;
    }
//    QueryPerformanceCounter(&time_after);
//    printf("rf total ticks is %ld", time_after.LowPart - time.LowPart);
    return Py_BuildValue("ll", err, bytes);
}

static PyObject *iocpcore_WSASend(iocpcore* self, PyObject *args) {
    HANDLE handle;
    char *buf;
    int buflen, res;
    DWORD err, bytes;
    DWORD flags = 0;
    PyObject *object, *object_arg;
    MyOVERLAPPED *ov;
    WSABUF wbuf;
//    LARGE_INTEGER time, time_after;
//    QueryPerformanceCounter(&time);
    if(!PyArg_ParseTuple(args, "lt#OO", &handle, &buf, &buflen, &object, &object_arg)) {
        return NULL;
    }
    if(buflen <= 0) {
        PyErr_SetString(PyExc_ValueError, "Invalid length specified");
        return NULL;
    }
    if(!PyCallable_Check(object)) {
        PyErr_SetString(PyExc_TypeError, "Callback must be callable");
        return NULL;
    }
    ov = PyMem_Malloc(sizeof(MyOVERLAPPED));
    g_imallocs++;
    if(!ov) {
        PyErr_NoMemory();
        return NULL;
    }
    memset(ov, 0, sizeof(MyOVERLAPPED));
    Py_INCREF(object);
    g_incobj++;
    Py_INCREF(object_arg);
    g_incarg++;
    ov->callback = object;
    ov->callback_arg = object_arg;
    wbuf.buf = buf;
    wbuf.len = buflen;
    CreateIoCompletionPort(handle, self->iocp, 0, 1); // sloppy!
#ifdef SPEW
    printf("calling WSASend(%d, 0x%p, %d, 0x%p, %d, 0x%p, 0x%p)\n", handle, &wbuf, 1, &bytes, flags, (OVERLAPPED *)ov, NULL);
#endif
    Py_BEGIN_ALLOW_THREADS;
    res = WSASend((SOCKET)handle, &wbuf, 1, &bytes, flags, (OVERLAPPED *)ov, NULL);
    Py_END_ALLOW_THREADS;
    err = WSAGetLastError();
#ifdef SPEW
    printf("    ws returned %d, err %ld\n", res, err);
#endif
    if(res == SOCKET_ERROR && err != WSA_IO_PENDING) {
        Py_DECREF(object);
        g_decobj++;
        Py_DECREF(object_arg);
        g_decarg++;
        PyMem_Free(ov);
        g_ifrees++;
        return PyErr_SetFromWindowsErr(err);
    }
    if(!res) {
        err = 0;
    }
//    QueryPerformanceCounter(&time_after);
//    printf("ws total ticks is %ld", time_after.LowPart - time.LowPart);
    return Py_BuildValue("ll", err, bytes);
}

static PyObject *iocpcore_WSARecv(iocpcore* self, PyObject *args) {
    HANDLE handle;
    char *buf;
    int buflen, res;
    DWORD err, bytes;
    DWORD flags = 0;
    PyObject *object, *object_arg;
    MyOVERLAPPED *ov;
    WSABUF wbuf;
//    LARGE_INTEGER time, time_after;
//    QueryPerformanceCounter(&time);
    if(!PyArg_ParseTuple(args, "lw#OO", &handle, &buf, &buflen, &object, &object_arg)) {
        return NULL;
    }
    if(buflen <= 0) {
        PyErr_SetString(PyExc_ValueError, "Invalid length specified");
        return NULL;
    }
    if(!PyCallable_Check(object)) {
        PyErr_SetString(PyExc_TypeError, "Callback must be callable");
        return NULL;
    }
    ov = PyMem_Malloc(sizeof(MyOVERLAPPED));
    g_imallocs++;
    if(!ov) {
        PyErr_NoMemory();
        return NULL;
    }
    memset(ov, 0, sizeof(MyOVERLAPPED));
    Py_INCREF(object);
    g_incobj++;
    Py_INCREF(object_arg);
    g_incarg++;
    ov->callback = object;
    ov->callback_arg = object_arg;
    wbuf.buf = buf;
    wbuf.len = buflen;
    CreateIoCompletionPort(handle, self->iocp, 0, 1); // sloppy!
#ifdef SPEW
    printf("calling WSARecv(%d, 0x%p, %d, 0x%p, 0x%p, 0x%p, 0x%p)\n", handle, &wbuf, 1, &bytes, &flags, (OVERLAPPED *)ov, NULL);
#endif
    Py_BEGIN_ALLOW_THREADS;
    res = WSARecv((SOCKET)handle, &wbuf, 1, &bytes, &flags, (OVERLAPPED *)ov, NULL);
    Py_END_ALLOW_THREADS;
    err = WSAGetLastError();
#ifdef SPEW
    printf("    wr returned %d, err %ld\n", res, err);
#endif
    if(res == SOCKET_ERROR && err != WSA_IO_PENDING) {
        Py_DECREF(object);
        g_decobj++;
        Py_DECREF(object_arg);
        g_decarg++;
        PyMem_Free(ov);
        g_ifrees++;
        return PyErr_SetFromWindowsErr(err);
    }
    if(!res) {
        err = 0;
    }
//    QueryPerformanceCounter(&time_after);
//    printf("wr total ticks is %ld", time_after.LowPart - time.LowPart);
    return Py_BuildValue("ll", err, bytes);
}


static PyObject *
set_error(void)
{
#ifdef MS_WINDOWS
    int err_no = WSAGetLastError();
    static struct {
        int no;
        const char *msg;
    } *msgp, msgs[] = {
        {WSAEINTR, "Interrupted system call"},
        {WSAEBADF, "Bad file descriptor"},
        {WSAEACCES, "Permission denied"},
        {WSAEFAULT, "Bad address"},
        {WSAEINVAL, "Invalid argument"},
        {WSAEMFILE, "Too many open files"},
        {WSAEWOULDBLOCK,
          "The socket operation could not complete "
          "without blocking"},
        {WSAEINPROGRESS, "Operation now in progress"},
        {WSAEALREADY, "Operation already in progress"},
        {WSAENOTSOCK, "Socket operation on non-socket"},
        {WSAEDESTADDRREQ, "Destination address required"},
        {WSAEMSGSIZE, "Message too long"},
        {WSAEPROTOTYPE, "Protocol wrong type for socket"},
        {WSAENOPROTOOPT, "Protocol not available"},
        {WSAEPROTONOSUPPORT, "Protocol not supported"},
        {WSAESOCKTNOSUPPORT, "Socket type not supported"},
        {WSAEOPNOTSUPP, "Operation not supported"},
        {WSAEPFNOSUPPORT, "Protocol family not supported"},
        {WSAEAFNOSUPPORT, "Address family not supported"},
        {WSAEADDRINUSE, "Address already in use"},
        {WSAEADDRNOTAVAIL, "Can't assign requested address"},
        {WSAENETDOWN, "Network is down"},
        {WSAENETUNREACH, "Network is unreachable"},
        {WSAENETRESET, "Network dropped connection on reset"},
        {WSAECONNABORTED, "Software caused connection abort"},
        {WSAECONNRESET, "Connection reset by peer"},
        {WSAENOBUFS, "No buffer space available"},
        {WSAEISCONN, "Socket is already connected"},
        {WSAENOTCONN, "Socket is not connected"},
        {WSAESHUTDOWN, "Can't send after socket shutdown"},
        {WSAETOOMANYREFS, "Too many references: can't splice"},
        {WSAETIMEDOUT, "Operation timed out"},
        {WSAECONNREFUSED, "Connection refused"},
        {WSAELOOP, "Too many levels of symbolic links"},
        {WSAENAMETOOLONG, "File name too long"},
        {WSAEHOSTDOWN, "Host is down"},
        {WSAEHOSTUNREACH, "No route to host"},
        {WSAENOTEMPTY, "Directory not empty"},
        {WSAEPROCLIM, "Too many processes"},
        {WSAEUSERS, "Too many users"},
        {WSAEDQUOT, "Disc quota exceeded"},
        {WSAESTALE, "Stale NFS file handle"},
        {WSAEREMOTE, "Too many levels of remote in path"},
        {WSASYSNOTREADY, "Network subsystem is unvailable"},
        {WSAVERNOTSUPPORTED, "WinSock version is not supported"},
        {WSANOTINITIALISED,
          "Successful WSAStartup() not yet performed"},
        {WSAEDISCON, "Graceful shutdown in progress"},
        /* Resolver errors */
        {WSAHOST_NOT_FOUND, "No such host is known"},
        {WSATRY_AGAIN, "Host not found, or server failed"},
        {WSANO_RECOVERY, "Unexpected server error encountered"},
        {WSANO_DATA, "Valid name without requested data"},
        {WSANO_ADDRESS, "No address, look for MX record"},
        {0, NULL}
    };
    if (err_no) {
        PyObject *v;
        const char *msg = "winsock error";

        for (msgp = msgs; msgp->msg; msgp++) {
            if (err_no == msgp->no) {
                msg = msgp->msg;
                break;
            }
        }

        v = Py_BuildValue("(is)", err_no, msg);
        if (v != NULL) {
            PyErr_SetObject(socket_error, v);
            Py_DECREF(v);
        }
        return NULL;
    }
    else
#endif

    return PyErr_SetFromErrno(socket_error);
}

static PyObject *
set_gaierror(int error)
{
    PyObject *v;

#ifdef EAI_SYSTEM
    /* EAI_SYSTEM is not available on Windows XP. */
    if (error == EAI_SYSTEM)
        return set_error();
#endif

#ifdef HAVE_GAI_STRERROR
    v = Py_BuildValue("(is)", error, gai_strerror(error));
#else
    v = Py_BuildValue("(is)", error, "getaddrinfo failed");
#endif
    if (v != NULL) {
        PyErr_SetObject(socket_gaierror, v);
        Py_DECREF(v);
    }

    return NULL;
}


// yay, rape'n'paste of makeipaddr from socketmodule.c.
static PyObject *
makeipaddr(struct sockaddr *addr, int addrlen)
{
    char buf[NI_MAXHOST];
    int error;

    error = getnameinfo(addr, addrlen, buf, sizeof(buf), NULL, 0,
        NI_NUMERICHOST);
    if (error) {
        set_gaierror(error);
        return NULL;
    }
    return PyString_FromString(buf);
}

// yay, rape'n'paste of makesockaddr from socketmodule.c. "I don't need it, so I removed it!"
static PyObject *
makesockaddr(struct sockaddr *addr, int addrlen, int proto)
{
#ifdef __BEOS__
    /* XXX: BeOS version of accept() doesn't set family correctly */
    addr->sa_family = AF_INET;
#endif

    switch (addr->sa_family) {

    case AF_INET:
    {
        struct sockaddr_in *a;
        PyObject *addrobj = makeipaddr(addr, sizeof(*a));
        PyObject *ret = NULL;
        if (addrobj) {
            a = (struct sockaddr_in *)addr;
            ret = Py_BuildValue("Oi", addrobj, ntohs(a->sin_port));
            Py_DECREF(addrobj);
        }
        return ret;
    }
    /* More cases here... */

    default:
        /* If we don't know the address family, don't raise an
           exception -- return it as a tuple. */
        return Py_BuildValue("is#",
                     addr->sa_family,
                     addr->sa_data,
                     sizeof(addr->sa_data));

    }
}


// yay, rape'n'paste of getsockaddrarg from socketmodule.c. "I couldn't understand what it does, so I removed it!"
static int getsockaddrarg(int sock_family, PyObject *args, struct sockaddr **addr_ret, int *len_ret)
{
    switch (sock_family) {
    case AF_INET:
    {
        struct sockaddr_in* addr;
        char *host;
        int port;
        unsigned long result;
        if(!PyTuple_Check(args)) {
            PyErr_Format(PyExc_TypeError, "AF_INET address must be tuple, not %.500s", args->ob_type->tp_name);
            return 0;
        }
        if(!PyArg_ParseTuple(args, "si", &host, &port)) {
            return 0;
        }
        addr = PyMem_Malloc(sizeof(struct sockaddr_in));
        g_amallocs++;
        result = inet_addr(host);
        if(result == -1) {
            PyMem_Free(addr);
            g_afrees++;
            PyErr_SetString(PyExc_ValueError, "Can't parse ip address string");
            return 0;
        }
#ifdef SPEW
        printf("getsockaddrarg setting addr, %lu, %d, %hu\n", result, AF_INET, htons((short)port));
#endif
        addr->sin_addr.s_addr = result;
        addr->sin_family = AF_INET;
        addr->sin_port = htons((short)port);
        *addr_ret = (struct sockaddr *) addr;
        *len_ret = sizeof *addr;
        return 1;
    }
    default:
        PyErr_SetString(PyExc_ValueError, "bad family");
        return 0;
    }
}


static PyObject *iocpcore_GetAcceptExSockaddrs(iocpcore* self, PyObject *args) {
    char *buf;
    int buflen;
    int localaddrlen = 0;
    int remoteaddrlen = 0;
    struct sockaddr *localaddr = NULL;
    struct sockaddr *remoteaddr = NULL;
    PyObject *pylocaladdr = NULL;
    PyObject *pyremoteaddr = NULL;
    PyObject *res = NULL;
    if(!PyArg_ParseTuple(args, "t#", &buf, &buflen)) {
        return NULL;
    }
    if(buflen <= 0) {
        PyErr_SetString(PyExc_ValueError, "Invalid length specified");
        return NULL;
    }
#ifdef SPEW
    printf("calling GetAcceptExSockaddrs(0x%p, %d, %d, %d, 0x%p, 0x%p, 0x%p, 0x%p)\n", buf, 0, buflen/2, buflen/2, &localaddr, &localaddrlen, &remoteaddr, &remoteaddrlen);
#endif
    gGetAcceptExSockaddrs(buf, 0, buflen/2, buflen/2, &localaddr, &localaddrlen, &remoteaddr, &remoteaddrlen);
#ifdef SPEW
    printf("    gaesa returned 0x%p, %d, 0x%p, %d\n", localaddr, localaddrlen, remoteaddr, remoteaddrlen);
#endif
    if ((localaddr == NULL) || (remoteaddr == NULL)) {
        PyErr_SetString(PyExc_ValueError, "Can't parse buffer");
        goto finally;
    }

    pylocaladdr = makesockaddr(localaddr, localaddrlen, AF_INET);
    if (pylocaladdr == NULL) {
        PyErr_SetString(PyExc_ValueError, "Can't parse local addr");
        goto finally;
    }

    pyremoteaddr = makesockaddr(remoteaddr, remoteaddrlen, AF_INET);
    if (pyremoteaddr == NULL) {
        PyErr_SetString(PyExc_ValueError, "Can't parse remote addr");
        goto finally;
    }

    res = PyTuple_Pack(2, pylocaladdr, pyremoteaddr);

finally:
    Py_XDECREF(pylocaladdr);
    Py_XDECREF(pyremoteaddr);
    return res;
}


static PyObject *iocpcore_WSASendTo(iocpcore* self, PyObject *args) {
    HANDLE handle;
    char *buf;
    int buflen, res, family, addrlen;
    DWORD err, bytes, flags = 0;
    PyObject *object, *object_arg, *address;
    MyOVERLAPPED *ov;
    WSABUF wbuf;
    struct sockaddr *addr;
//    LARGE_INTEGER time, time_after;
//    QueryPerformanceCounter(&time);
    if(!PyArg_ParseTuple(args, "lt#iOOO", &handle, &buf, &buflen, &family, &address, &object, &object_arg)) {
        return NULL;
    }
    if(buflen <= 0) {
        PyErr_SetString(PyExc_ValueError, "Invalid length specified");
        return NULL;
    }
    if(!getsockaddrarg(family, address, &addr, &addrlen)) {
        return NULL;
    }
    if(!PyCallable_Check(object)) {
        PyErr_SetString(PyExc_TypeError, "Callback must be callable");
        return NULL;
    }
    ov = PyMem_Malloc(sizeof(MyOVERLAPPED));
    g_imallocs++;
    if(!ov) {
        PyErr_NoMemory();
        return NULL;
    }
    memset(ov, 0, sizeof(MyOVERLAPPED));
    Py_INCREF(object);
    g_incobj++;
    Py_INCREF(object_arg);
    g_incarg++;
    ov->callback = object;
    ov->callback_arg = object_arg;
    wbuf.len = buflen;
    wbuf.buf = buf;
    CreateIoCompletionPort(handle, self->iocp, 0, 1); // sloppy!
#ifdef SPEW
    printf("calling WSASendTo(%d, 0x%p, %d, 0x%p, %ld, 0x%p, %d, 0x%p, 0x%p)\n", handle, &wbuf, 1, &bytes, flags, addr, addrlen, ov, NULL);
#endif
    Py_BEGIN_ALLOW_THREADS;
    res = WSASendTo((SOCKET)handle, &wbuf, 1, &bytes, flags, addr, addrlen, (OVERLAPPED *)ov, NULL);
    Py_END_ALLOW_THREADS;
    err = WSAGetLastError();
#ifdef SPEW
    printf("    wst returned %d, err %ld\n", res, err);
#endif
    if(res == SOCKET_ERROR && err != WSA_IO_PENDING) {
        Py_DECREF(object);
        g_decobj++;
        Py_DECREF(object_arg);
        g_decarg++;
        PyMem_Free(ov);
        g_ifrees++;
        return PyErr_SetFromWindowsErr(err);
    }
    if(!res) {
        err = 0;
    }
//    QueryPerformanceCounter(&time_after);
//    printf("st total ticks is %ld", time_after.LowPart - time.LowPart);
    return Py_BuildValue("ll", err, bytes);
}

static PyObject *iocpcore_WSARecvFrom(iocpcore* self, PyObject *args) {
    HANDLE handle;
    char *buf;
    int buflen, res, ablen;
    DWORD err, bytes, flags = 0;
    PyObject *object, *object_arg;
    MyOVERLAPPED *ov;
    WSABUF wbuf;
    AddrBuffer *ab;
//    LARGE_INTEGER time, time_after;
//    QueryPerformanceCounter(&time);
    if(!PyArg_ParseTuple(args, "lw#w#OO", &handle, &buf, &buflen, &ab, &ablen, &object, &object_arg)) {
        return NULL;
    }
    if(buflen <= 0) {
        PyErr_SetString(PyExc_ValueError, "Invalid length specified");
        return NULL;
    }
    if(ablen < sizeof(int)+sizeof(struct sockaddr)) {
        PyErr_SetString(PyExc_ValueError, "Address buffer too small");
        return NULL;
    }
    if(!PyCallable_Check(object)) {
        PyErr_SetString(PyExc_TypeError, "Callback must be callable");
        return NULL;
    }
    ov = PyMem_Malloc(sizeof(MyOVERLAPPED));
    g_imallocs++;
    if(!ov) {
        PyErr_NoMemory();
        return NULL;
    }
    memset(ov, 0, sizeof(MyOVERLAPPED));
    Py_INCREF(object);
    g_incobj++;
    Py_INCREF(object_arg);
    g_incarg++;
    ov->callback = object;
    ov->callback_arg = object_arg;
    wbuf.len = buflen;
    wbuf.buf = buf;
    ab->size = ablen;
    CreateIoCompletionPort(handle, self->iocp, 0, 1); // sloppy!
#ifdef SPEW
    printf("calling WSARecvFrom(%d, 0x%p, %d, 0x%p, 0x%p, 0x%p, 0x%p, 0x%p, 0x%p)\n", handle, &wbuf, 1, &bytes, &flags, (struct sockaddr *)ab->buffer, &ab->size, ov, NULL);
#endif
    Py_BEGIN_ALLOW_THREADS;
    res = WSARecvFrom((SOCKET)handle, &wbuf, 1, &bytes, &flags, (struct sockaddr *)ab->buffer, &ab->size, (OVERLAPPED *)ov, NULL);
    Py_END_ALLOW_THREADS;
    err = WSAGetLastError();
#ifdef SPEW
    printf("    wrf returned %d, err %ld\n", res, err);
#endif
    if(res == SOCKET_ERROR && err != WSA_IO_PENDING) {
        Py_DECREF(object);
        g_decobj++;
        Py_DECREF(object_arg);
        g_decarg++;
        PyMem_Free(ov);
        g_ifrees++;
        return PyErr_SetFromWindowsErr(err);
    }
    if(!res) {
        err = 0;
    }
//    QueryPerformanceCounter(&time_after);
//    printf("wrf total ticks is %ld", time_after.LowPart - time.LowPart);
    return Py_BuildValue("ll", err, bytes);
}

// rape'n'paste from socketmodule.c
static PyObject *parsesockaddr(struct sockaddr *addr, int addrlen)
{
    PyObject *ret = NULL;
    if (addrlen == 0) {
        /* No address -- may be recvfrom() from known socket */
        Py_INCREF(Py_None);
        return Py_None;
    }

    switch (addr->sa_family) {
    case AF_INET:
    {
        struct sockaddr_in *a = (struct sockaddr_in *)addr;
        char *s;
        s = inet_ntoa(a->sin_addr);
        if (s) {
            ret = Py_BuildValue("si", s, ntohs(a->sin_port));
        } else {
            PyErr_SetString(PyExc_ValueError, "Invalid AF_INET address");
        }
        return ret;
    }
    default:
        /* If we don't know the address family, don't raise an
           exception -- return it as a tuple. */
        return Py_BuildValue("is#",
                     addr->sa_family,
                     addr->sa_data,
                     sizeof(addr->sa_data));

    }
}

static PyObject *iocpcore_interpretAB(iocpcore* self, PyObject *args) {
    char *buf;
    int len;
    AddrBuffer *ab;
    if(!PyArg_ParseTuple(args, "t#", &buf, &len)) {
        return NULL;
    }
    ab = (AddrBuffer *)buf;
    return parsesockaddr((struct sockaddr *)(ab->buffer), ab->size);
}

static PyObject *iocpcore_getsockinfo(iocpcore* self, PyObject *args) {
    SOCKET handle;
    WSAPROTOCOL_INFO pinfo;
    int size = sizeof(pinfo), res;
    if(!PyArg_ParseTuple(args, "l", &handle)) {
        return NULL;
    }
    res = getsockopt(handle, SOL_SOCKET, SO_PROTOCOL_INFO, (char *)&pinfo, &size);
    if(res == SOCKET_ERROR) {
        return PyErr_SetFromWindowsErr(0);
    }
    return Py_BuildValue("iiii", pinfo.iMaxSockAddr, pinfo.iAddressFamily, pinfo.iSocketType, pinfo.iProtocol);
}

static PyObject *iocpcore_AcceptEx(iocpcore* self, PyObject *args) {
    SOCKET handle, acc_sock;
    char *buf;
    int buflen, res;
    DWORD bytes, err;
    PyObject *object, *object_arg;
    MyOVERLAPPED *ov;
    if(!PyArg_ParseTuple(args, "llOOw#", &handle, &acc_sock, &object, &object_arg, &buf, &buflen)) {
        return NULL;
    }
    if(!PyCallable_Check(object)) {
        PyErr_SetString(PyExc_TypeError, "Callback must be callable");
        return NULL;
    }
    ov = PyMem_Malloc(sizeof(MyOVERLAPPED));
    g_imallocs++;
    if(!ov) {
        PyErr_NoMemory();
        return NULL;
    }
    memset(ov, 0, sizeof(MyOVERLAPPED));
    Py_INCREF(object);
    g_incobj++;
    Py_INCREF(object_arg);
    g_incarg++;
    ov->callback = object;
    ov->callback_arg = object_arg;
    CreateIoCompletionPort((HANDLE)handle, self->iocp, 0, 1); // sloppy!
#ifdef SPEW
    printf("calling AcceptEx(%d, %d, 0x%p, %d, %d, %d, 0x%p, 0x%p)\n", handle, acc_sock, buf, 0, buflen/2, buflen/2, &bytes, ov);
#endif
    Py_BEGIN_ALLOW_THREADS;
    res = gAcceptEx(handle, acc_sock, buf, 0, buflen/2, buflen/2, &bytes, (OVERLAPPED *)ov);
    Py_END_ALLOW_THREADS;
    err = WSAGetLastError();
#ifdef SPEW
    printf("    ae returned %d, err %ld\n", res, err);
#endif
    if(!res && err != ERROR_IO_PENDING) {
        Py_DECREF(object);
        g_decobj++;
        Py_DECREF(object_arg);
        g_decarg++;
        PyMem_Free(ov);
        g_ifrees++;
        return PyErr_SetFromWindowsErr(err);
    }
    if(res) {
        err = 0;
    }
    return Py_BuildValue("ll", err, 0);
}

static PyObject *iocpcore_ConnectEx(iocpcore* self, PyObject *args) {
    SOCKET handle;
    int res, addrlen, family;
    DWORD err;
    PyObject *object, *object_arg, *address;
    MyOVERLAPPED *ov;
    struct sockaddr *addr;
    if(!PyArg_ParseTuple(args, "liOOO", &handle, &family, &address, &object, &object_arg)) {
        return NULL;
    }
    if(!getsockaddrarg(family, address, &addr, &addrlen)) {
        return NULL;
    }
    if(!PyCallable_Check(object)) {
        PyErr_SetString(PyExc_TypeError, "Callback must be callable");
        return NULL;
    }
    ov = PyMem_Malloc(sizeof(MyOVERLAPPED));
    g_imallocs++;
    if(!ov) {
        PyErr_NoMemory();
        return NULL;
    }
    memset(ov, 0, sizeof(MyOVERLAPPED));
    Py_INCREF(object);
    g_incobj++;
    Py_INCREF(object_arg);
    g_incarg++;
    ov->callback = object;
    ov->callback_arg = object_arg;
    CreateIoCompletionPort((HANDLE)handle, self->iocp, 0, 1); // sloppy!
#ifdef SPEW
    printf("calling ConnectEx(%d, 0x%p, %d, 0x%p)\n", handle, addr, addrlen, ov);
#endif
    Py_BEGIN_ALLOW_THREADS;
    res = gConnectEx(handle, addr, addrlen, NULL, 0, NULL, (OVERLAPPED *)ov);
    Py_END_ALLOW_THREADS;
    PyMem_Free(addr);
    g_afrees++;
    err = WSAGetLastError();
#ifdef SPEW
    printf("    ce returned %d, err %ld\n", res, err);
#endif
    if(!res && err != ERROR_IO_PENDING) {
        Py_DECREF(object);
        g_decobj++;
        Py_DECREF(object_arg);
        g_decarg++;
        PyMem_Free(ov);
        g_ifrees++;
        return PyErr_SetFromWindowsErr(err);
    }
    if(res) {
        err = 0;
    }
    return Py_BuildValue("ll", err, 0);
}

static PyObject *iocpcore_PostQueuedCompletionStatus(iocpcore* self, PyObject *args) {
    int res;
    DWORD err;
    PyObject *object, *object_arg;
    MyOVERLAPPED *ov;
    if(!PyArg_ParseTuple(args, "OO", &object, &object_arg)) {
        return NULL;
    }
    if(!PyCallable_Check(object)) {
        PyErr_SetString(PyExc_TypeError, "Callback must be callable");
        return NULL;
    }
    ov = PyMem_Malloc(sizeof(MyOVERLAPPED));
    g_imallocs++;
    if(!ov) {
        PyErr_NoMemory();
        return NULL;
    }
    memset(ov, 0, sizeof(MyOVERLAPPED));
    Py_INCREF(object);
    g_incobj++;
    Py_INCREF(object_arg);
    g_incarg++;
    ov->callback = object;
    ov->callback_arg = object_arg;
#ifdef SPEW
    printf("calling PostQueuedCompletionStatus(0x%p)\n", ov);
#endif
    Py_BEGIN_ALLOW_THREADS;
    res = PostQueuedCompletionStatus(self->iocp, 0, 0, (OVERLAPPED *)ov);
    Py_END_ALLOW_THREADS;
    err = WSAGetLastError();
#ifdef SPEW
    printf("    pqcs returned %d, err %ld\n", res, err);
#endif
    if(!res && err != ERROR_IO_PENDING) {
        Py_DECREF(object);
        g_decobj++;
        Py_DECREF(object_arg);
        g_decarg++;
        PyMem_Free(ov);
        g_ifrees++;
        return PyErr_SetFromWindowsErr(err);
    }
    if(res) {
        err = 0;
    }
    return Py_BuildValue("ll", err, 0);
}

PyObject *iocpcore_AllocateReadBuffer(PyObject *self, PyObject *args)
{
    int bufSize;
    if(!PyArg_ParseTuple(args, "i", &bufSize)) {
        return NULL;
    }
    return PyBuffer_New(bufSize);
}

PyObject *iocpcore_get_mstats(PyObject *self, PyObject *args)
{
    if(!PyArg_ParseTuple(args, "")) {
        return NULL;
    }
    return Py_BuildValue("(ii)(ii)(ii)(ii)", g_imallocs, g_ifrees, g_amallocs, g_afrees, g_incobj, g_decobj, g_incarg, g_decarg);
}

static PyMethodDef iocpcore_methods[] = {
    {"doIteration", (PyCFunction)iocpcore_doIteration, METH_VARARGS,
     "Perform one event loop iteration"},
    {"issueWriteFile", (PyCFunction)iocpcore_WriteFile, METH_VARARGS,
     "Issue an overlapped WriteFile operation"},
    {"issueReadFile", (PyCFunction)iocpcore_ReadFile, METH_VARARGS,
     "Issue an overlapped ReadFile operation"},
    {"issueWSASend", (PyCFunction)iocpcore_WSASend, METH_VARARGS,
     "Issue an overlapped WSASend operation"},
    {"issueWSARecv", (PyCFunction)iocpcore_WSARecv, METH_VARARGS,
     "Issue an overlapped WSARecv operation"},
    {"issueWSASendTo", (PyCFunction)iocpcore_WSASendTo, METH_VARARGS,
     "Issue an overlapped WSASendTo operation"},
    {"issueWSARecvFrom", (PyCFunction)iocpcore_WSARecvFrom, METH_VARARGS,
     "Issue an overlapped WSARecvFrom operation"},
    {"interpretAB", (PyCFunction)iocpcore_interpretAB, METH_VARARGS,
     "Interpret address buffer as returned by WSARecvFrom"},
    {"issueAcceptEx", (PyCFunction)iocpcore_AcceptEx, METH_VARARGS,
     "Issue an overlapped AcceptEx operation"},
    {"GetAcceptExSockaddrs", (PyCFunction) iocpcore_GetAcceptExSockaddrs, METH_VARARGS,
     "Given data obtained from AcceptEx, retrieve the local and remote address tuples"},
    {"issueConnectEx", (PyCFunction)iocpcore_ConnectEx, METH_VARARGS,
     "Issue an overlapped ConnectEx operation"},
    {"issuePostQueuedCompletionStatus", (PyCFunction)iocpcore_PostQueuedCompletionStatus, METH_VARARGS,
     "Issue an overlapped PQCS operation"},
    {"getsockinfo", (PyCFunction)iocpcore_getsockinfo, METH_VARARGS,
     "Given a socket handle, retrieve its protocol info"},
    {"AllocateReadBuffer", (PyCFunction)iocpcore_AllocateReadBuffer, METH_VARARGS,
     "Allocate a buffer to read into"},
    {"get_mstats", (PyCFunction)iocpcore_get_mstats, METH_VARARGS,
     "Get memory leak statistics"},
    {NULL}
};

static PyTypeObject iocpcoreType = {
    PyObject_HEAD_INIT(NULL)
    0,                         /*ob_size*/
    "_iocp.iocpcore",             /*tp_name*/
    sizeof(iocpcore),             /*tp_basicsize*/
    0,                         /*tp_itemsize*/
    (destructor)iocpcore_dealloc, /*tp_dealloc*/
    0,                         /*tp_print*/
//    (getattrfunc)iocpcore_getattr, /*tp_getattr*/
    0, /*tp_getattr*/
    0,                         /*tp_setattr*/
    0,                         /*tp_compare*/
    0,                         /*tp_repr*/
    0,                         /*tp_as_number*/
    0,                         /*tp_as_sequence*/
    0,                         /*tp_as_mapping*/
    0,                         /*tp_hash */
    0,                         /*tp_call*/
    0,                         /*tp_str*/
    0,                         /*tp_getattro*/
    0,                         /*tp_setattro*/
    0,                         /*tp_as_buffer*/
    Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE, /*tp_flags*/
    "core functionality for IOCP reactor", /* tp_doc */
    0,                         /* tp_traverse */
    0,                         /* tp_clear */
    0,                         /* tp_richcompare */
    0,                         /* tp_weaklistoffset */
    0,                         /* tp_iter */
    0,                         /* tp_iternext */
    iocpcore_methods,             /* tp_methods */
//    iocpcore_members,             /* tp_members */
    0,             /* tp_members */
//    iocpcore_getseters,           /* tp_getset */
    0,           /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
//    (initproc)iocpcore_init,      /* tp_init */
    0,      /* tp_init */
    0,                         /* tp_alloc */
    iocpcore_new,                 /* tp_new */
};

static PyMethodDef module_methods[] = {
    {NULL}  /* Sentinel */
};

#ifndef PyMODINIT_FUNC /* declarations for DLL import/export */
#define PyMODINIT_FUNC void
#endif
PyMODINIT_FUNC
init_iocp(void) 
{
    int have_connectex = 1;
    PyObject *m;
    PyObject *socket_module;
    PyObject *tp_log;
    GUID guid1 = WSAID_CONNECTEX; // should use one GUID variable, but oh well
    GUID guid2 = WSAID_ACCEPTEX;
    GUID guid3 = WSAID_GETACCEPTEXSOCKADDRS;
    DWORD bytes, ret;
    SOCKET s;
    if(PyType_Ready(&iocpcoreType) < 0) {
        return;
    }
    socket_module = PyImport_ImportModule("_socket"); // cause WSAStartup to get called
    if(!socket_module) {
        return;
    }
    // shouldn't we be increfing these?
    socket_gaierror = PyObject_GetAttrString(socket_module, "gaierror");
    socket_error = PyObject_GetAttrString(socket_module, "error");
    Py_DECREF(socket_module);
    if (!socket_gaierror) {
        return;
    }
    if (!socket_error) {
        return;
    }

    s = socket(AF_INET, SOCK_STREAM, 0);
    ret = WSAIoctl(s, SIO_GET_EXTENSION_FUNCTION_POINTER, &guid1, sizeof(GUID),
                   &gConnectEx, sizeof(gConnectEx), &bytes, NULL, NULL);
    if(ret == SOCKET_ERROR) {
        have_connectex = 0;
    }
    
    ret = WSAIoctl(s, SIO_GET_EXTENSION_FUNCTION_POINTER, &guid2, sizeof(GUID),
                   &gAcceptEx, sizeof(gAcceptEx), &bytes, NULL, NULL);
    if(ret == SOCKET_ERROR) {
        PyErr_SetFromWindowsErr(0);
        return;
    }

    ret = WSAIoctl(s, SIO_GET_EXTENSION_FUNCTION_POINTER, &guid3, sizeof(GUID),
                   &gGetAcceptExSockaddrs, sizeof(gGetAcceptExSockaddrs), &bytes, NULL, NULL);
    if(ret == SOCKET_ERROR) {
        PyErr_SetFromWindowsErr(0);
        return;
    }

    closesocket(s);

    /* Grab twisted.python.log.callWithLogger */
    tp_log = PyImport_ImportModule("twisted.python.log");
    if (!tp_log) {
        return;
    }

    // shouldn't we be increfing this?
    callWithLogger = PyObject_GetAttrString(tp_log, "callWithLogger");
    Py_DECREF(tp_log);
    if (!callWithLogger) {
        return;
    }
    
    m = Py_InitModule3("_iocp", module_methods,
                       "core functionality for IOCP reactor");
    if(!m) {
        return;
    }

    ret = PyModule_AddIntConstant(m, "have_connectex", have_connectex);
    if(ret == -1) {
        return;
    }

    Py_INCREF(&iocpcoreType);
    PyModule_AddObject(m, "iocpcore", (PyObject *)&iocpcoreType);
}

