#!/usr/bin/env python
import tempfile
import socket
import Queue
import sys
import time
import os
import threading
import StringIO

from PIL import ImageFile

class Message:
    TYPE_IMG = "Img"
    TYPE_XML = "Xml"
    def __init__(self, msgType, data):
        self._type = msgType
        self._data = data

    def getType(self):
        return self._type
        
    def setType(self, msgType):
        self._type = msgType

    def getData (self):
        return self._data

    def setData (self, data):
        self_data = data

    def __str__(self):
        return str(self._type) + "\n" + str(self._data)
    def __len__(self):
        return len(str(self))

class NetworkHandler(threading.Thread):
    """A class to handle sending and receiving of raw information packets. 
    Protocol for sending and receiving looks like:

        <number of bytes in data>\n
        <data>
    """
    def __init__(self, data_q, resp_q, sock, addr):
        """Set up thread object.
            data_q : queue to put data received into
            resp_q : queue to read responses from
            sock : socket of active connection
            addr : socket address of active connection
        """
        threading.Thread.__init__(self)
        self.sock = sock
        self.addr = addr
        self.recv_queue = data_q
        self.resp_queue = resp_q
    def run(self):
        """Perform the network management loop forever.
            1) Wait on the socket for data
            2) Put data into receive queue
            3) Wait on response queue for data
            4) Send response data back on socket
            5) Repeat
            See note about protocol in __init__
        """
        try:
            print "Connected by %s" % (str(self.addr))
            buf = ''
            infp = self.sock.makefile()
            #length = struct.unpack(infp.read(4))
            #print "Reading %s bytes" % (length)
            length = int(infp.readline())

            buf = infp.read(length)
            print "Read %s bytes" % (length)
            self.recv_queue.put(buf)

            #self.resp_queue.put("Finished receiving %s" % (time.time()))

            response = self.resp_queue.get()
            response = str(len(response)) + "\n" + str(response)
            print "Sending... on %s" % (str(self.sock))
            #response = "Finished receiving %s" % (time.time())
            print "NetworkHandler: sending %s" % (response[:300])
            sent = self.sock.send(response)
            print "NetworkHandler: successfully sent %s bytes" % (sent)
            self.resp_queue.task_done()
        finally:
            self.sock.shutdown(socket.SHUT_RDWR)
            self.sock.close()
    

class Printer(threading.Thread):
    def __init__(self, queue):
        threading.Thread.__init__(self)
        self.queue = queue
    def run(self):
        while True:
            result = self.queue.get()
            print result
            self.queue.task_done()


class FilePrinter(Printer):
    def __init__(self, queue, filename = ""):
        Printer.__init__(self, queue)
        self.fname = filename
    def run(self):
        while True:
            result = self.queue.get()
            print "Printing result (%s) " % (len(result))
            try:
                #fp = open(self.fname, "wb")

                fp, fname = tempfile.mkstemp(suffix = '.jpg', dir="./received")
                print "Saving to %s" % (fname)
                fp = os.fdopen(fp, 'w+b')
                fp.write(result)
                fp.close()
            except Exception as e:
                print "Error:, file not written. %s" % (e)
            finally:
                self.queue.task_done()





class ServerThread(threading.Thread):
    """Thread class to manage incoming connections and spawn off receive/response threads"""
    def __init__(self, host = '', port = 30000):
        """Constructor. Sets up the a response queue and a request queue for external use.
            host: default hostname to use for server
            port: port to listen on
        """
        threading.Thread.__init__(self)
        self.daemon = True
        self.host = host
        self.port = port
        self.request_queue = Queue.Queue()
        self.response_queue = Queue.Queue()
        self.sock = None

    def getRequestQueue(self):
        "Returns the queue used to receive data from connected clients"
        return self.request_queue

    def getResponseQueue(self):
        "Returns the queue used to send response data back to clients"
        return self.response_queue

    def run(self):
        """Receives new connections forever.
            1) Listen for connection
            2) On new connection spawn new network handler thread for that connection
            3) Repeat
        """
        self.sock = sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        while True:
            try:
                sock.bind( ( self.host, self.port ) )
                print "Server listening on port %s" % (self.port)
                break
            except Exception as e:
                print e
                time.sleep(1)

        try:
            sock.listen(1)
            while True:
                conn, addr = sock.accept()

                nThread = NetworkHandler(self.request_queue, self.response_queue, conn, addr)
                nThread.daemon=True
                nThread.start()
        except Exception as e:
            print "Server error: %s" % (e)
            raise e
        finally:
            self.finish()

    def finish(self):
        if self.sock is not None:
            self.sock.close()
        
        
if __name__ == "__main__":
    HOST = ''
    PORT = 30000
    if len(sys.argv) < 2:
        print "Usage: %s <filename>" % (sys.argv[0])
        exit(1)

    sThread = ServerThread()
    sThread.start()
    print "Server Thread started"
    time.sleep(0.5)

    cThread = ClientThread(sys.argv[1])
    cThread.start()
    #print "Client Thread Started"

    try:
        sThread.join(3000)
        print "Thread Joined"
    except KeyboardInterrupt as e:
        print "Main thread: %s" % (e)
        sThread.finish()
        raise e
