#!/usr/bin/env python
"""
filename: NetSketchGUI.py

Description:
   This class should control all interface matters. It must export:
       TkSketchGUISingleton
       TkSketchGUI (Class)
          drawLine
          drawCircle
          drawText
   All other functions and interface behavior is up to the GUI designer.
   This implementation listens for MouseDown events and builds strokes to hand off
      to the board system. Upon any event, Redraw is called globally to fetch all 
      board paint objects and display them.
Todo:
   It would be nice if the interface weren't so directly tied to the Tkinter underpinnings.
   I.e., TkSketchGUI is essentially a Tkinter frame object, and must be manipulated similarly.
"""


import pdb
import time
import threading
import Queue
import StringIO
import Image

from xml.etree import ElementTree as ET

from SketchFramework.SketchGUI import _SketchGUI
from SketchFramework.Point import Point
from SketchFramework.Stroke import Stroke
from SketchFramework.Board import BoardSingleton
from SketchFramework.NetworkReceiver import ServerThread
from SketchFramework.strokeout import imageBufferToStrokes, GETNORMWIDTH

from Observers import CircleObserver
from Observers import ArrowObserver
from Observers import DebugObserver
from Observers import TextObserver
from Observers import DiGraphObserver
from Observers import TuringMachineObserver


from Utils.StrokeStorage import StrokeStorage
from Utils import Logger

from Observers.ObserverBase import Animator

# Constants
WIDTH = 1024
HEIGHT = 3 * WIDTH / 4

MID_W = WIDTH/2
MID_H = HEIGHT/2

   
logger = Logger.getLogger("NetSketchGUI", Logger.DEBUG)



class FileResponseThread(threading.Thread):
    def __init__(self, inQ, outQ, filename = "xmlout.xml"):
        threading.Thread.__init__(self)
        self.daemon = True
        self.fname = filename
        self.inQ = inQ
        self.outQ = outQ


    def run(self):
       while True:
            image = self.inQ.get()
            logger.debug("Received data")
            fp = open(self.fname, "r")
            try:
                output = fp.read()
                self.outQ.put(output)
            except Exception as e:
                print e
            finally:
                fp.close()


 

class DummyGUI(_SketchGUI):

    Singleton = None
    def __init__(self):

       # Private data members
       self._serverThread = None
       self._dummyProcThread = None
       self._setupImageServer()


       self.run()
        


    def _setupImageServer(self):
        "Set up the server thread to start listening for image data, which it puts into its response queue. Then the imgprocthread converts image data to strokes, which are enqueued in self._strokeQueue"
        self._serverThread = ServerThread(port = 30000)
        img_recv_queue = self._serverThread.getRequestQueue()
        self._xmlResponseQueue = self._serverThread.getResponseQueue()

        self._fileResponseThread = FileResponseThread(img_recv_queue, self._xmlResponseQueue)
        self._fileResponseThread.start()

        self._serverThread.start()


    def run(self):
        while True:
            time.sleep(100)

            

if __name__ == "__main__":
    DummyGUI()
