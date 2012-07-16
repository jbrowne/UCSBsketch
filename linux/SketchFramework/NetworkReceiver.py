#!/usr/bin/env python
"""
The network receiver works like this:
A single server thread starts and listens on the 
requisite port number. 
On a connection being accepted, it spawns a new
NetworkReceiver thread to handle the traffic for
the connection.
"""
import tempfile
import socket
import Queue
import sys
import time
import os
import threading
import StringIO
import pdb
import struct

from PIL import ImageFile

class Message:
    TYPE_IMG = "Img"
    TYPE_XML = "Xml"
    TYPE_INFO = "Info"

    @classmethod
    def parse(cls, inString):
        """Factory method that returns a message parsed from the string,
        or None if the string is poorly formatted"""
        retMsg = None
        strIO = StringIO.StringIO(inString)

        msgType = strIO.readline()
        dataString = inString[len(msgType):]
        msgType = msgType.rstrip()

        if msgType in [Message.TYPE_XML, Message.TYPE_IMG, Message.TYPE_INFO]:
            retMsg = Message(msgType, dataString)
        return retMsg

    def __init__(self, msgType, data):
        """Create a new message with type msgType, and data"""
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
            while True:
                print "Connected by %s" % (str(self.addr))
                buf = ''
                infp = self.sock.makefile()
                #length = struct.unpack(infp.read(4))
                #print "Reading %s bytes" % (length)
                lenstr = infp.readline()
                if  len(lenstr) > 0:
                    length = int(lenstr)

                    buf = infp.read(length)
                    print "Read %s bytes" % (length)
                    msg = Message.parse(buf)
                    self.recv_queue.put(msg)

                    #self.resp_queue.put("Finished receiving %s" % (time.time()))

                    response = self.resp_queue.get()
                    response = str(len(response)) + "\n" + str(response)
                    print "Sending... on %s" % (str(self.sock))
                    #response = "Finished receiving %s" % (time.time())
                    print "NetworkHandler: sending %s" % (response[:300])
                    sent = self.sock.send(response)
                    print "NetworkHandler: successfully sent %s bytes" % (sent)
                    self.resp_queue.task_done()
                else:
                    #Disconnected before more data received
                    break
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
        self.daemon = True
    def run(self):
        while True:
            msg = self.queue.get()
            print "Printing msg (%s) " % (len(msg))
            try:
                #fp = open(self.fname, "wb")

                fp, fname = tempfile.mkstemp(suffix = '.jpg', dir="./received")
                print "Saving to %s" % (fname)
                fp = os.fdopen(fp, 'w+b')
                fp.write(msg.getData())
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
        self._alive = True
        self.networkThreads = []

    def getRequestQueue(self):
        "Returns the queue used to receive data from connected clients"
        return self.request_queue

    def getResponseQueue(self):
        "Returns the queue used to send response data back to clients"
        return self.response_queue

    def stop(self):
        """Stop the server from listening"""
        print("Stopping thread")
        self._alive = False
        self.finish()

    def acceptConnection(self):
        """Accept a connection and spawn a receiver thread"""
        print "Accepting"
        conn, addr = self.sock.accept()
        print "Accepted"
        nThread = NetworkHandler(self.request_queue, self.response_queue, conn, addr)
        nThread.daemon=True
        self.networkThreads.append(nThread)
        nThread.start()
        
    def run(self):
        """Receives new connections forever.
            1) Listen for connection
            2) On new connection spawn new network handler thread for that connection
            3) Repeat
        """
        self.sock =  socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print "Binding"
        while self._alive:
            try:
                self.sock.bind( ( self.host, self.port ) )
                print "Server listening on port %s" % (self.port)
                break
            except Exception as e:
                #print e
                time.sleep(1)

        try:
            print "Listening"
            self.sock.listen(1)
            while self._alive:
                self.acceptConnection()
        except socket.error as e:
            print "Server error: %s:%s" % (type(e), e)
            #raise e

    def finish(self):
        print( "Closing socket" )
        if self.sock is not None:
            try:
                self.sock.shutdown(socket.SHUT_RD)
            except Exception as e:
                print e
            #self.sock.close()
        
        
if __name__ == "__main__":
    HOST = ''
    PORT = 30000
    #if len(sys.argv) < 2:
        #print "Usage: %s <filename>" % (sys.argv[0])
        #exit(1)

    sThread = ServerThread()
    print "Server Thread started"

    fpThread = FilePrinter(sThread.getRequestQueue())
    fpThread.start()
    sThread.start()

    try:
        sThread.join(3000)
        print "Thread Joined"
    except KeyboardInterrupt as e:
        print "Main thread: %s" % (e)
        sThread.finish()
        raise e
