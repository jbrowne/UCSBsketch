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
      self._dragging = False
      Canvas.__init__(self, Width=WIDTH, Height=HEIGHT)
      #Register for canvas mouse events
      DOM.sinkEvents(self.getElement(), Event.MOUSEEVENTS)
      DOM.setEventListener(self.getElement(), self)


      self._currentPointList = []

   def onBrowserEvent(self, event):
      kind = DOM.eventGetType(event)
      x = DOM.eventGetClientX(event) - DOM.getAbsoluteLeft(self.getElement())
      y = DOM.eventGetClientY(event) - DOM.getAbsoluteTop(self.getElement())
      if kind == "mousedown":
         self._dragging = True
         self.onMouseDown(x,y)
      elif kind == "mousemove" and self._dragging:
         self.onMouseDrag(x,y)
      elif (kind == "mouseup" or kind == "mouseout") and self._dragging:
         self._dragging = False
         self.onMouseUp(x,y)

   def onMousedown(self, x, y):
      print "Mousedown"
      self._currentPointList.append(Point(x,y))

   def onMouseDrag(self, x, y):
      #print "Mouse dragging"
      self._currentPointList.append(Point(x,y))

   def onMouseUp(self, x, y):
      print "Mouseup"
      self._callback_AddStroke(self._currentPointList)
      self._currentPointList = []

   def setCallback_AddStroke(self, function):
      self._callback_AddStroke = function
   def setCallback_DeleteStroke(self, function):
      self._callback_DeleteStroke = function

   def drawLine(self, x1, y1, x2, y2):
      


def run():
   GUI = _PyjSketchGUI()
   RootPanel().add(GUI.getBoardCanvasElement())
   

      
if __name__ == '__main__':
   run()
