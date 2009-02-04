/***
 * unix_socket_tools.h
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
#ifndef _SOCKET_H
#define _SOCKET_H
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>

char* SocketName();
int ClientOpenUnixSocket( char * path );
int ServerOpenUnixSocket( char * path );
int WaitForUnixClient( int sock );
#endif
