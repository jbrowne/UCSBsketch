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
import threading
import Queue
import StringIO
import Image
from Tkinter import *
from tkFileDialog import askopenfilename
from tkMessageBox import *

from SketchFramework.SketchGUI import _SketchGUI
from SketchFramework.Point import Point
from SketchFramework.Curve import CubicCurve
from SketchFramework.Stroke import Stroke
from SketchFramework.Board import Board
from Utils.StrokeStorage import StrokeStorage
from Utils.GeomUtils import getStrokesIntersection, strokeContainsStroke, strokeApproximateCubicCurves
from Utils import GeomUtils
from Utils import Logger
from SketchFramework import ImageStrokeConverter

from Observers.ObserverBase import Animator


# Constants
WIDTH = 1000
HEIGHT = 800
MID_W = WIDTH/2
MID_H = HEIGHT/2
   
logger = Logger.getLogger("TkSketchGUI", Logger.DEBUG)

def _initializeBoard(board):
    """Board initialization code, conveniently placed at the beginning of the file for easy modification"""

    from Observers import DebugObserver
    from Observers import RubineObserver
    from Bin import BinObserver, EqualsObserver, PlusObserver, MinusObserver, DivideObserver, MultObserver, ExpressionObserver, EquationObserver, DirectedLine
    from Observers import NumberObserver

    from Observers import CircleObserver
    from Observers import ArrowObserver
    from Observers import DiGraphObserver
    from Observers import TuringMachineObserver
    from Observers import LineObserver
    from Observers import TextObserver
    """
    from Observers import RaceTrackObserver
    from Observers import TemplateObserver
    from Observers import TestAnimObserver
    """

    if board is not None:
        RubineObserver.RubineMarker(board, "RubineData.xml", debug=True)
        #RubineObserver.RubineVisualizer(board)

        CircleObserver.CircleMarker(board)
        #CircleObserver.CircleVisualizer(board)
        ArrowObserver.ArrowMarker(board)
        ArrowObserver.ArrowVisualizer(board)
        LineObserver.LineMarker(board)
        #LineObserver.LineVisualizer(board)
        TextObserver.TextCollector(board)
        TextObserver.TextVisualizer(board)
        DiGraphObserver.DiGraphMarker(board)
        DiGraphObserver.DiGraphVisualizer(board)
        DiGraphObserver.DiGraphExporter(board)
        TuringMachineObserver.TuringMachineCollector(board)
        TuringMachineObserver.TuringMachineExporter(board)
        TuringMachineObserver.TuringMachineVisualizer(board)

        """
        DirectedLine.DirectedLineMarker(board)

        NumberObserver.NumCollector(board)
        NumberObserver.NumVisualizer(board)

        #BinObserver.BinCollector(board)
        #BinObserver.BinVisualizer(board)
        EqualsObserver.EqualsMarker(board)
        EqualsObserver.EqualsVisualizer(board)
        PlusObserver.PlusMarker(board)
        PlusObserver.PlusVisualizer(board)
        MinusObserver.MinusMarker(board)
        MinusObserver.MinusVisualizer(board)
        DivideObserver.DivideMarker(board)
        DivideObserver.DivideVisualizer(board)
        MultObserver.MultMarker(board)
        MultObserver.MultVisualizer(board)
        ExpressionObserver.ExpressionObserver(board)
        ExpressionObserver.ExpressionVisualizer(board)
        #EquationObserver.EquationObserver(board)
        #EquationObserver.EquationVisualizer(board)


        TestAnimObserver.TestMarker()
        TestAnimObserver.TestAnimator(fps = 1 / 3.0)
        RaceTrackObserver.SplitStrokeMarker()
        RaceTrackObserver.SplitStrokeVisualizer()
        RaceTrackObserver.RaceTrackMarker()
        RaceTrackObserver.RaceTrackVisualizer()
        TemplateObserver.TemplateMarker()
        TemplateObserver.TemplateVisualizer()
        """
        
        
        d = DebugObserver.DebugObserver(board)
        """
        d.trackAnnotation(DiGraphObserver.DiGraphNodeAnnotation)
        d.trackAnnotation(TestAnimObserver.TestAnnotation)
        d.trackAnnotation(MSAxesObserver.LabelMenuAnnotation)
        d.trackAnnotation(MSAxesObserver.LegendAnnotation)
        d.trackAnnotation(LineObserver.LineAnnotation)
        d.trackAnnotation(ArrowObserver.ArrowAnnotation)
        d.trackAnnotation(MSAxesObserver.AxesAnnotation)
        d.trackAnnotation(TemplateObserver.TemplateAnnotation)
        d.trackAnnotation(CircleObserver.CircleAnnotation)
        d.trackAnnotation(RaceTrackObserver.RaceTrackAnnotation)
        d.trackAnnotation(RaceTrackObserver.SplitStrokeAnnotation)
        
        d.trackAnnotation(TuringMachineObserver.TuringMachineAnnotation)
        d.trackAnnotation(DiGraphObserver.DiGraphAnnotation)
        d.trackAnnotation(TextObserver.TextAnnotation)
        d.trackAnnotation(BarAnnotation)
        """


class ImgProcThread (threading.Thread):
    "A Thread that continually pulls image data from imgQ and puts the resulting strokes in strokeQ"
    def __init__(self, imgQ, strokeQ):
        threading.Thread.__init__(self)
        self.daemon = True

        self.img_queue = imgQ
        self.stk_queue = strokeQ
    def run(self):
        while True:
            image = StringIO.StringIO(self.img_queue.get())
            logger.debug("Processing net image")
            stks = imageBufferToStrokes(image)
            logger.debug("Processed net image, converting strokes")
            for stk in stks:
                newStroke = Stroke()
                for x,y in stk.points:
                   scale = WIDTH / float(1280)
                   newPoint = Point(scale * x,HEIGHT - scale * y)
                   newStroke.addPoint(newPoint)
                self.stk_queue.put(newStroke)


class AnnotationDialog:
    def __init__ (self, parent, anno_list):
        top = self.top = Toplevel(parent)
        Label (top, text="Choose an Annotation Type").pack()
        self.lbox = Listbox(top)
        self.lbox.bind("<Double-Button-1>", (lambda x: self.ok()) )
        self.lbox.pack()
        for entry in anno_list:
            self.lbox.insert(END, entry)

        b = Button(top, text="Cancel", command=self.cancel)
        b.pack(pady=5)
        self.data = None
    def ok(self):
        selected =  self.lbox.curselection()
        if len(selected) > 0:
            self.data = self.lbox.get(ACTIVE)
        self.top.destroy()
    def cancel(self):
        self.top.destroy()

#TODO: Wrapper for TSketchGUI because This inherits from frame and we can't just switch it to inherit from SketchGUI
class TkSketchFrame(Frame, _SketchGUI):
    """The base GUI class. 
    Class must implement drawText, drawLine and drawCircle. X-Y origin is bottom-left corner.
    Aside from these restrictions, interface options (reset board, etc) are up to the GUI programmer."""
    def __init__(self):
        "Set up the Tkinter GUI stuff as well as the board logic"
        global HEIGHT, WIDTH

        #Set up all the logical board stuff before displaying anything
        self.StrokeQueue = Queue.Queue()
        self.Board = None
        self.CurrentPointList = []
        self.StrokeList = []
        self.AnimatorDrawtimes = {} #A dictionary of Animator subclasses to the deadline for the next frame draw 
        self.StrokeLoader = StrokeStorage()
        #self.SetupImageServer()
        self.ResetBoard()

        self.root = Tk()
        self.root.title("Sketchy/Scratch")
        Frame.__init__(self, self.root)
        self.pack()
        #Set up the GUI stuff

        self.drawMenuOptions = {}
        
        self.BoardCanvas= Canvas(self, width=WIDTH, height = HEIGHT, bg="white", bd=2)
        self.BoardCanvas.pack(side=BOTTOM)
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
        self.Redraw()

        self.run()

    def run(self):
       try:
           while 1:
               self.root.update()
               self.AnimateFrame()
               self.AddQueuedStroke()
               self.root.update_idletasks()
       except TclError:
           pass

    def initBoardObservers( observers, debugAnnotations = None ):
        if observers is not None:
            for obs in observers:
                obs(self.Board)
      
    def MakeMenu(self):
        "Reserve places in the menu for fun actions!"
        win = self.master 
        top_menu = Menu(win)
        win.config(menu=top_menu)
        
        self.object_menu = Menu(top_menu)
        top_menu.bind("<ButtonPress-1>",(lambda e: self.RebuildObjectMenu()))
        self.RebuildObjectMenu()
        top_menu.add_cascade(label="ObjectMenu", menu=self.object_menu)

        top_menu.add_command(label="Reset Board", command = (lambda :self.ResetBoard() or self.Redraw()), underline=1 )
        top_menu.add_command(label="Load strokes.dat", command = (lambda : self.LoadStrokes() or self.Redraw()), underline=1 )
        top_menu.add_command(label="Save strokes.dat", command = (lambda : self.SaveStrokes()), underline=1 )
        top_menu.add_command(label="Undo Stroke", command = (lambda :self.RemoveLatestStroke() or self.Redraw()), underline=1 )
        top_menu.add_command(label="Strokes From Image", command = (lambda :self.LoadStrokesFromImage() or self.Redraw()), underline=1 )


    def AddQueuedStroke(self):
        #Only process one stroke per round
        if not self.StrokeQueue.empty():
            stk = self.StrokeQueue.get()
            logger.debug("Adding queued stroke %s" % (stk))
            self.Board.AddStroke(stk)
            self.StrokeList.append(stk)
            self.Redraw()
            self.StrokeQueue.task_done()

    def LoadStrokes(self):
      for stroke in self.StrokeLoader.loadStrokes():
         self.Board.AddStroke(stroke)
         self.StrokeList.append(stroke)

    def SaveStrokes(self):
      self.StrokeLoader.saveStrokes(self.StrokeList)
        
    def LoadStrokesFromImage(self):
        fname = askopenfilename(initialdir='/home/jbrowne/src/sketchvision/images/')
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
           self.Board.AddStroke(newStroke)
           self.StrokeList.append(newStroke)

    def RemoveLatestStroke(self):
        if len (self.StrokeList) > 0:
            stroke = self.StrokeList.pop()
            self.Board.RemoveStroke(stroke)

    def RebuildObjectMenu(self):
        "Search the board for existing objects, and add a menu entry to manipulate it (drawAll)"
        observers = self.Board.GetBoardObservers()
        draw_vars = {}
        for obs in observers:
            key = obs.__class__
            if key not in self.drawMenuOptions and hasattr(obs, "DrawAll"):
                draw_vars[key] = key.DrawAll
        
        for key, var in draw_vars.items():
            self.drawMenuOptions[key] = self.object_menu.add_command(label=key.__name__,command=(lambda class_=key: self.InvertDraw(class_)), underline = 0)

    def InvertDraw(self, class_):
        "Essentially checkbox behavior for BoardObserver.DrawAll variable"
        if hasattr(class_, "DrawAll"):
            class_.DrawAll = not class_.DrawAll
            self.Redraw()


    def InitializeBoard(self):
        """Initialize all of the board observers and register debugable annotations, etc."""
        _initializeBoard(self.Board)
            

    def ResetBoard(self):
        "Clear all strokes and board observers from the board (logically and visually)"
        self.p_x = self.p_y = None

        self.Board = Board(gui = self)
        self.InitializeBoard()
        self.RegisterAnimators()
        self.CurrentPointList = []
        self.StrokeList = []


    def RegisterAnimators(self):
        self.AnimatorDrawtimes = {}
        for obs in self.Board.BoardObservers:
            if Animator in type(obs).__mro__: #Check if it inherits from Animator
                logger.debug( "Registering %s as animator" % (obs))
                self.AnimatorDrawtimes[obs] = time.time()
                
                
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
        suggestStrokes = set()
        if len(self.CurrentPointList) > 0:
            containerStroke = Stroke( self.CurrentPointList )#, smoothing=True )
            for testStroke in self.Board.Strokes:
                if strokeContainsStroke(containerStroke, testStroke):
                    suggestStrokes.add(testStroke)
            if len(suggestStrokes) > 0:
                annoNameMap = dict( [(k.__name__, k) for k in self.Board.AnnoTargeters.keys() ] )
                d = AnnotationDialog(self, annoNameMap.keys())
                self.wait_window(d.top)
                if d.data is not None:
                    self.Board.SuggestAnnotation(annoNameMap[d.data], list(suggestStrokes))


        self.CurrentPointList = []
        self.p_x = self.p_y = None
        self.Redraw()

    def CanvasRightMouseDown(self, event):
        x = event.x
        y = event.y
        #self.BoardCanvas.create_oval(x,y,x,y,activewidth="1", fill="black", outline = "black")
        
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
                    self.Board.RemoveStroke(stk)
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
        if len(self.CurrentPointList) > 0:
            stroke = Stroke( self.CurrentPointList )#, smoothing=True )
            
            self.Board.AddStroke(stroke)
            self.StrokeList.append(stroke)
            self.CurrentPointList = []
            
        
    def CanvasMouseUp(self, event):
        "Finish the stroke and add it to the board"
        #start a new stroke
        self.AddCurrentStroke()
        self.p_x = self.p_y = None
        self.Redraw()

    """
    def SetupImageServer(self):
        self.serverThread = ServerThread(port = 30000)
        self.net_queue = self.serverThread.getResponseQueue()
        self.serverThread.start()
        self.imgProcThread = ImgProcThread(self.net_queue, self.StrokeQueue)
        self.imgProcThread.start()
    """

                
        

        
    def AnimateFrame(self):
        for obs, deadline in self.AnimatorDrawtimes.items():
            if deadline <= 1000 * time.time():
                obs.drawMyself()
                self.AnimatorDrawtimes[obs] = 1000 *( (1 / float(obs.fps)) + time.time() ) #Time the next frame

        
    def Redraw(self):
        "Find all the strokes on the board, draw them, then iterate through every object and have it draw itself"
        global HEIGHT, WIDTH
        self.BoardCanvas.delete(ALL)
        strokes = self.Board.Strokes
        observers = self.Board.BoardObservers
        for s in strokes:
           s.drawMyself()
           #lr = GeomUtils.pointListLinearRegression(s.Points)
           #self.drawLine(lr[0].X, lr[0].Y, lr[1].X, lr[1].Y, color = "#C0C000")

           #for curv in strokeApproximateCubicCurves(s):
               #self.drawCurve(curv, color="#FF0000")

           """
           s2 = GeomUtils.strokeApproximatePolyLine(s)
           self.drawStroke(s2, color="#0FcF00")
           for pt in s2.Points:
               self.drawCircle(pt.X, pt.Y, radius=2, width = 2, color="#FF00FF")


           angleList = GeomUtils.pointlistAnglesVector(s2.Points)
           i = 1
           cuspIdx = []
           numCusps = 0
           while i < len(angleList) - 1:
               totalAngle = sum(angleList[i-1:i+2]) * 57
               if totalAngle > 90 or totalAngle < -90:
                   numCusps += 1
                   cPt = s.Points[i]
                   self.drawCircle(cPt.X, cPt.Y, radius = 2, color = "#c0fc00", width = 2)
                   #cuspIdx.append(i)
                   i = i + 2
               i+= 1
           """

            
        for obs in observers:
           obs.drawMyself()

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
    def drawCurve(self, curve, width = 2, color = "#000000"):
        "Draw a curve on the board with width and color as specified"
        self.drawStroke(curve.toStroke(), width = width, color = color)
        colorwheel = ["#FF0000", "#00FF00", "#0000FF", "#FF00FF"]
        for i, pt in enumerate(curve.getControlPoints()):
            color = colorwheel[i]
            self.drawCircle(pt.X, pt.Y, radius=4-i, width = width, color = color)
	"""
        for pt in curve.getControlPoints():
            self.drawCircle(pt.X, pt.Y, radius=2, width = width, color = "#0000FF")
	"""



if __name__ == "__main__":
    TkSketchFrame()



