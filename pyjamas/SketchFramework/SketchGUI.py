#!/usr/bin/python
"""
filename: SketchGUI.py

Description:
   This class should control all interface matters. It must export:
       SketchGUISingleton
       SketchGUI (Class)
          drawLine
          drawCircle
          drawText
   All other functions and interface behavior is up to the GUI designer.
   This implementation listens for MouseDown events and builds strokes to hand off
      to the board system. Upon any event, Redraw is called globally to fetch all 
      board paint objects and display them.
"""
HEIGHT = 800
WIDTH = 1280
from Point import Point
from Utils.Hacks import type

from Utils import Logger
#from SketchFramework.Stroke import Stroke
#from SketchFramework.Board import BoardSingleton
#from SketchSystem import initialize, standAloneMain

logger = Logger.getLogger("SketchGUI", Logger.DEBUG)
class _SketchGUI(object):
    HEIGHT = 800
    WIDTH = 1280
    """The base GUI class. 
    Class must implement drawText, drawLine and drawCircle. X-Y origin is bottom-left corner.
    Aside from these restrictions, interface options (reset board, etc) are up to the GUI programmer."""
    Singleton = None
    def getDimensions(self):
        "Returns (Height, Width) in pixels of the sketch GUI canvas"
        return _SketchGUI.WIDTH, _SketchGUI.HEIGHT
    def __init__(self):
        raise NotImplemented

    def drawCircle(self, x, y, radius=1, color="#000000", fill="", width=1.0):
        "Draw a circle on the canvas at (x,y) with radius rad. Color should be 24 bit RGB string #RRGGBB. Empty string is transparent"
        logger.debug("drawCircle")
        raise NotImplemented
        
        
         
    def drawLine(self, x1, y1, x2, y2, width=2, color="#000000"):
        "Draw a line on the canvas from (x1,y1) to (x2,y2). Color should be 24 bit RGB string #RRGGBB"
        logger.debug("drawLine")
        raise NotImplemented
         
    def drawText (self, x, y, InText="", size=10, color="#000000"):
        "Draw some text (InText) on the canvas at (x,y). Color as defined by 24 bit RGB string #RRGGBB"
        logger.debug("drawText")
        raise NotImplemented
        
# ------------------------------------------------
#      Optional overloads
    def drawBox(self, topleft, bottomright, topright = None, bottomleft = None, color="#000000", width=2):
        if topright is None:
            topright = Point(bottomright.X, topleft.Y)
        if bottomleft is None:
            bottomleft = Point(topleft.X, bottomright.Y)
        self.drawLine(topleft.X, topleft.Y, topright.X, topright.Y, color=color, width=width)
        self.drawLine(topright.X, topright.Y, bottomright.X, bottomright.Y, color=color, width=width)
        self.drawLine(bottomright.X, bottomright.Y, bottomleft.X, bottomleft.Y, color=color, width=width)
        self.drawLine(bottomleft.X, bottomleft.Y, topleft.X, topleft.Y, color=color, width=width)
    
    def drawStroke(self, stroke, width = 2, color="#000000", erasable = False):
        prev_p = None
        for next_p in stroke.Points:
            if prev_p is not None:
                self.drawLine(prev_p.X, prev_p.Y, next_p.X, next_p.Y, width=width, color=color)
            prev_p = next_p
    def Subtest(self):
       print "I am NOT a PyjSketchGUI"
    
def SketchGUISingleton():
    "Returns the GUI instance we're currently working with."
    #from SketchFramework import WpfSketchGUI as GuiInstance
    from SketchFramework import PyjSketchGUI as GuiInstance
    return GuiInstance.SketchGUISingleton()
    
    



def drawCircle (x, y, radius=1, color="#000000", fill="", width=1.0):
    s = SketchGUISingleton()
    s.drawCircle(x,y,radius=radius,  color=color, fill=fill, width=width)

def drawText (x, y, InText="", size=10, color="#000000"):
    s = SketchGUISingleton()
    s.drawText(x,y,InText=InText, size = size, color=color)

def drawLine(x1, y1, x2, y2, width=2, color="#000000"):
    s = SketchGUISingleton()
    s.drawLine(x1,y1,x2,y2, width=width, color=color)
    
def drawBox(topleft, bottomright, topright = None, bottomleft = None, color="#000000", width=2):
    s = SketchGUISingleton()
    s.drawBox(topleft, bottomright, topright = topright, bottomleft = bottomleft, color=color, width=width)
    
def drawStroke(stroke, width = 2, color="#000000", erasable = False):
    s = SketchGUISingleton()
    s.drawStroke(stroke, width = width, color = color, erasable = erasable)
   
def getDimensions():
    s = SketchGUISingleton()
    return s.getDimensions()

