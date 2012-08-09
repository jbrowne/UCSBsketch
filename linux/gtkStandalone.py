#!/usr/bin/env python

# example helloworld2.py

from SketchFramework.SketchGUI import _SketchGUI
from SketchFramework.Point import Point
from SketchFramework.Curve import CubicCurve
from SketchFramework.Stroke import Stroke
from SketchFramework.Board import Board

from Utils.GeomUtils import *

import Config

import cairo
import pangocairo
import pdb
import pygtk
import math
pygtk.require('2.0')
import gtk
HEIGHT = 1280
WIDTH = 720

class DrawGUI (_SketchGUI, gtk.DrawingArea):

    def __init__(self):
        # Create a new window
        gtk.DrawingArea.__init__(self)
        self.resize(WIDTH, HEIGHT)

        #Cairo drawing data
        self.context = None

        #Semantic board data
        self.board = Board(gui = self)
        self.strokeList = []
        Config.initializeBoard(self.board)

        #Event hooks
        self.connect("button_press_event", self.onMouseDown)
        self.connect("motion_notify_event", self.onMouseMove)
        self.connect("button_release_event", self.onMouseUp)
        self.set_events(gtk.gdk.BUTTON_RELEASE_MASK | 
                        gtk.gdk.BUTTON_PRESS_MASK |
                        gtk.gdk.POINTER_MOTION_MASK )
        self.connect("expose_event", self.onExpose)

        #GUI data variables
        self.isMouseDown1 = False
        self.isMouseDown3 = False
        self.currentPoints = []


    def getContext(self):
        return self.window.cairo_create()


    def resize(self, w,h):
        """Set the size of the canvas to w x h"""
        self.set_size_request(h, w)

    def onMouseDown(self, widget, e):
        """Respond to a mouse being pressed"""
        if e.button == 1:
            self.isMouseDown1 = True
            self.context = self.getContext()
            self.currentPoints.append(self.b2c(Point(e.x, e.y)))
        elif e.button == 3:
            self.isMouseDown3 = True
            self.context = self.getContext()
            self.currentPoints.append(self.b2c(Point(e.x, e.y)))

    def onMouseMove(self, widget, e):
        """Respond to the mouse moving"""
        if self.isMouseDown1:
            p = self.currentPoints[-1]
            curPt = self.b2c(Point(e.x, e.y))
            self.currentPoints.append(curPt)
            self.context = self.getContext()
            self.drawLine(p.X, p.Y, curPt.X, curPt.Y, color="#ffffff")
        elif self.isMouseDown3:
            p = self.currentPoints[-1]
            curPt = self.b2c(Point(e.x, e.y))
            self.currentPoints.append(curPt)
            self.context = self.getContext()
            self.drawLine(p.X, p.Y, curPt.X, curPt.Y, color="#0ccccc")
    
    def onMouseUp(self, widget, e):
        """Respond to the mouse being released"""
        if e.button == 1:
            self.isMouseDown1 = False
            curPt = self.b2c(Point(e.x, e.y))
            self.currentPoints.append(curPt)
            stroke = Stroke( self.currentPoints)
            self.currentPoints = []
            self.strokeList.append(stroke)
            self.board.AddStroke(stroke)
            self.draw()
        elif e.button == 3:
            self.isMouseDown3 = False
            curPt = self.b2c(Point(e.x, e.y))
            self.currentPoints.append(curPt)
            stroke = Stroke( self.currentPoints)
            self.currentPoints = []
            for stk in list(self.strokeList):
                if len(getStrokesIntersection(stroke, stk) ) > 0:
                    self.board.RemoveStroke(stk)
                    self.strokeList.remove(stk)
            self.draw()

    def onExpose(self, widget, e):
        """Respond to the window being uncovered"""
        #self.context = self.getContext()
        #rect = self.get_allocation()
        ## set a clip region for the expose e
        #self.context.rectangle(e.area.x, e.area.y,
        #                       e.area.width, e.area.height)
        #self.context.clip()
        self.draw()
        return False

    def clearBoard(self, bgColor="#000000"):
        """Erase the contents of the board"""
        self.context.save()
        c = hexToTuple(bgColor)
        self.context.set_source_rgb(*c)
        rect = self.get_allocation()
        self.context.rectangle(rect.x, rect.y, rect.width, rect.height)
        self.context.fill()
        self.context.restore()
        
    def draw(self):
        """Draw the board"""
        self.context = self.getContext()
        self.clearBoard()
        for stk in self.board.Strokes:
            stk.drawMyself()
        for obs in self.board.BoardObservers:
            obs.drawMyself()

    def drawCircle(self, x, y, radius=1, color="#FFFFFF", fill="", width=1.0):
        """Draw a circle on the canvas at (x,y) with radius rad. Color should be
        24 bit RGB string #RRGGBB. Empty string is transparent"""
        self.context.save()
        #Draw the line
        c = hexToTuple(color)
        self.context.set_source_rgb(*c)
        pt = self.b2c(Point(x,y))
        self.context.arc(pt.X, pt.Y, radius, 0, math.pi * 2)
        self.context.stroke()
        self.context.restore()
         
    def drawLine(self, x1, y1, x2, y2, width=2, color="#FFFFFF"):
        """Draw a line on the canvas from (x1,y1) to (x2,y2). Color should be 24
        bit RGB string #RRGGBB"""
        print x1, y1, x2, y2
        self.context.save()
        #Draw the line
        c = hexToTuple(color)
        print c
        self.context.set_source_rgb(*c)
        p1 = self.b2c(Point(x1, y1))
        p2 = self.b2c(Point(x2, y2))
        print p1, p2
        self.context.move_to( p1.X, p1.Y )
        self.context.line_to( p2.X, p2.Y )
        self.context.stroke()
        self.context.restore()
         
    def drawText (self, x, y, InText="", size=10, color="#FFFFFF"):
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
    def drawBox(self, tl, br, topright = None, 
                bottomleft = None, color="#FFFFFF", width=2):
        self.context.save()
        tl = self.b2c(tl)
        br = self.b2c(br)

        x = tl.X
        y = tl.Y

        w = br.X - tl.X
        h = br.Y - tl.Y

        c = hexToTuple(color)
        self.context.set_source_rgb(*c)
        self.context.rectangle(x,y,w,h)
        self.context.stroke()
        self.context.restore()
    
    def drawStroke(self, stroke, width = 2, color="#FFFFFF", erasable = False):
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
        

    def b2c(self, pt):
        """Converts bottom-left origin Board coordinates to raw canvas coords
        and back"""
        rect = self.get_allocation()
        return Point(pt.X, rect.height - pt.Y)

def hexToTuple(hexString):
    """Converts a 24-bit hex string, e.g. #ff0010, to a tuple
        of ints, e.g. (255, 0, 16)"""
    retTuple = ( float(int(hexString[1:3], 16))/255.0,
                 float(int(hexString[3:5], 16))/255.0,
                 float(int(hexString[5:7], 16))/255.0 )
    return retTuple


def main():
    window = gtk.Window()
    board = DrawGUI()

    window.add(board)
    window.connect("destroy", gtk.main_quit)
    window.show_all()

    gtk.main()
if __name__ == "__main__":
    main()
