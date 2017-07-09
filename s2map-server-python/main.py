#!/usr/bin/python2

'''Main module for starting the http server and accept request'''

import sys
import logging
import socketserver

import s2map_handler


def start_server(addr='localhost', port=8000):
    '''Given the addr & port settings, start the server'''
    httpd = socketserver.TCPServer((addr, port), s2map_handler.S2Server)
    # dont actually know what this do, come back later
    # httpd.allow_reuse_address = True

    print "http server runs on", addr, ':', port
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print "bye"
        httpd.shutdown()
    except Exception as error:
        logging.exception(error.message)
        httpd.shutdown()


if __name__ == "__main__":
    '''It assumes that the first agrument been pased to the program is the addr, the second
    is the port. For port, an integer type is expected. If it's not the case, an exception
    will be thrown'''
    ARGS = sys.argv
    if len(ARGS) == 2:
        start_server(ARGS[1])
    elif len(ARGS) == 3:
        start_server(ARGS[1], int(ARGS[2]))
    else:
        start_server()
