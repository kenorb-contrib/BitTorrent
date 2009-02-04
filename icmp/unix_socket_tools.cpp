/***
 * unix_socket_tools.c
 *
 * by David Harrison
 *
 * This module contains functions for handling Unix domain sockets.  The layer
 * supplied by this module hides usage of the data structures passed to
 * UNIX system calls.  This assumes that you want a connectionless
 * byte stream connection between a server and a client.  This module
 * does not support datagram communications.  Note that unix domain sockets
 * are different from internet sockets.  If you want node to node 
 * communications then use the routines in socket_tools.c
 ***/
#include <sys/types.h>
#include <stdlib.h>
#include <strings.h>
#include <sys/param.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <string.h>
#include <stdio.h>
#include "unix_socket_tools.h"

#define ERROR          -1
#define QUEUE_SIZE     5


/***
 * SocketName
 *
 * This will generate a path to a file to use as a socket.  The socket
 * will be placed in the user's home directory.  This function does not
 * need to be called unless the user just wants to generate a single use
 * socketname.  The user can pass any path to ClientOpenUnixSocket
 * and ServerOpenUnixSocket just as long as the user has write permission
 * to the directory.
 *
 * Arguments: NONE.
 * Returns:
 *     Pointer to a path string.
 *     NULL = the function failed to allocate space for the HOME environment
 *            variable or it could not find the HOME environment variable.
 ***/
char filename[MAXPATHLEN];
char* SocketName()
{
    char* home;

    if (( home = getenv( "HOME" )) == NULL ) return NULL;
    strcpy( filename, home ); 
    strcat( filename, "/.bittorrent/unix-socket" );
    return filename;  
}


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
int ClientOpenUnixSocket( char* path )
{
    int                 serverlen;
    int                 sock;
    struct sockaddr_un  server;

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
int ServerOpenUnixSocket( char* path )
{
    int                serverlen;
    int                sock;
    struct sockaddr_un server;

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
    if ( bind( sock, (struct sockaddr *) &server, serverlen ) == ERROR )
        return ERROR;

    /**
     ** Set the socket to listen.
     **/
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
 * functions on unix domaint sockets.  See socket_tools.c for TCP/IP sockets. 
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

