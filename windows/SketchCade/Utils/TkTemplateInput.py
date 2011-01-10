#!/usr/bin/python

import time
import math
import pdb
from Utils import GeomUtils
import Stroke
from SketchFramework import Point

from Tkinter import *
from tkMessageBox import *


# Constants
TEMPLATE_FILE = "board_templates.dat"
TEMPLATE_SAMPLE = 64 #num points in a template

WIDTH = 800
HEIGHT = 600
MID_W = WIDTH/2
MID_H = HEIGHT/2

def scoreStroke(stroke, template):
    sNorm = GeomUtils.strokeNormalizeSpacing(stroke, TEMPLATE_SAMPLE)
    centr = GeomUtils.centroid(sNorm.Points)
    point_vect = []
    templ_vect = []
    for q in template:
       templ_vect.append(q.X)
       templ_vect.append(q.Y)
    for p in sNorm.Points:
       point_vect.append(p.X - centr.X)
       point_vect.append(p.Y - centr.Y)
    angularDist = GeomUtils.vectorDistance(point_vect, templ_vect)
    return angularDist

def loadTemplates(filename = TEMPLATE_FILE):
    print "Loading templates: %s" % filename
    try:
       fp = open(filename, "r")
    except:
       return
    
    templates = {}
    current_template = None 
    for line in fp.readlines():
       fields = line.split()
       if line.startswith("#TEMPLATE"):
           assert len(fields) == 2
           current_template = fields[1]
           templates[current_template] = []
       elif line.startswith("#END"):
           assert len(fields) == 2
           template_name = fields[1]
           assert current_template == template_name
           current_template = None 
       else:
           assert len(fields) == 2
           x = float(fields[0])
           y = float(fields[1])
           assert current_template is not None
           templates[current_template].append(Point.Point(x, y))
    return templates
          
           
def storeTemplate(normStroke, tag=None, filename = TEMPLATE_FILE, overwrite = False):
    print "Saving template %s to: %s" % (tag, filename)
    if overwrite:
       fp = open (filename, "w")
    else:
       fp = open (filename, "a")

    if type(tag) is str:
       print >> fp, "#TEMPLATE %s" % (tag)
       for p in normStroke.Points:
          print >> fp, "%s %s" % (p.X, p.Y)
       print >>fp, "#END %s" % (tag)
    fp.close()


class SketchGUI(Frame):
    def __init__(self, master = None, **kargs):
        "Set up the Tkinter GUI stuff as well as the board logic"
        global HEIGHT, WIDTH

        Frame.__init__(self, master, **kargs)
        self.pack()
        #Set up the GUI stuff

        self.drawMenuOptions = {}
        
        self.BoardCanvas= Canvas(self, width=WIDTH, height = HEIGHT, bg="white", bd=2)
        self.BoardCanvas.pack(side=BOTTOM)
        self.BoardCanvas.bind("<ButtonPress-1>", self.CanvasMouseDown)
        self.BoardCanvas.bind("<B1-Motion>", self.CanvasMouseDown)          
        self.BoardCanvas.bind("<ButtonRelease-1>", self.CanvasMouseUp)      




        
        self.CurrentPointList = []
        self.StrokeList = []
        self.templates = {}


        self.p_y = self.p_x = None

        #self.ResetBoard()
        self.MakeMenu()
        #LoadStrokes()
        #self.Redraw()

      
    def MakeMenu(self):
        "Reserve places in the menu for fun actions!"
        win = self.master 
        top_menu = Menu(win)
        win.config(menu=top_menu)
        
        self.object_menu = Menu(top_menu)
        #top_menu.bind("<ButtonPress-1>",(lambda e: self.RebuildObjectMenu()))
        #self.RebuildObjectMenu()
        top_menu.add_command(label="Reset Board", command = (lambda :self.Redraw()), underline=1 )
        top_menu.add_command(label="Load Templates", command = self.LoadTemplates, underline=1 )
        top_menu.add_command(label="Save Template", command = self.SaveTemplate, underline=1 )
        top_menu.add_command(label="Recognize Stroke", command = (lambda :self.Redraw()), underline=1 )
        top_menu.add_command(label="Input Stroke", command = (lambda : self.Redraw()), underline=1 )


    def InvertDraw(self, class_):
        "Essentially checkbox behavior for BoardObject.DrawAll variable"
        if hasattr(class_, "DrawAll"):
            class_.DrawAll = not class_.DrawAll
            self.Redraw()
 
    def CanvasMouseDown(self, event):
        "Draw a line connecting the points of a stroke as it is being drawn"
        
        x = event.x
        y = event.y
        #self.BoardCanvas.create_oval(x,y,x,y,activewidth="1", fill="black", outline = "black")
        
        if self.p_x != None and self.p_y != None:
            p_x = self.p_x
            p_y = self.p_y
            self.BoardCanvas.create_line(p_x, p_y, x ,y, fill = "black", width=2)

        x = float(event.x)
        y = float(HEIGHT - event.y)
        t = time.time()
        self.CurrentPointList.append(Point.Point(x,y,t))

        self.p_x = x
        self.p_y = HEIGHT - y
            
        
    def SaveTemplate(self, numSamples = TEMPLATE_SAMPLE):
        if len(self.StrokeList) > 0:
            last_stroke = self.StrokeList[-1]
            template_name = str(len(self.StrokeList))
            sNorm = GeomUtils.strokeNormalizeSpacing(last_stroke, numSamples)
            centroid = GeomUtils.centroid(sNorm.Points)
            sNorm = sNorm.translate(-1*centroid.X, -1 * centroid.Y)
            storeTemplate(sNorm, tag=template_name)

    def LoadTemplates(self):
        self.templates = loadTemplates()

    def CanvasMouseUp(self, event):
        "Finish the stroke and add it to the board"
        #start a new stroke
        new_stroke = Stroke.Stroke(self.CurrentPointList)
        self.StrokeList.append(new_stroke)
        self.CurrentPointList = []
        self.p_x = self.p_y = None

        for tag, templ in self.templates.items():
            print "Stroke to template %s: %s" % (tag, scoreStroke(new_stroke, templ))
        
    def Redraw(self):
        """Find all the strokes on the board, draw them, then iterate through every object and
            have it draw itself"""
        global HEIGHT, WIDTH
        self.BoardCanvas.delete(ALL)

    def drawPoint(self, point):
        self.drawCircle(point.X, point.Y, rad = 3)

    def drawCircle(self, x, y, rad=1, color="#000000", fill="", width=1.0):
         "Draw a circle on the canvas at (x,y) with radius rad. Color should be 24 bit RGB string #RRGGBB. Empty string is transparent"
         y = HEIGHT - y
         self.BoardCanvas.create_oval(x-rad,y-rad,x+rad,y+rad,width=width, fill=fill, outline = color)
    def drawLine(self, x1, y1, x2, y2, LineWidth=2, color="#000000"):
         "Draw a line on the canvas from (x1,y1) to (x2,y2). Color should be 24 bit RGB string #RRGGBB"
         y1 = HEIGHT - y1
         y2 = HEIGHT - y2
         self.BoardCanvas.create_line(x1, y1, x2 ,y2, fill = color, width=LineWidth)
    def drawText (self, x, y, InText="", size=10, color="#000000"):
        "Draw some text (InText) on the canvas at (x,y). Color as defined by 24 bit RGB string #RRGGBB"
        y = HEIGHT - y
        text_font = ("times", size, "")
        self.BoardCanvas.create_text(x,y,text = InText, fill = color, font = text_font, anchor=NW) 
    def drawStroke(self, stroke, LineWidth = 2, color="#000000"):
        prev_p = None
        for next_p in stroke.Points:
            if prev_p is not None:
                self.drawLine(prev_p.X, prev_p.Y, next_p.X, next_p.Y, LineWidth=LineWidth, color=color)
            prev_p = next_p



def GUIRun():
    root = Tk()
    root.title("Template Generator")
    app = SketchGUI(master = root)
    try:
    	while 1:
	    root.update_idletasks()
	    root.update()
    except TclError:
        pass
    #root.mainloop()

if __name__ == "__main__":
    GUIRun()



