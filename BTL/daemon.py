# The contents of this file are subject to the BitTorrent Open Source License
# Version 1.1 (the License).  You may not copy or use this file, in either
# source code or executable form, except in compliance with the License.  You
# may obtain a copy of the License at http://www.bittorrent.com/license/.
#
# Software distributed under the License is distributed on an AS IS basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied.  See the License
# for the specific language governing rights and limitations under the
# License.
 
# by David Harrison

import sys, os, stat, pwd, grp
import logging
from twisted.scripts import twistd
import atexit
from BTL.log import injectLogger
from BTL.platform import app_name

def getuid_from_username(username):
    return pwd.getpwnam(username)[2]

def getgid_from_username(username):
    return pwd.getpwnam(username)[3]

def getgid_from_groupname(groupname):
    return grp.getgrnam(groupname)[2]

def daemon(**kwargs):
    """When this function returns, you are a daemon.

       valid kwargs:

         - pidfile,
         - logfile,
         - use_syslog, and
         - anything defined by twistd.ServerOptions.
    """
    if os.name == 'mac':
        raise NotImplementedError( "Daemonization doesn't work on macs." )
    
    uid = os.getuid()
    gid = os.getgid()
    if uid == 0 and not kwargs.has_key("username"):
        raise Exception( "If you start with root privileges you need to "
            "provide a username argument so that daemon() can shed those "
            "privileges before returning." )
    if kwargs.has_key("username") and kwargs["username"]:
        username = kwargs["username"]
        print "setting username to uid of ", username
        uid = getuid_from_username(username) 
        gid = getgid_from_username(username) # uses this user's group
        del kwargs["username"]
    if kwargs.has_key("groupname") and kwargs["groupname"]:
        print "setting groupname to gid of ", kwargs["groupname"]
        gid = getgid_from_groupname(kwargs["groupname"])
        del kwargs["groupname"]

    pid_dir = os.path.join("/var/run/", app_name )
    pidfile = os.path.join( pid_dir, app_name + ".pid")
    if not isinstance(kwargs,twistd.ServerOptions):
        config = twistd.ServerOptions()
        for k in kwargs:
            config[k]=kwargs[k]
    config['daemon'] = True
    if config.has_key("pidfile"):
      pidfile = config['pidfile']
    else:
      config['pidfile'] = pidfile
    pid_dir = os.path.split(pidfile)[0]
    if pid_dir and not os.path.exists(pid_dir):
        os.mkdir(pid_dir)
        os.chown(pid_dir,uid,gid)
    twistd.checkPID(pidfile)
    use_syslog = config.get('use_syslog',True)
    if config.has_key('logfile') and config['logfile']:
        injectLogger(use_syslog=use_syslog, log_file=config['logfile'])
    elif use_syslog:
        injectLogger(use_syslog=True)
    else:
        raise Exception( "You are attempting to daemonize without a log file,"
                         "and with use_syslog set to false.  A daemon must "
                         "output to syslog, a logfile, or both." )
    twistd.setupEnvironment(config)  # forks, moves into its own process
                                     # group, forks again, middle process
                                     # exits with status 0.  Creates pid
                                     # file. Also redirects stdout, stderr
                                     # to /dev/null. 
    # I am now a daemon.
    
    # pid file can be removed because it is in a subdirectory
    # of /var/run that is owned by the user id running
    # the service and not by root.
    #
    # Dave says, "daemon no longer removes pid file.  If
    # monitors see a pidfile exists and the process is not
    # running then the monitor will restart the process.
    # If you want the process to REALLY die then the
    # pid file should be removed external to the program,
    # e.g., by an init.d script that is passed "stop".
    #
    #def rmpid():
    #    if os.path.exists(pidfile):
    #        try:
    #            os.unlink(pidfile)
    #        except Exception,e:
    #            import logging
    #            log = logging.getLogger(app_name)
    #            log.error( str(e), exc_info = sys.exc_info())
    #atexit.register(rmpid)

    if not os.path.exists(pidfile):
        import logging
        log = logging.getLogger(app_name)
        log.error( "pidfile %s does not exist" % pidfile )

    os.chown(pidfile, uid, gid)
    os.chmod(pidfile, stat.S_IRUSR|stat.S_IWUSR|stat.S_IROTH|stat.S_IRGRP)

    if os.getuid() == 0:
        twistd.shedPrivileges(False, uid, gid)
