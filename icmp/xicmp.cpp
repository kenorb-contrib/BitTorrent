/* 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
*/

/**
 * This program forwards ICMP echo and responses and only ICMP echoes
 * and responses to a raw socket from a unix socket or the reverse
 * direction.  It otherwise does not modify the packets.  By running
 * this process as setuid, it allows programs to send ICMP messages
 * without root.  This program only ensures that the messages passed
 * along to the raw socket are IPv4 with appropriate size, have the
 * ICMP protocol number, and have the ICMP message type of either 
 * an echo reply or repsonse.
 *
 * xicmp.cpp is intended to run as a separate process executed as root so that
 * it can access raw sockets.  THIS FILE MUST NOT BE WRITABLE BY ANY
 * UNPRIVILEGED USER. 
 *
 * by David Harrison
 */
#include <stdlib.h>
#include <unistd.h>
#include <iostream>
#include <stdio.h>
//#include "unix_socket_tools.h"
#include <string.h>
#include <strings.h>
#include <sys/select.h>
#include <sys/time.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <netinet/ip.h>
#include <arpa/inet.h>
#include <sys/param.h>
#include <errno.h>
#include <netinet/ip_icmp.h>
#include <map>
//#include <ext/hash_map>

const int BUFLEN      = 1500;
const int ERROR       =   -1;
const int QUEUE_SIZE  =    5;
using namespace std;

map< int, const char* > errmsg;
static struct init_errmsg {
    init_errmsg() {
        // All of this text was cut and pasted from the linux man pages.
        // the error messages may not be correct since they may contain
        // text that is specific to a given system call.  Most of the text 
        // comes from the select, read, and write man pages.
        errmsg[EACCES         ] = "Permission to create a socket of the specified type and/or protocol is denied.";
        errmsg[EAFNOSUPPORT   ] = "The implementation does not support the specified  address  family.";
        errmsg[EINVAL         ] = "Unknown protocol, or protocol family not available.";
        errmsg[EMFILE         ] = "Process file table overflow.";
        errmsg[ENFILE         ] = "The  system  limit  on  the  total number of open files has been reached.";
        errmsg[ENOBUFS        ] = "Insufficient memory is available.  The socket cannot be created until sufficient resources are freed.";
        errmsg[ENOMEM         ] = "Insufficient memory is available.  The socket cannot be created until sufficient resources are freed.";
        errmsg[EPROTONOSUPPORT] = "The  protocol  type  or  the specified protocol is not supported within this domain.";
        errmsg[EAGAIN] = "Non-blocking  I/O has been selected using O_NONBLOCK and no data was immediately available for reading.";
        errmsg[EBADF] =  "fd is not a valid file descriptor or is not open for reading.";
        errmsg[EFAULT] = "buf is outside your accessible address space.";
        errmsg[EINTR  ] = "The call was interrupted by a signal before any data was read.";
        errmsg[EINVAL ] = "fd is attached to an object which is unsuitable for reading;  or the  file  was  opened  with  the  O_DIRECT flag, and either the address specified in buf, the value specified in count,  or  the current file offset is not suitably aligned.";
        errmsg[EIO    ] = "I/O error. This will happen for example when the process is in a background process group, tries to  read  from  its  controlling tty,  and  either it is ignoring or blocking SIGTTIN or its process group is orphaned.  It may also occur when there is a  low-level I/O error while reading from a disk or tape.";
        errmsg[EISDIR ] = "fd refers to a directory.";
        errmsg[EPIPE] = "fd is connected to a pipe or socket whose reading end is closed.  When  this  happens the writing process will also receive a SIG- PIPE signal.  (Thus, the write return value is seen only if  the program catches, blocks or ignores this signal.)";

    }
} init_errmsg_instance;

void print_errno() {
    if ( errmsg.find(errno) != errmsg.end() )
        cerr << errmsg[errno];
    else cerr << "errno=" << errno;
    cerr << endl << flush;
}

void hexout( const char *buf, ssize_t len ) {
    size_t i, j;
    char temp[32];
    char intstr[100];
    char to_print[100];
    unsigned char c;
    char *p = &to_print[0];
    temp[0] = intstr[0] = to_print[0] = '\0';
   
    cout << "buffer len=" << len << endl;
    for ( i = 0; i < len; ++i, ++buf, ++p ) {
        c = (unsigned char) *buf;
        sprintf( temp, "%02x ", (unsigned int) c );  
        strcat( intstr, temp );
        if ( *buf >= ' ' && *buf < '~' && *buf != '\\' ) 
            *p = *buf;
        else *p = '.';
        if ( i % 8 == 7 ) {
            ++p;
            *p = '\0';
            p = (&to_print[0])-1;
            cout << to_print << "\t" << intstr << endl;
            temp[0] = intstr[0] = to_print[0] = '\0';
        }
    }

    // if last line was not output...
    if ( i % 8 != 7 ) { 
        // add padding whitespace so that to_print is always 8 characters wide.
        for ( ; i % 8 < 7; ++i, ++p ) *p = ' ';
        *p = ' ';
        ++p;
        *p = '\0';

        // output last line.
        cout << to_print << "\t" << intstr << endl << flush;
    }
}

/***
 * SocketName
 *
 * Builds the filename ~/.bittorrent/xicmp-unix-socket directory.
 *
 * Returns:
 *     Pointer to a path string.  The string is static memory.
 *     NULL = the function failed to allocate space for the HOME environment
 *            variable or it could not find the HOME environment variable.
 ***/
//char filename[MAXPATHLEN];
//char* SocketName()
//{
//    char* home;
//
//    if (( home = getenv( "HOME" )) == NULL ) return NULL;
//    strcpy( filename, home ); 
//    strcat( filename, "/.bittorrent/xicmp-unix-socket" );
//    return filename;  
//}


/***
 * ClientOpenUnixSocket
 *
 * This function will create a socket and then attempt to connect to the
 * corresponding server socket.
 *
 * Arguments:
 *     path:   This is the path to the UNIX socket file.
 *
 * Returns:
 *     >= 0 :  the file descriptor of the socket.
 *     -1   : error.  errno indicates the error.
 ***/
int ClientOpenUnixSocket( const char* path )
{
    int                 serverlen;
    int                 sock;
    sockaddr_un  server;

    /**
     ** Create the socket.
     **/
    sock = socket( AF_UNIX, SOCK_STREAM, 0 );
    if ( sock == ERROR ) return ERROR;

    /**
     ** Connect to the socket with given path and on the server. 
     **/
    bzero( (char*) &server, sizeof( server ));
    server.sun_family = AF_UNIX;
    strcpy( server.sun_path, path );
    serverlen = strlen( server.sun_path ) + sizeof( server.sun_family );
    if (( connect( sock, (struct sockaddr*) &server, serverlen ))== ERROR )
        return ERROR;

    /**
     ** Return the file descriptor of the socket.
     **/
    return sock;
}


/***
 * ServerOpenUnixSocket
 *
 * This function will create a socket, bind it to the server's path
 * and then set the socket to listen for connections.
 * When set to listen, the program won't actually halt listening for
 * a connection.  You must call WaitForClient to get the program to
 * block until a connection is established.
 *
 * Arguments:
 *     path: path to the unix socket file.
 *
 * Returns:
 *     >= 0 : the file descriptor of the server's socket.
 *     -1   : error. errno indicates the error.
 ***/
int ServerOpenUnixSocket( const char* path )
{
    int                serverlen;
    int                sock;
    struct sockaddr_un server;
    int                status;

    cout << "ServerOpenUnixSocket " << path << endl;
    /** Try to remove the path if it exists. **/
    status = unlink(path);
    if ( status == ERROR ) return ERROR;

    /**
     ** Create a socket.
     **/
    sock = socket( AF_UNIX, SOCK_STREAM, 0 );
    if ( sock == ERROR ) return ERROR;

    /**
     ** Bind the socket to a path and an address.
     **/
    bzero((char *) &server, sizeof(server));
    server.sun_family = AF_UNIX;
    strcpy( server.sun_path, path );
    serverlen = strlen( server.sun_path ) + sizeof( server.sun_family );
    cout << "ServerOpenUnixSocket: bind" << endl << flush;
    if ( bind( sock, (struct sockaddr *) &server, serverlen ) == ERROR )
        return ERROR;

    /**
     ** Set the socket to listen.
     **/
    cout << "ServerOpenUnixSocket: listen" << endl << flush;
    if ( listen( sock, QUEUE_SIZE ) == ERROR ) return ERROR;

    /**
     ** Return the sockets file desciptor.
     **/
    return sock;
}



/***
 * WaitForUnixClient
 *
 * This function will block the caller process until a client attempts to
 * make a connectioni at which time this function will accept the connection
 * and return the new file descriptor for the socket.  Note that this
 * functions on unix domain sockets.  See socket_tools.c for TCP/IP sockets. 
 *
 * Arguments:
 *     sock : socket file descriptor for server.
 *
 * Returns:
 *     >= 0  : file descriptor of the new socket to use with the client.
 *     -1    : error.  The type of error is stored in errno.
 ***/
int WaitForUnixClient( int sock )
{
    socklen_t          client_length;
    int                newsock;
    struct sockaddr    client;

    /**
     ** Block until a client connects.  Allow any client to connect; therefore,
     ** ignore the "client" record.
     **/
    newsock = accept( sock, &client, &client_length );

    return newsock;
}


// read a single field.
int read_field( int fd, char *buffer, uint32_t len ) {
    long nread = 0;
    int status;
    char temp[100];
    char *p = &buffer[0];
    while ( nread < len ) {
        fflush(stdout);
        status = read(fd, temp, len-nread);
        fflush(stdout);
        if (status < 0 ) {
            // don't return if the read was stopped by an interrupt.
            if ( errno != EINTR ) return status;
        }
        else if (status > 0 ) {
            nread += status;
            bcopy( p, temp, status );
            p += status;
        }
        else return nread;
    }
    return nread;
}

// read a message prefaced by a longword containing its length.
// returns read status if error or number of bytes read.
// if number of bytes to read exceeds buffsz then it returns -1 after
// reading only the message length.
// 
// Returns the message length excluding the leading length longword or
// -1 if the read failed.  Returns 0 if end-of-file.
int read_message( int fd, char *buffer, int buffsz ) {
    uint32_t len;
    int status;
    cout << "read_message: before calling read_field for length." << endl;
    status = read_field( fd, (char*) &len, sizeof(len));
    if ( status <= 0 ) return status;
    len = ntohl(len);
    cout << "read_message: reading message of length " << len << endl;
    if ( len > buffsz ) return -1;
    int nread = read_field( fd, buffer, len );
    if ( nread < len ) return -1;  // don't process partial messages.
    return nread;
}

int write_field( int fd, char *buffer, uint32_t len ) {
    int status;
    char *p = buffer;
    int left = len;
    while ( left > 0 ) {
        status = write(fd,p,left);
        if ( status == -1 ) {
            // don't return if the write was stopped by a write.
            if ( errno != EINTR ) return status;
        }
        else {
            p += status;
            left -= status;
        }
    }
    return len;
}

/**
 * returns number of bytes written excluding the leading length 
 * longword or -1 if an error occurred. 
 */
int write_message( int fd, char *buffer, uint32_t len ) {
    uint32_t nlen = htonl(len);
    int status = write_field( fd, (char*) &nlen, sizeof(nlen) );
    if ( status == -1 ) return status;
    status = write_field( fd, buffer, len );
    if ( status == -1 ) return status;
    return len;
}

/**
 * Returns whether this looks like a valid ICMP echo or reply message.
 */
bool valid_icmp( const char *buf, ssize_t len ) {
    struct ip *iph = (struct ip *) buf;
    struct icmphdr *icmph = (struct icmphdr*) &buf[20];
    if ( len < 32) {
        cout <<  "too short. len=" << len << endl << flush;
        return false;
    }
    if (iph -> ip_v != 4 ) { // IPv4
        cout <<  "wrong version" << endl << flush;
        return false;
    }
    if (iph -> ip_hl != 5) { // should be 5 longwords.
        cout <<  "not 5 longword header length" << endl << flush;
        return false;   
    }
    
    if ( iph->ip_p != 1 ) { // ICMP protocol number is 1
        // 2 = IGMP, 6 = TCP, 17 = UDP
        cout << "protocol number = " << (unsigned int) ((char) (iph->ip_p)) << endl << flush;
        return false;
    }
    if ( icmph-> type != ICMP_ECHOREPLY &&
         icmph-> type != ICMP_ECHO ) 
        return false;
    return true;
}

int main(int argc, const char *argv[]) {
    int port = -1;
    int status; 
    ssize_t nread;
    int ufd, sock;
    char buf[BUFLEN];
    struct ip *iph = (struct ip *) buf;
    memset (buf, 0, BUFLEN);	/* clear the buffer */

    if ( argc != 2 ) {
        cerr << "Usage:" << endl << "  xicmp unix_socket_fname" << endl;
        exit(-1);
    }

    // open a unix socket for communication with BitTorrent.
    const char *fname = argv[1];
    ufd = ClientOpenUnixSocket(fname);
    if ( ufd == -1 ) {
        cerr << "Failed to create server socket to communicate "
             << "with BitTorrent." << endl;
        print_errno();
        exit(-1);
    }

    // make the unix socket readable and writeable by BitTorrent.
    //uid_t real_uid = getuid();
    //gid_t real_gid = getgid();
    //status = chown(name, real_uid, real_gid);
    //if ( status == -1 ) {
    //    cerr << "Cannot change the owner of the unix socket so that "
    //         << "the socket is readable and writeable to BitTorrent. path="
    //         << name << endl;
    //    print_errno();
    //    exit(-1);
    //}
  
    // wait for a unix client to come along.
    //cout << "Waiting for unix client." << endl << flush;
    //ufd = WaitForUnixClient(sock);
    //if ( status == -1 ) {
    //    cerr << "Failed while waiting for BitTorrent to connect to xicmp." 
    //         << endl;
    //    print_errno();
    //    exit(-1);
    //}

    // open a raw socket.
    int raw = socket (PF_INET, SOCK_RAW, IPPROTO_ICMP);
    if ( status == -1 ) {
        cerr << "Failed to create raw socket." << endl;
        print_errno();
        exit(-1);
    }

    // tell kernel that the header is inlcuded
    {				/* lets do it the ugly way.. */
      int one = 1;
      const int *val = &one;
      if (setsockopt (raw, IPPROTO_IP, IP_HDRINCL, val, sizeof (one)) < 0) {
          cerr << "Cannot set the 'header include (IP_HDRINCL)' option on "
               << "raw socket." << endl;
          print_errno();
          exit(-1);
      }
    }

    // define the timeout.
    struct timeval tv;

    // put raw socket and unix sockets in the select.
    fd_set rfds, wfds;    
    timeval val;
    int maxfd;
    if (raw > ufd) maxfd = raw;
    else maxfd = ufd;

    while ( 1 ) {
        FD_ZERO(&rfds);
        FD_SET(raw, &rfds);
        FD_SET(ufd, &rfds);
        tv.tv_sec = 10L;
        tv.tv_usec = 0L;

        // perform select on the unix and raw socket.
        status = select(maxfd + 1, &rfds, NULL, NULL,&tv);
        if ( status == -1 ) {
            cerr << "select() failed." << endl;
            print_errno();
            exit(-1);
        }
     
        // if unix socket then...
        if ( FD_ISSET(ufd, &rfds) ) {
        
            // read from Unix socket.
            nread = read_message(ufd, buf, BUFLEN);
            if ( nread == -1 ) {
                cerr << "Failed to read message from UNIX socket." << endl;
                print_errno();
                exit(-1);
            }
            if ( nread == 0 ) {
                cout << "BitTorrent closed." << endl;
                exit(0);
            }
  
            if ( valid_icmp( buf, nread ) ) {

                struct sockaddr_in sin;
                sin.sin_addr.s_addr = iph->ip_dst.s_addr;
    			/* the sockaddr_in containing the dest. address is used
    			   in sendto() to determine the datagrams path */
    
                sin.sin_family = AF_INET;
                sin.sin_port = 80;  // doesn't matter.
    
                // write to raw socket.
                status = sendto (raw, buf, nread,
    		  0, (struct sockaddr *) &sin, sizeof (sin));
                if ( status == -1 ) {
    	        cerr << "error writing to raw socket" << endl;
                    exit(-1);
                }
            }
        }

        // else read from raw socket and write to Unix socket.
        else if ( FD_ISSET(raw, &rfds) ) {
            sockaddr from;
            socklen_t fromlen;
            nread = recvfrom(raw, buf, BUFLEN, 0, &from, &fromlen);
            if ( nread == -1 ) {
                cerr << "error reading from the raw socket" << endl;
                exit(-1);
            }

            // if it is an ICMP message then forward to UNIX socket.
            if ( valid_icmp(buf, nread) ) {
		hexout( buf, nread ); 
                status = write_message(ufd, buf, (unsigned) nread);  
                if ( status == -1 ) {
                    // don't fail if no one is yet reading from the socket.
                    if ( errno != ENOTCONN ) {
                        cerr << "error writing to the raw socket." << endl;
                        print_errno();
                        exit(-1);
                    }
                }
                if ( status == 0 ) {
                    cerr << "BitTorrent closed" << endl;
                    exit(0);
                }
            }
        }
        else {
            cout << "select returned but neither raw or ufd bits are set." 
                 << endl;
        }
    }

}



