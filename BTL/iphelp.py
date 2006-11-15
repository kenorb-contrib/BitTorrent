import ctypes
from BTL.iptypes import inet_addr, IPAddr, DWORD, ULONG

Iphlpapi = ctypes.windll.Iphlpapi

class MIB_IPADDRROW(ctypes.Structure):
    _fields_ = [("dwAddr", IPAddr),
                ("dwIndex", DWORD),
                ("dwMask", DWORD),
                ("dwBCastAddr", IPAddr),
                ("dwReasmSize", DWORD),
                ("unused1", ctypes.c_ushort),
                ("wType", ctypes.c_ushort),
                ]

MAX_INTERFACES = 10
class MIB_IPADDRTABLE(ctypes.Structure):
    _fields_ = [("dwNumEntries", DWORD),
                ("table", MIB_IPADDRROW * MAX_INTERFACES)]

def get_interface_by_index(index):
    table = MIB_IPADDRTABLE()
    size = ULONG(ctypes.sizeof(table))
    table.dwNumEntries = 0
    Iphlpapi.GetIpAddrTable(ctypes.byref(table), ctypes.byref(size), 0)

    for n in xrange(table.dwNumEntries):
        row = table.table[n]
        if row.dwIndex == index:
            return str(row.dwAddr)
    raise IndexError("interface index out of range")

def get_route_ip(ip=None):
    #ip = socket.gethostbyname('bittorrent.com')
    # doesn't really matter if this is out of date, we're just trying to find
    # the interface to get to the internet.
    ip = ip or '38.99.5.27'
    ip = inet_addr(ip)

    index = ctypes.c_ulong()
    Iphlpapi.GetBestInterface(ip, ctypes.byref(index))
    index = long(index.value)
    try:
        interface_ip = get_interface_by_index(index)
    except:
        interface_ip = None
    return interface_ip

