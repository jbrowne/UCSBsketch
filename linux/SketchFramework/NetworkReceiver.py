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


class NetworkHandler(threading.Thread):
    def __init__(self, data_q, sock, addr):
        threading.Thread.__init__(self)
        self.sock = sock
        self.addr = addr
        self.queue = data_q
    def run(self):
        try:
            print "Connected by %s" % (str(self.addr))
            buf = ''
            infp = self.sock.makefile()
            #length = struct.unpack(infp.read(4))
            #print "Reading %s bytes" % (length)
            length = int(infp.readline())

            buf = infp.read(length)
            print "Read %s bytes" % (length)
            """

            data = self.sock.recv(4096)
            while len(data) > 0: #not data.startswith('<quit>'):
                print "%s bytes received" % (len (data))
                print "___%s" % (data[:min(len(data), 10)])
                buf += data
                data = self.sock.recv(4096)
            """
            self.queue.put(buf)

            print "Sending... on %s" % (str(self.sock))
            response = "Finished receiving %s" % (time.time())
            self.sock.sendall(response)
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
                self.queue.task_done()
                fp.close()
            except Exception as e:
                print "Error:, file not written. %s" % (e)





class ServerThread(threading.Thread):
    def __init__(self, host = '', port = 30000):
        threading.Thread.__init__(self)
        self.daemon = True
        self.host = host
        self.port = port
        self.queue = Queue.Queue()
        self.sock = None

    def getResponseQueue(self):
        return self.queue

    def run(self):
        #pThread = FilePrinter(self.queue, filename="outfile.dat")
        #pThread.daemon = True
        #pThread.start()
            
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

                nThread = NetworkHandler(self.queue, conn, addr)
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
