# Written by John Hoffman
# derived by example code by Myers Carpenter
# see LICENSE.txt for license information

import socket
from traceback import print_exc

try:
    True
except:
    True = 1
    False = 0

DEBUG = False

local_IP = None
try:
    import pythoncom, win32com.client
                # exception if not windows or needed libs not in place
    from subnetparse import IP_List
    local_IPs = IP_List()
    local_IPs.set_intranet_addresses()
    
    for info in socket.getaddrinfo(socket.gethostname(),0):
                # exception if socket library isn't recent
        ip = info[4][0]
        if local_IPs.includes(ip):
            local_IP = ip
            if DEBUG:
                print 'Local IP found: '+ip
            break
    # local_IP stays None if the intranet address can't be found
    # hopefully there aren't more than one!
except:
    if DEBUG:
        print_exc()

local_IPs = None    # drop this object, not needed any more


def _get_map():
    return win32com.client.Dispatch("HNetCfg.NATUPnP").StaticPortMappingCollection
        # may raise exception, may return None if UPnP is not enabled


def UPnP_test():
    try:
        assert local_IP is not None     # checks several things, above
        pythoncom.CoInitialize()
        assert _get_map() is not None   # checks UPnP support and if it's enabled
        pythoncom.CoUninitialize()
        return True
    except:
        return False


def UPnP_check_available(begp,endp):    # warning! This is slow
    pythoncom.CoInitialize()
    try:
        map = _get_map()
    except:
        pythoncom.CoUninitialize()
        return None
    ports_in_use = []
    for i in xrange(len(map)):
        try:
            port = map[i].ExternalPort
        except:
            continue
        if port >= begp and port <= endp:
            ports_in_use.append(port)
    pythoncom.CoUninitialize()
    return ports_in_use


def UPnP_open_port(p):
    pythoncom.CoInitialize()
    map = _get_map()
    try:
        map.Add(p,'TCP',p,local_IP,True,'BT')
        if DEBUG:
            print 'port opened: '+local_IP+':'+str(p)
        success = True
    except:
        if DEBUG:
            print "COULDN'T OPEN "+str(p)
            print_exc()
        success = False
    pythoncom.CoUninitialize()
    return success


def UPnP_close_port(p):
    pythoncom.CoInitialize()
    map = _get_map()
    try:
        map.Remove(p,'TCP')
        success = True
        if DEBUG:
            l = UPnP_check_available(p,p)
            if l:
                print 'ERROR CLOSING '+str(p)
            else:
                print 'port closed: '+str(p)
    except:
        if DEBUG:
            print 'ERROR CLOSING '+str(p)
            print_exc()
        success = False
    pythoncom.CoUninitialize()
    return success
