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

   This implementation hosts a server on port 30000 to listen for incoming picture data.
   The photo is then processed to extract the strokes, strokes are added to the board, and
   the system responds to the client with an xml description of the board's state.
"""


import pdb
import time
import threading
import Queue
import StringIO
import Image
import traceback

from xml.etree import ElementTree as ET

from SketchFramework.SketchGUI import _SketchGUI
from SketchFramework.Point import Point
from SketchFramework.Stroke import Stroke
from SketchFramework.Board import Board
from SketchFramework.NetworkReceiver import ServerThread, Message

from Observers import CircleObserver
from Observers import ArrowObserver
from Observers import DebugObserver
from Observers import TextObserver
from Observers import DiGraphObserver
from Observers import TuringMachineObserver
from Observers import RubineObserver


from sketchvision.ImageStrokeConverter import imageBufferToStrokes, GETNORMWIDTH
from Utils.StrokeStorage import StrokeStorage
from Utils import Logger

from Observers.ObserverBase import Animator

# Constants
WIDTH = 1024
HEIGHT = int(4.8 * WIDTH / 8)

MID_W = WIDTH/2
MID_H = HEIGHT/2

   
logger = Logger.getLogger("NetSketchGUI", Logger.DEBUG)


class DrawAction(object):
    "Base class for a draw action"
    def __init__(self, action_type):
        self.action_type = action_type
    def xml(self):
        raise NotImplemented

class DrawCircle(DrawAction):
    "An object that defines parameters for drawing a circle"
    def __init__(self, x, y, radius, color, fill, width):
        DrawAction.__init__(self, "Circle")
        self.x = x
        self.y = y
        self.radius = radius
        self.color = color
        self.fill = fill
        self.width = width

        self._hash = None

    def __hash__(self):
        if self._hash is None:
            self._hash = 0
            for member in [self.action_type, 
                           self.x, self.y, 
                           self.radius, 
                           self.color, 
                           self.fill, 
                           self.width]:
                self._hash = hash(self._hash + hash(member))
        return self._hash

    def xml(self):
        "Returns an ElementTree of this object"
        root = ET.Element(self.action_type)
        x = ET.SubElement(root, "x")
        x.text = str(self.x)

        y = ET.SubElement(root, "y")
        y.text = str(self.y)

        radius = ET.SubElement(root, "radius")
        radius.text = str(self.radius)

        color = ET.SubElement(root, "color")
        color.text = str(self.color)

        fill = ET.SubElement(root, "fill")
        fill.text = str(self.fill)

        width = ET.SubElement(root, "width")
        width.text = str(self.width)

        return root


class DrawStroke(DrawAction):
    "An object defining the parameters to draw a stroke"
    def __init__(self, stroke, width, color):
        DrawAction.__init__(self, "Stroke")
        self.stroke = stroke
        self.width = width
        self.color = color

    def xml(self):
        "Returns an ElementTree of this object"
        root = ET.Element(self.action_type)

        root.attrib['id'] = str(self.stroke.id)
        root.attrib['color'] = str(self.color)
        root.attrib['width'] = str(self.width)

        for i, pt in enumerate(self.stroke.Points):
            pt_el = ET.SubElement(root, "p")
            
            #pt_el.attrib['id'] = str(i)
            pt_el.attrib['x'] = str(pt.X)
            pt_el.attrib['y'] = str(pt.Y)

        return root

class DrawLine(DrawAction):
    "An object defining the parameters to draw a Line"
    def __init__(self, x1, y1, x2, y2, width, color):
        DrawAction.__init__(self, "Line")
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2

        self.width = width
        self.color = color

        self._hash = None

    def __hash__(self):
        if self._hash is None:
            self._hash = 0
            for member in [self.action_type, 
                           self.x1, self.y1, 
                           self.x2, self.y2, 
                           self.color, 
                           self.width]:
                self._hash = hash(self._hash + hash(member))
        return self._hash 

    def xml(self):
        "Returns an ElementTree of this object"
        root = ET.Element(self.action_type)
        x = ET.SubElement(root, "x1")
        x.text = str(self.x1)

        y = ET.SubElement(root, "y1")
        y.text = str(self.y1)

        x = ET.SubElement(root, "x2")
        x.text = str(self.x2)

        y = ET.SubElement(root, "y2")
        y.text = str(self.y2)

        color = ET.SubElement(root, "color")
        color.text = str(self.color)

        width = ET.SubElement(root, "width")
        width.text = str(self.width)

        return root

class DrawText(DrawAction):
    "An object defining parameters to draw a string of text"
    def __init__(self, x, y, text, size, color):
        DrawAction.__init__(self, "Text")
        self.x = x
        self.y = y
        self.text = text
        self.size = size
        self.color = color

        self._hash = None

    def __hash__(self):
        if self._hash is None:
            self._hash = 0
            for member in [self.action_type, 
                           self.x, self.y, 
                           self.text,
                           self.size,
                           self.color]:
                self._hash = hash(self._hash + hash(member))
        return self._hash 

    def xml(self):
        "Returns an ElementTree of this object"
        root = ET.Element(self.action_type)
        x = ET.SubElement(root, "x")
        x.text = str(self.x)

        y = ET.SubElement(root, "y")
        y.text = str(self.y)

        text_el = ET.SubElement(root, "text")
        text_el.text = str(self.text)

        color = ET.SubElement(root, "color")
        color.text = str(self.color)

        size = ET.SubElement(root, "size")
        size.text = str(self.size)

        return root
        
class SketchResponseThread(threading.Thread):
    """A Thread that handles the different requests sent for network interaction with the board"""
    def __init__(self, recv_q, send_q):
        """Set up everything for receiving and sending messages.
            recv_q: the Queue for pulling data messages received from the client
            send_q: the Queue into which the appropriate responses to the client will be put
        """
        threading.Thread.__init__(self)
        self.daemon = True
        self._recv_q = recv_q
        self._send_q = send_q
        
        self._boards = {}
    def run(self):
        """Continually receive and handle requests from clients, and generate appropriate responses"""
        while True:
            in_msg = self._recv_q.get()
            logger.debug("Received something")
            if in_msg is not None:
                logger.debug("Message type %s" % (in_msg.getType))
                if in_msg.getType() == Message.TYPE_IMG:
                    logger.debug("Processing image")
                    xml_response = self.processNewImage(in_msg.getData())
                    fp = open("xmlout.xml", "w")
                    print >> fp, ET.tostring(xml_response)
                    fp.close()
                    respMsg = Message(Message.TYPE_XML, ET.tostring(xml_response))
                    self._send_q.put(respMsg)
                elif in_msg.getType() == Message.TYPE_XML:
                    logger.debug("Processing XML")
                    pass
                else:
                    logger.debug("Unknown message type")
            else:
                logger.debug("Invalid message type")
            self._recv_q.task_done()

    def processNewImage(self, imageData):
        """Take in image data, process iself._Boardt and return a string of the resulting board XML"""
        logger.debug("Processing net image")
        stkDict = imageBufferToStrokes(imageData)
        stks = stkDict['strokes']
        width, height = stkDict['dims']
        logger.debug("Processed net image, converting strokes")

        self.resetBoard()
        newBoard = self._Board
        self._boards[newBoard.getID()] = newBoard

        retXML = newBoard.xml(width, height)
        try:
            for stk in stks:
                pointList = []
                for x,y in stk.points:
                   #scale = WIDTH / float(GETNORMWIDTH())
                   pointList.append( Point(x, height - y) )
                newBoard.AddStroke(Stroke(pointList))

            retXML = newBoard.xml(width, height)
        except Exception as e:
            logger.error("ERROR: %s" % str(e))
            logger.error("%s" % traceback.format_exc())
        return retXML

    def resetBoard(self):
        "Clear all strokes and board observers from the board (logically and visually)"
        self._Board = Board()

        CircleObserver.CircleMarker(self._Board)
        #CircleObserver.CircleVisualizer(self._Board)
        ArrowObserver.ArrowMarker(self._Board)
        #ArrowObserver.ArrowVisualizer(self._Board)
        #LineObserver.LineMarker(self._Board)
        #LineObserver.LineVisualizer(self._Board)
        TextObserver.TextCollector(self._Board)
        TextObserver.TextVisualizer(self._Board)
        DiGraphObserver.DiGraphMarker(self._Board)
        #DiGraphObserver.DiGraphVisualizer(self._Board)
        #DiGraphObserver.DiGraphExporter(self._Board)
        TuringMachineObserver.TuringMachineCollector(self._Board)
        #TuringMachineObserver.TuringMachineVisualizer(self._Board)
        #TuringMachineObserver.TuringMachineExporter(self._Board)
        """
        
        #TemplateObserver.TemplateMarker(self._Board)
        #TemplateObserver.TemplateVisualizer(self._Board)
        
        RubineObserver.RubineMarker(self._Board, "RL10dash.xml", debug=True)
        
        d = DebugObserver.DebugObserver(self._Board)
        #d.trackAnnotation(TestAnimObserver.TestAnnotation)
        #d.trackAnnotation(MSAxesObserver.LabelMenuAnnotation)
        #d.trackAnnotation(MSAxesObserver.LegendAnnotation)
        #d.trackAnnotation(LineObserver.LineAnnotation)
        #d.trackAnnotation(ArrowObserver.ArrowAnnotation)
        #d.trackAnnotation(MSAxesObserver.AxesAnnotation)
        #d.trackAnnotation(TemplateObserver.TemplateAnnotation)
        #d.trackAnnotation(CircleObserver.CircleAnnotation)
        #d.trackAnnotation(RaceTrackObserver.RaceTrackAnnotation)
        #d.trackAnnotation(RaceTrackObserver.SplitStrokeAnnotation)
        
        #d.trackAnnotation(TuringMachineObserver.TuringMachineAnnotation)
        #d.trackAnnotation(DiGraphObserver.DiGraphAnnotation)
        #d.trackAnnotation(TextObserver.TextAnnotation)
        #d.trackAnnotation(BarAnnotation)
        """
        

    

class VisionServer(object):
    def __init__(self):
       # Private data members
       self._serverThread = None
       self._recv_q = None
       self._send_q = None
       self._netDispatchThread = None
       self._setupNetworkDispatcher()


    def _setupNetworkDispatcher(self):
        self._serverThread = ServerThread(port = 30000)
        self._recv_q = self._serverThread.getRequestQueue()
        self._send_q = self._serverThread.getResponseQueue()
        self._netDispatchThread = SketchResponseThread(self._recv_q, self._send_q)
        self._netDispatchThread.start()
        self._serverThread.start()

    def run(self):
        """Reset the board and wait for some entity to add strokes to the strokeQueue. 
        Add these strokes to the board, and build the xml view of the board, then queue the
        response to send back"""
        while True:
            action = raw_input()
            if action.strip().upper() == "C":
                self._serverThread.stop()
                self._serverThread.join()
                break
            else:
                print "unknown action"
            


def main():
    VisionServer().run()
    

if __name__ == "__main__":
    main()
