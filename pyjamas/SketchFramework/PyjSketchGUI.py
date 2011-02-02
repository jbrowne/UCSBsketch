from SketchFramework.SketchGUI import _SketchGUI
from SketchFramework.Stroke import Stroke
from SketchFramework.Point import Point
from SketchFramework.Board import BoardSingleton, _Board

from Utils import Logger
from Utils.Hacks import type
from pyjamas.Canvas2D import Canvas
from pyjamas.ui.RootPanel import RootPanel
from pyjamas.ui import Event
from pyjamas.ui.MouseListener import MouseHandler
from pyjamas import DOM 
from pyjamas import Window

import math

from __pyjamas__ import jsinclude
jsinclude("javascript/processing.js")
from __javascript__ import Processing


logger = Logger.getLogger('PyjSketchGUI', Logger.DEBUG)

WIDTH = 1024
HEIGHT = 768 

_Singleton = None

def SketchGUISingleton():
   global _Singleton
   if _Singleton is None:
      _Singleton = _PyjSketchGUI()
   return _Singleton


class _PyjSketchGUI(_SketchGUI):
   def __init__(self, *args, **kargs):
      self._Board = BoardSingleton()
      self.BoardCanvas = _BoardCanvas()
      self.BoardCanvas.setCallback_AddStroke(lambda pl: self._addStroke(pl))
      self.BoardCanvas.setCallback_Redraw( (lambda: self._redraw()))

   def _addStroke(self, pointlist):
      "A callback function for the board canvas to send its points to"
      newStroke = Stroke(points = pointlist)
      self._Board.AddStroke( newStroke )

   def _redraw(self):
      b = self._Board
      logger.debug("BO's: %s\n AO's: %s\n SO's: %s" % (b.BoardObservers, b.AnnoObservers.values(), b.StrokeObservers))
      for obs in b.BoardObservers:
         obs.drawMyself()
      for s in b.Strokes:
         s.drawMyself()
      

   def getBoardCanvasElement(self):
      "Returns the BoardCanvas element that needs to be added to the DOM to actually interact with a user."
      return self.BoardCanvas

   def drawCircle(self, x, y, radius=1, color="#000000", fill="", width=1.0):
      "Draw a circle on the canvas at (x,y) with radius rad. Color should be 24 bit RGB string #RRGGBB. Empty string is transparent"
      self.BoardCanvas.drawCircle(x,y,radius=radius,  color=color, fill=fill, width=width)
     
     
      
   def drawLine(self, x1, y1, x2, y2, width=2, color="#000000"):
      "Draw a line on the canvas from (x1,y1) to (x2,y2). Color should be 24 bit RGB string #RRGGBB"
      self.BoardCanvas.drawLine(x1,y1,x2,y2, width=width, color=color)
      
   def drawText (self, x, y, InText="", size=10, color="#000000"):
      "Draw some text (InText) on the canvas at (x,y). Color as defined by 24 bit RGB string #RRGGBB"
      self.BoardCanvas.drawText(x,y,InText=InText, size = size, color=color)

class _BoardCanvas(Canvas):
   def __init__(self):
      self._dragging = False
      Canvas.__init__(self, Width=WIDTH, Height=HEIGHT)
      canvasElement = self.getElement()
      #Register for canvas mouse events
      self._proc = Processing(DOM.getFirstChild(canvasElement))
      self._proc.setup = (lambda: self.setup_proc())
      self._proc.draw = None
      self._proc.init()

      DOM.sinkEvents(canvasElement, Event.MOUSEEVENTS)
      DOM.setEventListener(canvasElement, self)

      self._currentPointList = []

      self._x = None
      self._y = None

      self._callback_Redraw = None
      self._callback_AddStroke = None
      self._callback_DeleteStroke = None
      
   def onBrowserEvent(self, event):
      kind = DOM.eventGetType(event)
      x = DOM.eventGetClientX(event) - DOM.getAbsoluteLeft(self.getElement())
      y = DOM.eventGetClientY(event) - DOM.getAbsoluteTop(self.getElement())
      y = HEIGHT - y
      if kind == "mousedown":
         self.onMouseDown(x,y)
         self._dragging = True
      elif kind == "mousemove" and self._dragging:
         self.onMouseDrag(x,y)
      elif (kind == "mouseup" or kind == "mouseout") and self._dragging:
         self._dragging = False
         self.onMouseUp(x,y)

   def setup_proc(self):
      self._proc.size(WIDTH,HEIGHT)
      self._proc.background(255)
      self._proc.stroke("#000000")
      self._proc.smooth()
   def redraw(self):
      if self._callback_Redraw is not None:
         self.clear_board()
         self._callback_Redraw()
   def clear_board(self):
      self._proc.background(255)


   def onMouseDown(self, x, y):
      self._x = x
      self._y = y
      #self.drawCircle(x,y,radius=1)

      self._currentPointList.append(Point(x,y))

   def onMouseDrag(self, x, y):
      self.drawLine(self._x, self._y, x, y)
      self._x = x
      self._y = y
      #self.drawCircle(x,y,radius=1)
      self._currentPointList.append(Point(x,y))

   def onMouseUp(self, x, y):
      self.drawLine(self._x, self._y, x, y)
      self._x = None
      self._y = None

      if self._callback_AddStroke is not None:
         self._callback_AddStroke(self._currentPointList)
      if self._callback_Redraw is not None:
         self._callback_Redraw()
      self._currentPointList = []

   def setCallback_AddStroke(self, function):
      self._callback_AddStroke = function
   def setCallback_DeleteStroke(self, function):
      self._callback_DeleteStroke = function
   def setCallback_Redraw(self, function):
      self._callback_Redraw = function

   def drawLine(self, x1, y1, x2, y2, width=2, color="#000000"):
      _y1 = HEIGHT - y1
      _y2 = HEIGHT - y2
      self._proc.stroke(color)
      self._proc.strokeWeight(width)
      self._proc.line(x1,_y1,x2,_y2)
      #self._proc.stroke("#000000")
   
   def drawCircle(self, x, y, radius=1, color="#000000", fill="", width=1.0):
      "Draw a circle on the canvas at (x,y) with radius rad. Color should be 24 bit RGB string #RRGGBB. Empty string is transparent"
      _y = HEIGHT - y
      self._proc.stroke(color)
      self._proc.strokeWeight(width)
      if fill == "":
         self._proc.noFill()
      else:
         self._proc.fill(fill)
      self._proc.ellipse(x,_y,2*radius, 2*radius)
      #self._proc.stroke("#000000")

   def drawText (self, x, y, InText="", size=10, color="#000000"):
      logger.debug("drawing text '%s' at %s, %s" % (InText, x,y))
      self._proc.fill(color)
      _y = HEIGHT - y
      self._proc.text(InText, x, _y)


def run():
   GUI = SketchGUISingleton()
   RootPanel().add(GUI.getBoardCanvasElement())
   

      
if __name__ == '__main__':
   run()
