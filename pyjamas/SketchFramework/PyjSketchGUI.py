from SketchFramework.SketchGUI import _SketchGUI
from SketchFramework.Stroke import Stroke
from SketchFramework.Point import Point
from SketchFramework.Board import BoardSingleton, _Board

from Utils import Logger
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

class _PyjSketchGUI(_SketchGUI):
   def __init__(self, *args, **kargs):
      self.BoardCanvas = _BoardCanvas()
      self.BoardCanvas.setCallback_AddStroke(lambda pl: self._addStroke(pl))
      self._Board = BoardSingleton()

   def _addStroke(self, pointlist):
      "A callback function for the board canvas to send its points to"
      logger.debug(pointlist)
      newStroke = Stroke(points = pointlist)
      logger.debug("Adding begun")
      self._Board.AddStroke( newStroke )
      logger.debug( "Done adding")
      

   def getBoardCanvasElement(self):
      "Returns the BoardCanvas element that needs to be added to the DOM to actually interact with a user."
      return self.BoardCanvas

class _BoardCanvas(Canvas):
   def __init__(self):
      self.p = self._proc
      self._dragging = False
      Canvas.__init__(self, Width=WIDTH, Height=HEIGHT)
      canvasElement = self.getElement()
      #Register for canvas mouse events
      self._proc = Processing(DOM.getFirstChild(canvasElement))
      self._proc.setup = self.setup_proc
      self._proc.draw = self.redraw
      self._proc.init()

      DOM.sinkEvents(canvasElement, Event.MOUSEEVENTS)
      DOM.setEventListener(canvasElement, self)

      self._currentPointList = []

      self._x = None
      self._y = None
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
   def redraw(self):
      pass
   def clear_board(self):
      self._proc.background(255)


   def onMouseDown(self, x, y):
      self._x = x
      self._y = y
      self.drawCircle(x,y,radius=1)

      self._currentPointList.append(Point(x,y))

   def onMouseDrag(self, x, y):
      self.drawLine(self._x, self._y, x, y)
      self._x = x
      self._y = y
      self.drawCircle(x,y,radius=1)
      self._currentPointList.append(Point(x,y))

   def onMouseUp(self, x, y):
      self.drawLine(self._x, self._y, x, y)
      self._x = None
      self._y = None

      self._callback_AddStroke(self._currentPointList)
      self._currentPointList = []

   def setCallback_AddStroke(self, function):
      self._callback_AddStroke = function
   def setCallback_DeleteStroke(self, function):
      self._callback_DeleteStroke = function

   def drawLine(self, x1, y1, x2, y2, width=2, color="#000000"):
      _y1 = HEIGHT - y1
      _y2 = HEIGHT - y2
      self._proc.line(x1,_y1,x2,_y2)
   
   def drawCircle(self, x, y, radius=1, color="#000000", fill="", width=1.0):
      _y = HEIGHT - y
      self._proc.ellipse(x,_y,radius, radius)
   def drawText (self, x, y, InText="", size=10, color="#000000"):
      pass


def run():
   GUI = _PyjSketchGUI()
   RootPanel().add(GUI.getBoardCanvasElement())
   

      
if __name__ == '__main__':
   run()
