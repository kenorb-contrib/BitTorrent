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

import os
import sys
import pwd
import grp
import stat
import logging
from twisted.scripts import twistd
import atexit
from BTL.log import injectLogger
from BTL.platform import app_name

noisy = False
def getuid_from_username(username):
    return pwd.getpwnam(username)[2]

def getgid_from_username(username):
    return pwd.getpwnam(username)[3]

def getgid_from_groupname(groupname):
    return grp.getgrnam(groupname)[2]

def daemon(**kwargs):
    """When this function returns, you are a daemon.
       If use_syslog is specified then this installs a logger.
       Iff capture_output is specified then stdout and stderr
       are also directed to syslog.

       valid kwargs:

         - pidfile,
         - logfile,
         - capture_output,    # log stdout and stderr?
         - capture_stdout_name   # getLogger(capture_name) for captured stdout stderr
         - capture_stdout_log_level
         - capture_stderr_name
         - capture_stderr_log_level
         - twisted_info_log_level  # log level for non-errors coming from twisted logging.
         - twisted_error_log_level # log level for errors coming from twisted logging.
         - log_level          # log only things ith level >= log_level.
         - use_syslog, and    # output to syslog.
         - anything defined by twistd.ServerOptions.
    """
    if os.name == 'mac':
        raise NotImplementedError( "Daemonization doesn't work on macs." )

    if noisy:
        print "in daemon"
    uid = os.getuid()
    gid = os.getgid()
    if uid == 0 and not kwargs.has_key("username"):
        raise Exception( "If you start with root privileges you need to "
            "provide a username argument so that daemon() can shed those "
            "privileges before returning." )
    if kwargs.has_key("username") and kwargs["username"]:
        username = kwargs["username"]
        uid = getuid_from_username(username)
        if noisy:
            print "setting username to uid of '%s', which is %d." % ( username, uid )
        if uid != os.getuid() and os.getuid() != 0:
            raise Exception( "When specifying a uid other than your own "
               "you must be running as root for setuid to work. "
               "Your uid is %d, while the specified user '%s' has uid %d."
               % ( os.getuid(), username, uid ) )
        gid = getgid_from_username(username) # uses this user's group
        del kwargs["username"]
    if kwargs.has_key("groupname") and kwargs["groupname"]:
        groupname = kwargs["groupname"]
        if noisy:
            print "setting groupname to gid of '%s', which is %d." % (groupname,gid)
        gid = getgid_from_groupname(groupname)
        del kwargs["groupname"]
    capture_output = kwargs.get("capture_output", False)
    if kwargs.has_key("capture_output"):
        del kwargs["capture_output"]
    capture_stdout_name = kwargs.get("capture_stdout_name", "stdout" )
    if kwargs.has_key("capture_stdout_name"):
        del kwargs["capture_stdout_name"]
    capture_stderr_name = kwargs.get("capture_stderr_name", "stderr" )
    if kwargs.has_key("capture_stderr_name"):
        del kwargs["capture_stderr_name"]
    capture_stdout_log_level = kwargs.get("capture_stdout_log_level", logging.INFO )
    if kwargs.has_key("capture_stdout_log_level"):
        del kwargs["capture_stdout_log_level"]
    capture_stderr_log_level = kwargs.get("capture_stderr_log_level", logging.INFO )
    if kwargs.has_key("capture_stderr_log_level"):
        del kwargs["capture_stderr_log_level"]
    log_level = kwargs.get("log_level", logging.INFO)
    if kwargs.has_key("log_level"):
        del kwargs["log_level"]
    twisted_info_log_level = kwargs.get("twisted_info_log_level", logging.INFO )
    if kwargs.has_key("twisted_info_log_level"):
        del kwargs["twisted_info_log_level"]
    twisted_error_log_level = kwargs.get("twisted_error_log_level", logging.ERROR )
    if kwargs.has_key("twisted_error_log_level"):
        del kwargs["twisted_error_log_level"]

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
    logfile = config.get('log_file', None )
    use_syslog = config.get('use_syslog', sys.platform != 'darwin' and not logfile)
    if config.has_key('logfile') and config['logfile']:
        if 'use_syslog' in config and config['use_syslog']:
            raise Exception( "You have specified both a logfile and "
                "that the daemon should use_syslog.  Specify one or "
                "the other." )
        injectLogger(use_syslog=False, log_file=config['logfile'], log_level = log_level,
                     capture_output = capture_output,
                     capture_stdout_name = capture_stdout_name,
                     capture_stderr_name = capture_stderr_name,
                     twisted_info_log_level = twisted_info_log_level,
                     twisted_error_log_level = twisted_error_log_level,
                     capture_stdout_log_level = capture_stdout_log_level,
                     capture_stderr_log_level = capture_stderr_log_level )
    elif use_syslog:
        injectLogger(use_syslog=True, log_level = log_level,
                     capture_output = capture_output,
                     capture_stdout_name = capture_stdout_name,
                     capture_stderr_name = capture_stderr_name,
                     twisted_info_log_level = twisted_info_log_level,
                     twisted_error_log_level = twisted_error_log_level,
                     capture_stdout_log_level = capture_stdout_log_level,
                     capture_stderr_log_level = capture_stderr_log_level )
    else:
        raise Exception( "You are attempting to daemonize without a log file,"
                         "and with use_syslog set to false.  A daemon must "
                         "output to syslog, a logfile, or both." )
    twistd.setupEnvironment(config)  # forks, moves into its own process
                                     # group, forks again, middle process
                                     # exits with status 0.  Creates pid
                                     # file. Also redirects stdout, stderr
                                     # to /dev/null.
    # I should now be a daemon.

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
    #            log.error( str(e), exc_info = sys.exc_info())
    #atexit.register(rmpid)

    if not os.path.exists(pidfile):
        raise Exception( "pidfile %s does not exist" % pidfile )

    os.chown(pidfile, uid, gid)
    os.chmod(pidfile, stat.S_IRUSR|stat.S_IWUSR|stat.S_IROTH|stat.S_IRGRP)

    if os.getuid() == 0:
        twistd.shedPrivileges(False, uid, gid)
    if os.getuid() != uid:
        raise Exception( "twistd failed to setuid to uid %d" % uid )
    if os.getgid() != gid:
        raise Exception( "twistd failed to setgid to gid %d" % gid )
