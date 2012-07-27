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
   This implementation listens for MouseDown events and builds
   strokes to hand off to the board system. Upon any event,
   Redraw is called globally to fetch all board paint objects and
   display them.
Todo:
   It would be nice if the interface weren't so directly tied to
   the Tkinter underpinnings.
   I.e., TkSketchGUI is essentially a Tkinter frame object, and must be
   manipulated similarly.
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
from xml.etree import ElementTree as ET

from SketchFramework.SketchGUI import _SketchGUI
from SketchFramework.Point import Point
from SketchFramework.Curve import CubicCurve
from SketchFramework.Stroke import Stroke
from SketchFramework.Board import Board
from Utils.StrokeStorage import StrokeStorage
from Utils.GeomUtils import (getStrokesIntersection,
                             strokeContainsStroke,
                             strokeApproximateCubicCurves)
from Utils import GeomUtils
from Utils import Logger
from Utils import ImageStrokeConverter

from Observers.ObserverBase import Animator

from functools import partial

# Constants
WIDTH = 1280 
HEIGHT = 800 
#WIDTH = 1680 
#HEIGHT =  1050
MID_W = WIDTH/2
MID_H = HEIGHT/2

logger = Logger.getLogger("TkSketchFrame", Logger.DEBUG)

def _initializeBoard(board):
    """Board initialization code, conveniently placed at the beginning of the
    file for easy modification"""

    from Observers import DebugObserver
    from Observers import RubineObserver
    from Bin import (BinObserver, EqualsObserver, PlusObserver,
                     MinusObserver, DivideObserver, MultObserver,
                     ExpressionObserver, EquationObserver, DirectedLine)
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

        CircleObserver.CircleMarker(board)
        #CircleObserver.CircleVisualizer(board)
        ArrowObserver.ArrowMarker(board)
        ArrowObserver.ArrowVisualizer(board)
        LineObserver.LineMarker(board)
        #LineObserver.LineVisualizer(board)
        TextObserver.TextCollector(board)
        #TextObserver.TextVisualizer(board)
        DiGraphObserver.DiGraphMarker(board)
        #DiGraphObserver.DiGraphVisualizer(board)
        DiGraphObserver.DiGraphExporter(board)
        TuringMachineObserver.TuringMachineCollector(board)
        TuringMachineObserver.TuringMachineExporter(board)
        TuringMachineObserver.TuringMachineVisualizer(board)

        """
        RubineObserver.RubineMarker(board, "RubineData.xml", debug=True)
        RubineObserver.RubineVisualizer(board)

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
    """A Thread that continually pulls image data from imgQ and puts the
    resulting strokes in strokeQ"""
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
                pointList = []
                for x,y in stk.points:
                   scale = WIDTH / float(1280)
                   newPoint = Point(scale * x,HEIGHT - scale * y)
                   pointList.append(newPoint)
                self.stk_queue.put(Stroke(pointList))


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

#TODO: Wrapper for TSketchGUI because This inherits from
#frame and we can't just switch it to inherit from SketchGUI
class TkSketchFrame(Frame, _SketchGUI):
    """The base GUI class.
    Class must implement drawText, drawLine and drawCircle. X-Y origin is
    bottom-left corner.
    Aside from these restrictions, interface options (reset board, etc) are up
    to the GUI programmer."""
    def __init__(self):
        "Set up the Tkinter GUI stuff as well as the board logic"
        global HEIGHT, WIDTH

        #Set up all the logical board stuff before displaying anything
        self.running = False
        self.isFullScreen = False
        self.OpQueue = Queue.Queue()
        self.StrokeQueue = Queue.Queue()
        self.Board = None
        self.CurrentPointList = []
        self._tempLines = []
        self.StrokeList = []
        self.AnimatorDrawtimes = {} #A dictionary of Animator subclasses to the
                                    #deadline for the next frame draw
        self.StrokeLoader = StrokeStorage()
        #self.SetupImageServer()
        self.ResetBoard()

        root = self.root = Tk()
        #capture = Tk() #Used exclusively to grab keyboard events
        #capture.focus_set()
        #sw = root.winfo_screenwidth()
        #sh = root.winfo_screenheight()

        self.root.title("Sketchy/Scratch")
        #root.overrideredirect(True) # Get rid of the menu bars
        root.geometry("%dx%d+0+0" % (WIDTH, HEIGHT)) #Set to full screen
        #root.focus_set() #Make sure we can grab keyboard
        Frame.__init__(self, self.root)
        self.pack()
        #Set up the GUI stuff

        self.drawMenuOptions = {}

        self.BoardCanvas= Canvas(self,
                    width=WIDTH, height = HEIGHT,
                    bg="black", bd=2)
        self.BoardCanvas.pack(side=BOTTOM)
        self.root.bind("<Alt-Return>", lambda e: self.toggleFullscreen() )
        self.root.bind("<Escape>", lambda e: self.toggleFullscreen() )
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
        self.SetCommandBindings(self.root, makeMenu=False)
        self.Redraw()

        #self.run()

    def toggleFullscreen(self):
        if not self.isFullScreen:
            self.root.withdraw()
            #sw = self.root.winfo_screenwidth()
            #sh = self.root.winfo_screenheight()
            sw, sh = 1024, 768
            self.BoardCanvas.config(width = sw, height= sh)
            self.root.overrideredirect(True) # Get rid of the menu bars
            self.root.geometry("%dx%d+1024+0" % (sw, sh)) #Set to full screen
            self.root.deiconify()
            #self.root.grab_set_global()

            self.capture = Tk() #Used exclusively to grab keyboard events
            self.capture.focus_force()
            self.capture.bind("<Escape>",  
                    lambda e: self.toggleFullscreen())
            self.capture.bind("<Alt-Return>",  
                    lambda e: self.toggleFullscreen())
            self.SetCommandBindings(self.capture, makeMenu=False)

        else:
            self.root.withdraw()
            self.root.overrideredirect(False)
            self.BoardCanvas.config(width = WIDTH, height = HEIGHT)
            self.root.geometry("%dx%d+0+0" % (WIDTH, HEIGHT))
            self.root.deiconify()
            #self.root.grab_release()
            self.capture.destroy()
            self.capture = None
            self.root.focus_force()
        self.isFullScreen = not self.isFullScreen
            
    def run(self):
       self.running = True
       #self.root.grab_set_global()
       self.root.update()
       try:
           while self.running:
               self.root.update()
               self.root.update_idletasks()
               self.AnimateFrame()
               self.AddQueuedStroke()
               self.runOp()
       except TclError:
           raise
       finally:
          pass
          #self.root.grab_release()

    def stop(self):
        print "Stopping!"
        self.running = False


    def post(self, operation):
        self.OpQueue.put(operation)

    def runOp(self):
        while not self.OpQueue.empty():
            op = self.OpQueue.get()
            op()
            self.OpQueue.task_done()

    def initBoardObservers( observers, debugAnnotations = None ):
        if observers is not None:
            for obs in observers:
                obs(self.Board)

    def SetCommandBindings(self, widget, makeMenu = True):
        "Reserve places in the menu for fun actions!"

        CMD_Reset = (lambda e=1:self.ResetBoard() or 
                     self.Redraw(clear=True))
        CMD_LoadStrokes = (lambda e=1: self.LoadStrokes() or 
                     self.Redraw())
        CMD_SaveStrokes = (lambda e=1: self.SaveStrokes())
        CMD_UndoStroke = (lambda e=1:self.RemoveLatestStroke() or 
                     self.Redraw())
        CMD_ProcessImage = (lambda e=1:self.LoadStrokesFromImage() or 
                     self.Redraw())

        widget.bind_all("<r>", CMD_Reset)
        widget.bind_all("<l>", CMD_LoadStrokes)
        widget.bind("<s>", CMD_SaveStrokes)
        widget.bind("<Control-z>", CMD_UndoStroke)
        widget.bind("<i>", CMD_ProcessImage)
        if makeMenu:
            win = self.master
            self.top_menu = top_menu = Menu(win)
            win.config(menu=top_menu)

            self.object_menu = Menu(top_menu)
            top_menu.bind("<ButtonPress-1>",(lambda e: self.RebuildObjectMenu()))
            self.RebuildObjectMenu()
            top_menu.add_cascade(label="ObjectMenu", menu=self.object_menu)
            top_menu.add_command(label="Reset Board", command = CMD_Reset)
            top_menu.add_command(label="Load strokes.dat",command = CMD_LoadStrokes)
            top_menu.add_command(label="Save strokes.dat",command = CMD_SaveStrokes)
            top_menu.add_command(label="Undo Stroke", command = CMD_UndoStroke)
            top_menu.add_command(label="Strokes From Image", 
                command = CMD_ProcessImage)


    def AddQueuedStroke(self):
        #Only process one stroke per round
        lim = 10
        if not self.StrokeQueue.empty() and lim > 0:
            lim -= 1
            stk = self.StrokeQueue.get()
            logger.debug("Adding queued stroke %s" % (stk))
            self.Board.AddStroke(stk)
            self.StrokeList.append(stk)
            self.Redraw()
            self.StrokeQueue.task_done()

    def LoadStrokes(self):
      for stroke in self.StrokeLoader.loadStrokes():
         self.AddStroke(stroke)
         #self.Board.AddStroke(stroke)
         #self.StrokeList.append(stroke)

    def SaveStrokes(self):
      self.StrokeLoader.saveStrokes(self.StrokeList)

    def LoadStrokesFromImage(self, image = None):
        global WIDTH, HEIGHT
        if image != None:
            try:
                strokeDict = ImageStrokeConverter.cvimgToStrokes(image)
            except:
                logger.error("Error importing strokes from frame")
                raise
        else:
            fname = askopenfilename(initialdir='/home/jbrowne/src/photos/')
            if fname == "":
               return

            try:
               logger.debug( "Loading strokes...")
               strokeDict = ImageStrokeConverter.imageToStrokes(fname)
               logger.debug( "Loaded %s strokes from '%s'" % 
                   (len(strokeDict['strokes']), fname))
            except Exception as e:
               logger.debug( "Error importing strokes from image '%s':\n %s" % 
                   (fname, e))
               raise

        strokes = strokeDict['strokes']
        WIDTH, HEIGHT = strokeDict['dims']
        for s in strokes:
           pointList = []
           for x,y in s.points:
              newPoint = Point(x, HEIGHT - y)
              pointList.append(newPoint)
           newStroke = Stroke(pointList)
           self.AddStroke(newStroke)


    def RemoveLatestStroke(self):
        if len (self.StrokeList) > 0:
            stroke = self.StrokeList.pop()
            self.Board.RemoveStroke(stroke)

    def RebuildObjectMenu(self):
        """Search the board for existing objects, and add a menu entry to 
        manipulate it (drawAll)"""
        observers = self.Board.GetBoardObservers()
        draw_vars = {}
        for obs in observers:
            key = obs.__class__
            if key not in self.drawMenuOptions and hasattr(obs, "DrawAll"):
                draw_vars[key] = key.DrawAll

        for key, var in draw_vars.items():
            self.drawMenuOptions[key] = self.object_menu.add_command(
                label=key.__name__,command=(
                    lambda class_=key: self.InvertDraw(class_)
                ), underline = 0
            )

    def InvertDraw(self, class_):
        "Essentially checkbox behavior for BoardObserver.DrawAll variable"
        if hasattr(class_, "DrawAll"):
            class_.DrawAll = not class_.DrawAll
            self.Redraw()


    def InitializeBoard(self):
        """Initialize all of the board observers and register debugable 
        annotations, etc."""
        _initializeBoard(self.Board)


    def ResetBoard(self):
        """Clear all strokes and board observers from the board (logically and 
        visually)"""
        self.p_x = self.p_y = None

        self.Board = Board(gui = self)
        self.InitializeBoard()
        self.RegisterAnimators()
        self.CurrentPointList = []
        self.StrokeList = []
        self._tempLines = []


    def RegisterAnimators(self):
        self.AnimatorDrawtimes = {}
        for obs in self.Board.BoardObservers:
            if Animator in type(obs).__mro__: #Check if it inherits from Animator
                logger.debug( "Registering %s as animator" % (obs))
                self.AnimatorDrawtimes[obs] = time.time()


    def CanvasMiddleMouseDown(self, event):
        x = event.x
        y = event.y
        #self.BoardCanvas.create_oval(x,y,x,y,activewidth="1", fill="black", 
        #outline = "black")

        if self.p_x != None and self.p_y != None:
            p_x = self.p_x
            p_y = self.p_y
            l = self.BoardCanvas.create_line(p_x, p_y, x ,y, 
                    fill = "blue", width=2)
            self._tempLines.append(l)

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
            l = self.BoardCanvas.create_line(p_x, p_y, x ,y, fill = "gray", width=2)
            self._tempLines.append(l)

        x = event.x
        y = HEIGHT - event.y
        t = time.time()
        self.CurrentPointList.append(Point(x,y,t))

        self.p_x = x
        self.p_y = HEIGHT - y

    def CanvasRightMouseUp(self, event):
        removed = False
        if len(self.CurrentPointList) > 0:
            stroke = Stroke( self.CurrentPointList )#, smoothing=True )
            self.CurrentPointList = []
            for stk in list(self.StrokeList):
                if len(getStrokesIntersection(stroke, stk) ) > 0:
                    logger.debug( "Removing Stroke")
                    removed = True
                    self.Board.RemoveStroke(stk)
                    self.StrokeList.remove(stk)
        self.p_x = self.p_y = None
        self.Redraw(clear=removed)

    def CanvasMouseDown(self, event):
        "Draw a line connecting the points of a stroke as it is being drawn"

        x = event.x
        y = event.y
        #self.BoardCanvas.create_oval(x,y,x,y,activewidth="1", fill="black", outline = "black")

        if self.p_x != None and self.p_y != None:
            p_x = self.p_x
            p_y = self.p_y
            l = self.BoardCanvas.create_line(p_x, p_y, x ,y, fill = "white", width=2)
            self._tempLines.append(l)

        x = event.x
        y = HEIGHT - event.y
        t = time.time()
        self.CurrentPointList.append(Point(x,y,t))

        self.p_x = x
        self.p_y = HEIGHT - y

    def AddCurrentStroke(self):
        if len(self.CurrentPointList) > 0:
            stroke = Stroke( self.CurrentPointList )#, smoothing=True )
            self.AddStroke(stroke)
            self.CurrentPointList = []

    def AddStroke(self, stroke):
        self.StrokeQueue.put(stroke)
        #self.Board.AddStroke(stroke)
        #self.StrokeList.append(stroke)

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


    def Redraw(self, clear=True):
        "Find all the strokes on the board, draw them, then iterate through every object and have it draw itself"
        global HEIGHT, WIDTH
        if clear:
            self.BoardCanvas.delete(ALL)
        else:
            for l in self._tempLines:
                self.BoardCanvas.delete(l)
        self._tempLines = []

        strokes = self.Board.Strokes
        observers = self.Board.BoardObservers
        for s in strokes:
           s.drawMyself()
        for obs in observers:
           obs.drawMyself()

        #fout = open("standalone.xml", "w")
        #bxml = self.Board.xml(WIDTH, HEIGHT)
        #print >> fout, ET.tostring(bxml)
        #fout.close()



    def do_drawCircle(self, x, y, radius=1, color="#FFFFFF", fill="", width=1.0):
         """Draw a circle on the canvas at (x,y) with radius rad. 
         Color should be 24 bit RGB string #RRGGBB.
         Empty string is transparent"""
         y = HEIGHT - y
         self.BoardCanvas.create_oval(x-radius,y-radius,x+radius,
            y+radius,width=width, fill=fill, outline = color)

    def do_drawLine(self, x1, y1, x2, y2, width=2, color="#FFFFFF"):
         """Draw a line on the canvas from (x1,y1) to (x2,y2). 
            Color should be 24 bit RGB string #RRGGBB"""
         y1 = HEIGHT - y1
         y2 = HEIGHT - y2
         self.BoardCanvas.create_line(x1, y1, x2 ,y2, fill=color, width = width)

    def do_drawText (self, x, y, InText="", size=10, color="#FFFFFF"):
        """Draw some text (InText) on the canvas at (x,y).
        Color as defined by 24 bit RGB string #RRGGBB"""
        y = HEIGHT - y
        text_font = ("times", size, "")
        self.BoardCanvas.create_text(x,y,text = InText,
            fill = color, font = text_font, anchor=NW)
    def do_drawCurve(self, curve, width = 2, color = "#FFFFFF"):
        "Draw a curve on the board with width and color as specified"
        self.drawStroke(curve.toStroke(), width = width, color = color)
        colorwheel = ["#FF0000", "#00FF00", "#0000FF", "#FF00FF"]
        for i, pt in enumerate(curve.getControlPoints()):
            color = colorwheel[i]
            self.drawCircle(pt.X, pt.Y, radius=4-i, 
                 width = width, color = color)
	"""
        for pt in curve.getControlPoints():
            self.drawCircle(pt.X, pt.Y, radius=2, width = width, color = "#0000FF")
	"""

    def do_drawStroke(self, stroke, width= 1, color = "#FFFFFF", erasable= True):
        if len(stroke.Points) >= 2:
            px, py = stroke.Points[0].X, stroke.Points[0].Y
            for pt in stroke.Points[1:]:
                x,y = pt.X, pt.Y
                self.do_drawLine(px, py, x, y, width=width, color=color)
                px, py = x,y
        #_SketchGUI.drawStroke(self, stroke, width = width, color = color, erasable = erasable)


    def drawText(self, *args, **kargs):
        op = partial(TkSketchFrame.do_drawText, self, *args, **kargs)
        self.OpQueue.put(op)
    def drawLine(self, *args, **kargs):
        op = partial(TkSketchFrame.do_drawLine, self, *args, **kargs)
        self.OpQueue.put(op)
    def drawCircle(self, *args, **kargs):
        op = partial(TkSketchFrame.do_drawCircle, self, *args, **kargs)
        self.OpQueue.put(op)
    def drawStroke(self, *args, **kargs):
        op = partial(TkSketchFrame.do_drawStroke, self, *args, **kargs)
        self.OpQueue.put(op)




if __name__ == "__main__":
    if len(sys.argv) > 1:
        #Do something with the CLI arguments
        fname = sys.argv[1]
        board = Board()
        _initializeBoard(board)

        stkLoader = StrokeStorage(fname+".dat")
        stkDict = ImageStrokeConverter.imageToStrokes(fname)
        stks = stkDict['strokes']
        WIDTH, HEIGHT = stkDict['dims']
        strokeList = []
        for s in stks:
            pointList = []
            for x,y in s.points:
               newPoint = Point(x, HEIGHT - y)
               pointList.append(newPoint)
            strokeList.append(Stroke(pointList))
            board.AddStroke(Stroke(pointList))

        stkLoader.saveStrokes(strokeList)
        #fout = open("standalone.xml", "w")
        #print >> fout, ET.tostring(board.xml(WIDTH, HEIGHT))
        #fout.close()

    else:
        TkSketchFrame().run()



