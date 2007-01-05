# handy stuff for windows ip functions
#
# by Greg Hazel

import ctypes
import socket
import struct

class IPAddr(ctypes.Structure):
    _fields_ = [ ("S_addr", ctypes.c_ulong),
                 ]

    def __str__(self):
        return socket.inet_ntoa(struct.pack("L", self.S_addr))

def inet_addr(ip):
    return IPAddr(struct.unpack("L", socket.inet_aton(ip))[0])

WCHAR = ctypes.wchar_t = ctypes.c_ushort
BYTE = ctypes.c_ubyte
SIZE_T = ctypes.size_t = ctypes.c_uint
ULONG = HANDLE = DWORD = ctypes.c_ulong
NO_ERROR = 0
