#!/usr/bin/env python

# example helloworld2.py

from SketchFramework.SketchGUI import _SketchGUI
from SketchFramework.Point import Point
from SketchFramework.Curve import CubicCurve
from SketchFramework.Stroke import Stroke
from SketchFramework.Board import Board

from Utils import Logger
from Utils.GeomUtils import *
from Utils.StrokeStorage import StrokeStorage
from sketchvision import ImageStrokeConverter

import Config
from functools import partial

import threading
import Queue
from multiprocessing import Queue as ProcQueue, Process
import gobject
import cairo
import pangocairo
import pdb
import pygtk
import math
pygtk.require('2.0')
import gtk
WIDTH, HEIGHT = 1024, 768


log = Logger.getLogger("GTK-GUI", Logger.WARN)
def processImage(image, strokeQueue, scaleDims):
    """This function will extract strokes
    from an image file. It will add the extracted strokes from
    the image to strokeQueue, scaled according to scaleDims"""
    pruneLen = 10
    width, height = scaleDims
    log.debug("Process spawned")
    try:
        strokeDict = ImageStrokeConverter.cvimgToStrokes(image)
    except Exception as e:
        raise

    strokes = strokeDict['strokes']
    w,h = strokeDict['dims']
    scale_x = width / float(w)
    scale_y = height / float(h)
    log.debug( "Got %s Strokes" % (len(strokes)) )
    for s in strokes:
        if len(s.points) > pruneLen:
            pointList = []
            for x,y in s.points:
                newPoint = Point(scale_x * x, height - (scale_y *y))
                pointList.append(newPoint)
            newStroke = Stroke(pointList)
            strokeQueue.put(newStroke)

class GTKGui (_SketchGUI, gtk.DrawingArea):
    def __init__(self, dims = (WIDTH, HEIGHT) ):
        # Create a new window
        gtk.DrawingArea.__init__(self)
        self.resize(*dims)# BREAKS when X forwarding

        #Semantic board data
        self.board = Board(gui = self)
        self.strokeList = []
        Config.initializeBoard(self.board)
        self.boardProcThread = BoardThread(self.board)

        #GUI data variables
        self.isMouseDown1 = False
        self.isMouseDown3 = False
        self.keyCallbacks = {}
        self.currentPoints = []
        self.opQueue = Queue.Queue()
        self.strokeQueue = ProcQueue()
        self.strokeLoader = StrokeStorage()
        self.screenImage = None
        self._pixbuf = None
        self._isFullscreen = False
        #Cairo drawing data
        self.renderBuffer = None
        self.context = None 
        self.resetBackBuffer()


        #Event hooks
        gobject.idle_add(self.processOps) #Idle event
        gobject.idle_add(self.processQueuedStrokes) #Async stroke processing
        self.set_property("can-focus", True) #So we can capture keyboard events
        self.connect("button_press_event", self.onMouseDown)
        self.connect("motion_notify_event", self.onMouseMove)
        self.connect("button_release_event", self.onMouseUp)
        self.connect("key_press_event", self.onKeyPress)
        self.connect("expose_event", self.onExpose)
        self.set_events(gtk.gdk.BUTTON_RELEASE_MASK | 
                        gtk.gdk.BUTTON_PRESS_MASK |
                        gtk.gdk.KEY_PRESS_MASK |
                        gtk.gdk.EXPOSURE_MASK |
                        gtk.gdk.POINTER_MOTION_MASK )

        #Enable the board processing
        self.boardProcThread.start()


    def getDimensions(self):
        "Return the (width, height) of the visible board area"
        return self.window.get_size()

    def post(self, op):
        self.opQueue.put(op)

    def registerKeyCallback(self, keyVal, function):
        """Register a function to be called when
        a certain keyVal is pressed"""
        log.debug("Registered function for %s" % (keyVal))
        self.keyCallbacks.setdefault(keyVal, []).append(function)

    def onKeyPress(self, widget, event, data=None):
        key = chr(event.keyval % 256)
        if key == 'r':
            self.resetBoard()
        elif key == 'i':
            def ok_callback(fileSelector):
                fname = fileSelector.get_filename()
                fileSelector.destroy()
                self.loadStrokesFromImage(filename=fname)

            fileSelector = gtk.FileSelection("Choose a photo")
            fileSelector.set_filename("./photos/")

            fileSelector.ok_button.connect("clicked", 
                                      (lambda w: ok_callback(fileSelector)) )
            fileSelector.cancel_button.connect("clicked", 
                                      (lambda w: fileSelector.destroy()) )
                                      
            fileSelector.show()
        elif key == 'l':
            self.loadStrokes()
        elif key == 's':
            self.saveStrokes()
        elif key == 'f':
            self.setFullscreen(not self._isFullscreen)
        elif key == 'q':
            exit(0)

        #Run the registered callbacks
        for func in self.keyCallbacks.get(key, ()):
            func()

    def resetBackBuffer(self):
        """Reset the back painting buffer, for example when the screen
        size changes"""
        x,y,w,h = self.allocation
        log.debug("Reset back buffer %sx%s" % (w,h))
        self.renderBuffer = cairo.ImageSurface(cairo.FORMAT_ARGB32, w,h)
        self.context = cairo.Context(self.renderBuffer)
        #self.screenImage = None

        
    def setFullscreen(self, makeFull):
        """Set the application fullscreen according to makeFull(boolean)"""
        win = gtk.window_list_toplevels()[0]
        self._pixbuf = None
        if makeFull:
            self.screenImage = None
            self._isFullscreen = True
            print ""
            log.debug("Fullscreen")
            win.fullscreen()
            self.opQueue.put(lambda : self._updateScreenImage())
            self.opQueue.put(lambda : self.resetBackBuffer())
            #self.resetBackBuffer()
            #self.boardChanged()
        else:
            self.screenImage = None
            self._isFullscreen = False
            log.debug("UNFullscreen")
            win.unfullscreen()
            self.opQueue.put(lambda : self.resetBackBuffer())
            #self.resetBackBuffer()
            #self.boardChanged()

    def resetBoard(self):
        self.opQueue = Queue.Queue()
        self.board = Board(gui = self)
        Config.initializeBoard(self.board)
        self.boardProcThread = BoardThread(self.board)
        self.boardProcThread.start()
        self.draw()

    def boardChanged(self):
        self.draw()
        #self.opQueue.put(partial(GTKGui.draw, self))

    def loadStrokesFromImage(self, filename=None, image=None):
        pruneLen = 1
        width, height = self.window.get_size()
        if image is None:
            if filename is None:
                return
            else:
                image = ImageStrokeConverter.loadFile(filename)

        p = Process(target = processImage,
                    args = (image, self.strokeQueue, (width,height) )
                   )
        p.start()
 
    def loadStrokes(self):
        for stroke in self.strokeLoader.loadStrokes():
            self.addStroke(stroke)
           # op = partial(GTKGui.addStroke, self, stroke)
           # self.opQueue.put(op)

    def saveStrokes(self):
        self.strokeLoader.saveStrokes(self.strokeList)


    def drawCircle(self, *args, **kargs):
        """Draw a circle on the canvas at (x,y) with radius rad. Color should be
        24 bit RGB string #RRGGBB. Empty string is transparent"""
        op = partial(GTKGui._drawCircle, self, *args, **kargs)
        self.opQueue.put(op)

    def drawText(self, *args, **kargs):
        """Draw some text (InText) on the canvas at (x,y). Color as defined by 24
        bit RGB string #RRGGBB"""
        op = partial(GTKGui._drawText, self, *args, **kargs)
        self.opQueue.put(op)

    def drawLine(self, *args, **kargs):
        """Draw a line on the canvas from (x1,y1) to (x2,y2). Color should be 24
        bit RGB string #RRGGBB"""
        op = partial(GTKGui._drawLine, self, *args, **kargs)
        self.opQueue.put(op)

    def drawStroke(self, *args, **kargs):
        """Draw a stroke on the board with width and color as specified."""
        op = partial(GTKGui._drawStroke, self, *args, **kargs)
        self.opQueue.put(op)

    def drawCurve(self, *args, **kargs):
        "Draw a curve on the board with width and color as specified"
        op = partial(GTKGui._drawCurve, self, *args, **kargs)
        self.opQueue.put(op)

    def drawBox(self, *args, **kargs):
        op = partial(GTKGui._drawBox, self, *args, **kargs)
        self.opQueue.put(op)

    #________________________________________
    #  Private, actual draw calls
    #________________________________________

    def _drawCircle(self, x, y, radius=1, color="#FFFFFF", fill="", width=1.0):
        """Draw a circle on the canvas at (x,y) with radius rad. Color should be
        24 bit RGB string #RRGGBB. Empty string is transparent"""
        self.context.save()
        #Draw the line
        pt = self.b2c(Point(x,y))
        self.context.arc(pt.X, pt.Y, radius, 0, math.pi * 2)
        if fill != "":
            self.context.set_source_rgb(* hexToTuple(fill) )
            self.context.fill_preserve()
        #c = hexToTuple(color)
        self.context.set_source_rgb(*hexToTuple(color))
        self.context.stroke()
        self.context.restore()
         
    def _drawLine(self, x1, y1, x2, y2, width=2, color="#FFFFFF", _context=None):
        """Draw a line on the canvas from (x1,y1) to (x2,y2). Color should be 24
        bit RGB string #RRGGBB"""
        if _context is None:
            context = self.context
        else:
            context = _context

        context.save()
        #Draw the line
        c = hexToTuple(color)
        context.set_source_rgb(*c)
        p1 = self.b2c(Point(x1, y1))
        p2 = self.b2c(Point(x2, y2))
        context.move_to( p1.X, p1.Y )
        context.line_to( p2.X, p2.Y )
        context.stroke()
        context.restore()
         
    def _drawText (self, x, y, InText="", size=10, color="#FFFFFF"):
        """Draw some text (InText) on the canvas at (x,y). Color as defined by 24
        bit RGB string #RRGGBB"""
        self.context.save()
        ctxt = pangocairo.CairoContext(self.context)
        layout = ctxt.create_layout()
        layout.set_text(InText)
        c = hexToTuple(color)
        self.context.set_source_rgb(*c)
        _, (tlx, tly, brx, bry) = layout.get_pixel_extents()
        pt = Point(x, y)
        #pt = self.b2c(Point(x, y - bry))
        pt = self.b2c(pt)
        ctxt.translate(pt.X, pt.Y)
        ctxt.show_layout(layout)
        self.context.restore()

    # ------------------------------------------------
    #      Optional overloads
    def _drawBox(self, tl, br, topright = None, 
                bottomleft = None, color="#FFFFFF", fill = "", width=2):
        self.context.save()
        tl = self.b2c(tl)
        br = self.b2c(br)

        x = tl.X
        y = tl.Y
        w = br.X - tl.X
        h = br.Y - tl.Y

        self.context.set_source_rgb(* hexToTuple(color))
        self.context.set_line_width(width)
        self.context.rectangle(x,y,w,h)
        if fill != "":
            self.context.set_source_rgb(* hexToTuple(fill))
            self.context.fill_preserve()
        self.context.stroke()
        self.context.restore()
    
    def _drawStroke(self, stroke, width = 2, color="#FFFFFF", erasable = False):
        """Draw a stroke on the board with width and color as specified."""
        self.context.save()
        #Draw the lines
        c = hexToTuple(color)
        self.context.set_source_rgb(*c)
        if len(stroke.Points) > 0:
            pt = self.b2c(stroke.Points[0])
            self.context.move_to( pt.X, pt.Y )
            if len(stroke.Points) > 1:
                for pt in stroke.Points[1:]:
                    pt = self.b2c(pt)
                    self.context.line_to( pt.X, pt.Y)
                self.context.stroke()
            else:
                #Draw a dot or something
                pass
        self.context.restore()
        
    #def drawCurve(self, curve, width = 2, color = "#FFFFFF"):
    #    "Draw a curve on the board with width and color as specified"

    def _getContext(self):
        return self.window.cairo_create()

    def resize(self, w,h):
        """Set the size of the canvas to w x h"""
        self.set_size_request(w,h)

    def processQueuedStrokes(self):
        if not self.strokeQueue.empty():
            log.debug("Adding queued stroke")
            stroke = self.strokeQueue.get()
            self.strokeList.append(stroke)
            self.boardProcThread.addStroke(stroke, callback = self.boardChanged)
        return True

    def processOps(self):
        """Process one operation from the opqueue"""
        if not self.opQueue.empty():
            op = self.opQueue.get() #Call the next operation in the queue
            op()
            self.opQueue.task_done()
        return True #Call me again next idle time

    def onMouseDown(self, widget, e):
        """Respond to a mouse being pressed"""
        if e.button == 1:
            self.isMouseDown1 = True
            self.currentPoints.append(self.b2c(Point(e.x, e.y)))
            return True
        elif e.button == 3:
            self.isMouseDown3 = True
            self.currentPoints.append(self.b2c(Point(e.x, e.y)))
            return True

    def onMouseMove(self, widget, e):
        """Respond to the mouse moving"""
        if self.isMouseDown1:
            p = self.currentPoints[-1]
            curPt = self.b2c(Point(e.x, e.y))
            self.currentPoints.append(curPt)
            liveContext = self._getContext()
            self._drawLine(p.X, p.Y, curPt.X, curPt.Y, 
                            color="#ffffff", _context= liveContext)
            return True
        elif self.isMouseDown3:
            p = self.currentPoints[-1]
            curPt = self.b2c(Point(e.x, e.y))
            self.currentPoints.append(curPt)
            liveContext = self._getContext()
            self._drawLine(p.X, p.Y, curPt.X, curPt.Y, 
                            color="#c00c0c", _context = liveContext)
            return True
    
    def onMouseUp(self, widget, e):
        """Respond to the mouse being released"""
        if e.button == 1:
            self.isMouseDown1 = False
            curPt = self.b2c(Point(e.x, e.y))
            self.currentPoints.append(curPt)
            stroke = Stroke( self.currentPoints)
            self.currentPoints = []
            self.addStroke(stroke)
            #self.opQueue.put(partial(GTKGui.addStroke, self, stroke))
            #self.draw()
            return True
        elif e.button == 3:
            self.isMouseDown3 = False
            curPt = self.b2c(Point(e.x, e.y))
            self.currentPoints.append(curPt)
            stroke = Stroke( self.currentPoints)
            self.currentPoints = []
            shouldRedraw = True
            for stk in list(self.strokeList):
                if len(getStrokesIntersection(stroke, stk) ) > 0:
                    self.eraseStroke(stk)
                    shouldRedraw = False
            if shouldRedraw:
                #pass
                self.draw()
            return True

    def addStroke(self, stroke):
        """Add as stroke to the board and our local bookkeeping"""
        self.strokeList.append(stroke)
        self.boardProcThread.addStroke(stroke, callback = self.boardChanged)

    def eraseStroke(self, stroke):
        """Remove a stroke from the board and our local lists"""
        self.strokeList.remove(stroke)
        self.boardProcThread.removeStroke(stroke, callback = self.boardChanged)
        

    def onExpose(self, widget, e):
        """Respond to the window being uncovered"""
        log.debug("Expose")
        if self.screenImage is not None:
            self.window.draw_pixbuf(None, self.screenImage, 0,0, 0,0)
        else:
            self.draw()

    def clearBoard(self, bgColor="#000000"):
        """Erase the contents of the board"""
        log.debug("Clear")
        self.context.save()
        c = hexToTuple(bgColor)
        self.context.set_source_rgb(*c)
        rect = self.get_allocation()
        self.context.rectangle(rect.x, rect.y, rect.width, rect.height)
        self.context.fill()
        self.context.restore()
        
    def draw(self):
        """Draw the board"""
        log.debug("Redraw")
        self.opQueue.put(partial(GTKGui.clearBoard, self))
        with self.board.Lock:
            for stk in self.board.Strokes:
                stk.drawMyself()
            for obs in self.board.BoardObservers:
                obs.drawMyself()
        self.doPaint()

    def doPaint(self):
        """A method to commit the current queue of draw events to 
        the screen"""
        self.opQueue.put(partial( GTKGui.flipContext, self) )
        self.opQueue.put(partial( GTKGui._updateScreenImage, self) )
        
    def flipContext(self):
        """Render the drawn surface to the screen"""
        log.debug("Flip image to surface")
        bufferToPaint = self.renderBuffer
        (nw, nh) = bufferToPaint.get_width(), bufferToPaint.get_height()
        log.debug(" Current buffer: %sx%s" % (nw, nh) )
        #Set up a new buffer to paint from
        self.resetBackBuffer()
        #Paint the render buffer to the live context
        liveContext = self._getContext()
        liveContext.set_source_surface(bufferToPaint)
        liveContext.paint()


    def _updateScreenImage(self):
        """Update the image of the screen we're dealing with"""
        log.debug("Update Screenshot")
        #if not self._isFullscreen:
        width, height = self.window.get_size()
        #if self._pixbuf is None:
        log.debug("  pixbuf size: %sx%s" % (width, height))
        _pixbuf = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, False, 8,
                                width, height)
        self.screenImage = _pixbuf.get_from_drawable(self.window, 
                                        self.window.get_colormap(), 
                                        0, 0, 0, 0, width, height)
        self.screenImage.save('screenshot.png', 'png')

        

    def b2c(self, pt):
        """Converts bottom-left origin Board coordinates to raw canvas coords
        and back"""
        rect = self.get_allocation()
        return Point(pt.X, rect.height - pt.Y)


class BoardThread(threading.Thread):
    def __init__(self, board):
        threading.Thread.__init__(self)
        self.daemon = True
        self.board = board
        self.qlock = threading.RLock()
        self.opQueue = Queue.Queue()
        self.running = True

    def stop(self):
        self.running = False

    def setQueue(self, queue):
        with self.qlock:
            self.opQueue = queue
    def getQueue(self):
        return self.opQueue

    def addStroke(self, stroke, callback = (lambda : 0)):
        op = partial(Board.AddStroke, self.board, stroke)
        self.opQueue.put( (op, callback,) )

    def removeStroke(self, stroke, callback = (lambda : 0)):
        op = partial(Board.RemoveStroke, self.board, stroke)
        self.opQueue.put( (op, callback,) )

    def run(self):
        while self.running:
            if not self.opQueue.empty():
                op, callback = self.opQueue.get()
                with self.board.Lock:
                    op()
                self.opQueue.task_done()
                callback()
            else:
                time.sleep(0.3)
        log.debug("Board thread quitting")
        


def hexToTuple(hexString):
    """Converts a 24-bit hex string, e.g. #ff0010, to a tuple
        of ints, e.g. (255, 0, 16)"""
    retTuple = ( float(int(hexString[1:3], 16))/255.0,
                 float(int(hexString[3:5], 16))/255.0,
                 float(int(hexString[5:7], 16))/255.0 )
    return retTuple

def main():
    window = gtk.Window()
    board = GTKGui()

    window.add(board)
    window.connect("destroy", gtk.main_quit)
    window.show_all()

    gtk.main()
if __name__ == "__main__":
    main()
