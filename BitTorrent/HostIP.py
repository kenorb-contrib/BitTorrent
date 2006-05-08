# a very simple (and silly) mechanism for getting the host_ip

import socket
from BitTorrent.platform import bttime
from BitTorrent.obsoletepythonsupport import set

__host_ip = None
__host_ip_cachetime = 0
__host_ips = None
__host_ips_cachetime = 0
CACHE_TIME = 300

def get_host_ip():
    global __host_ip
    global __host_ip_cachetime

    if __host_ip is not None and __host_ip_cachetime + CACHE_TIME > bttime():
        return __host_ip
    
    #try:
    #    ip = socket.gethostbyname(socket.gethostname())
    #except socket.error, e:
    # mac sometimes throws an error, so they can just wait.
    # plus, complicated /etc/hosts will return invalid IPs

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(("bittorrent.com", 80))
        endpoint = s.getsockname()
        __host_ip = endpoint[0]
    except socket.error, e:
        __host_ip = socket.gethostbyname(socket.gethostname())

    return __host_ip

def get_host_ips():
    global __host_ips
    global __host_ips_cachetime

    if __host_ips is not None and __host_ips_cachetime + CACHE_TIME > bttime():
        return __host_ips
    
    l = set()

    host_ip = get_host_ip()
    if host_ip is not None:
        l.add(host_ip)

    try:
        hostname = socket.gethostname()
        hostname, aliaslist, ipaddrlist = socket.gethostbyname_ex(hostname)
        l.update(ipaddrlist)
    except socket.error, e:
        print "ARG", e        

    __host_ips = l
    __host_ips_cachetime = bttime()

    return __host_ips