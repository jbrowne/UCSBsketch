from pyjamas import DOM 
from pyjamas.ui import Event
from pyjamas.Canvas import Color
from pyjamas.ui.RootPanel import RootPanel
from pyjamas.Canvas.GWTCanvas import GWTCanvas
from pyjamas.ui.HorizontalPanel import HorizontalPanel

class CanvasTest(object):
   def __init__(self):
      self.canvas = GWTCanvas(coordX = 400, coordY= 400, pixelX = 400, pixelY = 400)
      self.canvas.addStyleName("gwt-canvas")
      DOM.sinkEvents(self.canvas.getElement(), Event.MOUSEEVENTS)
      #DOM.setEventListener(self.canvas.getElement(), self)

      self.canvas.setFillStyle(Color.Color(255, 0, 0))
      self.canvas.fillRect(4,4,10,10)

      self._dragging = False
      #Register for canvas mouse events


      RootPanel().add(self.canvas)

   def onBrowserEvent(self, event):
      print "Event happened"
      kind = DOM.eventGetType(event)
      x = DOM.eventGetClientX(event) - DOM.getAbsoluteLeft(self.canvas.getElement())
      y = DOM.eventGetClientY(event) - DOM.getAbsoluteTop(self.canvas.getElement())
      print "Type of event: %s" % (kind)
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

   def onMouseDrag(self, x, y):
      print "Mouse dragging"

   def onMouseUp(self, x, y):
      print "Mouseup"

if __name__ == '__main__':
   CanvasTest()
