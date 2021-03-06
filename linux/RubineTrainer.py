#!/usr/bin/python
"""
filename: TkSketchGUI.py

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
import Queue
import StringIO
import Image
import traceback
from Tkinter import *
from tkFileDialog import askopenfilename
from tkMessageBox import *

from sketchvision import ImageStrokeConverter
from SketchFramework.SketchGUI import _SketchGUI
from SketchFramework.Point import Point
from SketchFramework.Stroke import Stroke
from SketchFramework.Board import Board
from Utils.StrokeStorage import StrokeStorage
from Utils.GeomUtils import getStrokesIntersection, strokeContainsStroke, strokeSmooth, strokeLength, strokeApproximateCubicCurves
from Utils import Logger, DataManager, GeomUtils
from Utils import Rubine #import RubineClassifier, RubineFeatureSet, BCPFeatureSet, BCP_ShapeFeatureSet



# Constants
WIDTH = 1000
HEIGHT = 800
MID_W = WIDTH/2
MID_H = HEIGHT/2
   
FEATURESET = Rubine.BCPFeatureSet
logger = Logger.getLogger("TkSketchGUI", Logger.DEBUG)

def _initializeBoard(board):
    pass


#TODO: Wrapper for TSketchGUI because This inherits from frame and we can't just switch it to inherit from SketchGUI
class TkSketchFrame(Frame, _SketchGUI):
    """The base GUI class. 
    Class must implement drawText, drawLine and drawCircle. X-Y origin is bottom-left corner.
    Aside from these restrictions, interface options (reset board, etc) are up to the GUI programmer."""
    def __init__(self):
        "Set up the Tkinter GUI stuff as well as the board logic"
        global HEIGHT, WIDTH


        self.root = Tk()
        self.root.title("Sketchy/Scratch")
        Frame.__init__(self, self.root)
        self.pack()
        #Set up the GUI stuff

        self.drawMenuOptions = {}
        
        self.BoardCanvas= Canvas(self, width=WIDTH, height = HEIGHT, bg="white", bd=2)
        self.BoardCanvas.pack(side=BOTTOM)
        self.ClassNameEntry = Entry(self)
        self.ClassNameEntry['width'] = 30
        self.ClassNameEntry.pack(side=RIGHT)

        #Left click bindings
        self.BoardCanvas.bind("<ButtonPress-1>", self.CanvasMouseDown)
        self.BoardCanvas.bind("<B1-Motion>", self.CanvasMouseDown)          
        self.BoardCanvas.bind("<ButtonRelease-1>", self.CanvasMouseUp)      

        #Right click bindings
        self.BoardCanvas.bind("<ButtonPress-3>", self.CanvasRightMouseDown)
        self.BoardCanvas.bind("<B3-Motion>", self.CanvasRightMouseDown)          
        self.BoardCanvas.bind("<ButtonRelease-3>", self.CanvasRightMouseUp)      

        #Middle click bindings
        self.BoardCanvas.bind("<ButtonPress-2>", self.CanvasMiddleMouseDown)
        self.BoardCanvas.bind("<B2-Motion>", self.CanvasMiddleMouseDown)          
        self.BoardCanvas.bind("<ButtonRelease-2>", self.CanvasMiddleMouseUp)      
        self.MakeMenu()

        #Set up all the logical board stuff before displaying anything
        self.StrokeQueue = Queue.Queue()
        self.CurrentPointList = []
        self.StrokeList = []
        self.StrokeLoader = StrokeStorage()
        self.ResetBoard()
        self._strokeTrainer = Rubine.RubineClassifier(featureSet = FEATURESET(), debug = True)
        #self.NewTrainingClass()

        self.Redraw()

        self.run()

    def run(self):
       try:
           while 1:
               self.root.update()
               self.root.update_idletasks()
       except TclError:
           pass

      
    def MakeMenu(self):
        "Reserve places in the menu for fun actions!"
        win = self.master 
        top_menu = Menu(win)
        win.config(menu=top_menu)
        
        #self.object_menu = Menu(top_menu)
        #top_menu.add_cascade(label="ObjectMenu", menu=self.object_menu)

        top_menu.add_command(label="Reset Board", command = (lambda :self.ResetBoard() or self.Redraw()), underline=1 )
        top_menu.add_command(label="Load strokes.dat", command = (lambda : self.LoadStrokes() or self.Redraw()), underline=1 )
        top_menu.add_command(label="Save strokes.dat", command = (lambda : self.SaveStrokes()), underline=1 )
        top_menu.add_command(label="Undo Stroke", command = (lambda :self.RemoveLatestStroke() or self.Redraw()), underline=1 )
        top_menu.add_command(label="New Rubine Class", command = (lambda :self.NewTrainingClass() or self.Redraw()), underline=1 )
        top_menu.add_command(label="Train Class on Strokes", command = (lambda :self.TrainClassOnStrokes() or self.Redraw()), underline=1 )
        top_menu.add_command(label="Save Training Data", command = (lambda :self.SaveTrainingWeights() or self.Redraw()), underline=1 )
        top_menu.add_command(label="Strokes From Image", command = (lambda :self.LoadStrokesFromImage() or self.Redraw()), underline=1 )


    def TrainClassOnStrokes(self):
        if self.currentSymClass == None:
            logger.warn("Cannot train on strokes. You must choose a class first!")
            return
        for stroke in self.StrokeList:
            self._strokeTrainer.addStroke(stroke, self.currentSymClass)
            logger.debug("Added stroke to examples for %s" % (self.currentSymClass))
        self.StrokeList = []
        self.currentSymClass = None

    def NewTrainingClass(self):
        name = None
        if self.ClassNameEntry.get().strip() != "":
            name = self.ClassNameEntry.get().strip()

        name = self._strokeTrainer.newClass(name = name)
        self.currentSymClass = name
        print "Now training class %s" % (self.currentSymClass)
        self.ResetBoard()

    def SaveTrainingWeights(self):
        self._strokeTrainer.saveWeights("RubineData.xml")
        self.ResetBoard()

    def LoadStrokes(self):
      for stroke in self.StrokeLoader.loadStrokes():
         self.StrokeList.append(stroke)
        #self.object_menu = Menu(top_menu)
        #top_menu.add_cascade(label="ObjectMenu", menu=self.object_menu)

    def LoadStrokesFromImage(self):
        fname = askopenfilename(initialdir='./')
        if fname == "":
           return

        try:
           logger.debug( "Loading strokes...")
           strokes = ImageStrokeConverter.imageToStrokes(fname)
        except Exception as e:
           logger.debug( "Error importing strokes from image '%s':\n %s" % (fname, e))
           return
        logger.debug( "Loaded %s strokes from '%s'" % (len(strokes), fname))

        for s in strokes:
           newStroke = Stroke()
           for x,y in s.points:
              scale = WIDTH / float(1280)
              newPoint = Point(scale * x,HEIGHT - scale * y)
              newStroke.addPoint(newPoint)
           #self.Board.AddStroke(newStroke)
           self.StrokeList.append(newStroke)

    def SaveStrokes(self):
        self.StrokeLoader.saveStrokes(self.StrokeList)

    def RemoveLatestStroke(self):
        if len (self.StrokeList) > 0:
            stroke = self.StrokeList.pop()



    def ResetBoard(self):
        "Clear all strokes and board observers from the board (logically and visually)"
        self.p_x = self.p_y = None

        self.CurrentPointList = []
        self.StrokeList = []


                
    def CanvasMiddleMouseDown(self, event):
        x = event.x
        y = event.y
        #self.BoardCanvas.create_oval(x,y,x,y,activewidth="1", fill="black", outline = "black")
        
        if self.p_x != None and self.p_y != None:
            p_x = self.p_x
            p_y = self.p_y
            self.BoardCanvas.create_line(p_x, p_y, x ,y, fill = "blue", width=2)

        x = event.x
        y = HEIGHT - event.y
        t = time.time()
        self.CurrentPointList.append(Point(x,y,t))

        self.p_x = event.x
        self.p_y = event.y

    def CanvasMiddleMouseUp(self, event):
        self.CurrentPointList = []
        self.p_x = self.p_y = None
        self.Redraw()

    def CanvasRightMouseDown(self, event):
        x = event.x
        y = event.y
        
        if self.p_x != None and self.p_y != None:
            p_x = self.p_x
            p_y = self.p_y
            self.BoardCanvas.create_line(p_x, p_y, x ,y, fill = "gray", width=2)

        x = event.x
        y = HEIGHT - event.y
        t = time.time()
        self.CurrentPointList.append(Point(x,y,t))

        self.p_x = x
        self.p_y = HEIGHT - y

    def CanvasRightMouseUp(self, event):
        delStrokes = set([])
        if len(self.CurrentPointList) > 0:
            stroke = Stroke( self.CurrentPointList )#, smoothing=True )
            self.CurrentPointList = []
            for stk in list(self.StrokeList):
                if len(getStrokesIntersection(stroke, stk) ) > 0:
                    logger.debug( "Removing Stroke")
                    self.StrokeList.remove(stk)
        self.p_x = self.p_y = None
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

        x = event.x
        y = HEIGHT - event.y
        t = time.time()
        self.CurrentPointList.append(Point(x,y,t))

        self.p_x = x
        self.p_y = HEIGHT - y

    def AddCurrentStroke(self):
        try:
            if len(self.CurrentPointList) > 0:
                stroke = Stroke( self.CurrentPointList )#, smoothing=True )
                self.StrokeList.append(stroke)
                logger.debug("StrokeAdded Successfully")
        except Exception as e:
            print traceback.format_exc()
            print e
        finally:
            self.CurrentPointList = []
        
    def CanvasMouseUp(self, event):
        "Finish the stroke and add it to the board"
        #start a new stroke
        self.AddCurrentStroke()
        self.p_x = self.p_y = None
        self.Redraw()
        
    def Redraw(self):
        "Find all the strokes on the board, draw them, then iterate through every object and have it draw itself"
        global HEIGHT, WIDTH
        self.BoardCanvas.delete(ALL)
        strokes = self.StrokeList
        for s in strokes:
           self.drawStroke( strokeSmooth(s, width = max(int(strokeLength(s) * 0.01), 1) ))
           #for c in strokeApproximateCubicCurves(s):
               #self.drawCurve(c)

    def drawCircle(self, x, y, radius=1, color="#000000", fill="", width=1.0):
         "Draw a circle on the canvas at (x,y) with radius rad. Color should be 24 bit RGB string #RRGGBB. Empty string is transparent"
         y = HEIGHT - y
         self.BoardCanvas.create_oval(x-radius,y-radius,x+radius,y+radius,width=width, fill=fill, outline = color)
         
    def drawLine(self, x1, y1, x2, y2, width=2, color="#000000"):
         "Draw a line on the canvas from (x1,y1) to (x2,y2). Color should be 24 bit RGB string #RRGGBB"
         y1 = HEIGHT - y1
         y2 = HEIGHT - y2
         self.BoardCanvas.create_line(x1, y1, x2 ,y2, fill=color, width = width)

    def drawText (self, x, y, InText="", size=10, color="#000000"):
        "Draw some text (InText) on the canvas at (x,y). Color as defined by 24 bit RGB string #RRGGBB"
        y = HEIGHT - y
        text_font = ("times", size, "")
        self.BoardCanvas.create_text(x,y,text = InText, fill = color, font = text_font, anchor=NW) 
    def drawStroke(self, stroke, width = 2, color="#000000", erasable = False):
        prev = None
        for p in stroke.Points:
            if prev != None:
                self.drawLine(prev.X, prev.Y, p.X, p.Y, width= width, color = color)
            prev = p


    

if __name__ == "__main__":
    #Just start the GUI for the trainer
    import cPickle as pickle
    args = sys.argv
    if len(args) > 1:
        if args[1] == "batch" and len(args) > 2:
            if len(args) > 3:
                outfname = args[3]
            else:
                outfname = "RubineData.xml"
            trainFile = open(args[2], "r")
            trainer = Rubine.RubineClassifier(featureSet = FEATURESET())
            for line in trainFile.readlines():
                if line.startswith("#"):
                    continue
                name, strokeFname = line.strip().split()
                print "Training %s from %s" % (name, strokeFname)
                trainer.newClass (name = name)
                strokes = StrokeStorage(filename = strokeFname).loadStrokes()
                for stk in strokes:
                    try:
                        trainer.addStroke(stk, name)
                    except Exception as e:
                        print e
            print "Saving Weights to %s" % (outfname)
            #pickle.dump(trainer, open("trainer.dmp", "wb"))
            trainer.saveWeights(outfname)

        else:   
            print "Usage: %s batch <training_spec>" % (args[0])
            exit(1)

    else:
        TkSketchFrame()




