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
import traceback
import cPickle as pickle
from Tkinter import *
from tkFileDialog import askopenfilename
from tkMessageBox import *

from SketchFramework.SketchGUI import _SketchGUI
from SketchFramework.Point import Point
from SketchFramework.Stroke import Stroke
from SketchFramework.Board import Board
from Utils.StrokeStorage import StrokeStorage
from Utils import GeomUtils
from Utils.GeomUtils import getStrokesIntersection, strokeContainsStroke
from Utils import DataManager
from Utils import Logger
from sketchvision import ImageStrokeConverter

from Observers.ObserverBase import Animator


# Constants
WIDTH = 1000
HEIGHT = 800
BOARDSCALE = 2.0 #Scale factor: Logical board size / physical No. pixels
   
logger = Logger.getLogger("TkSketchGUI", Logger.DEBUG)

def _p2b(x,y):
    """Converts physical pixels to board coordinates"""
    global HEIGHT, BOARDSCALE
    return (x * BOARDSCALE, (HEIGHT - y) * BOARDSCALE)

def _b2p(x, y):
    """Converts board coordinates to physical pixels"""
    global HEIGHT, BOARDSCALE
    return (x / BOARDSCALE, HEIGHT - (y / BOARDSCALE ) )

def setBoardScale(width, height):
    """Set the global values for scaling board coordinates to physical coordinates. 
    Input: logical width and height of the board"""
    global BOARDSCALE, WIDTH, HEIGHT
    xFact = width / float(WIDTH)
    yFact = height / float(HEIGHT)
    BOARDSCALE = max(yFact, xFact)
    print "Setting BOARDSCALE to %f" % (BOARDSCALE)

def traceStroke(stroke):
    """Take in a true stroke with timing data, bitmap it and
    then trace the data for it"""
    #logger.debug("Stripping Timing Information from Stroke")
    #logger.debug("Stroke in, %s points" % len(stroke.Points))
    strokeLen = GeomUtils.strokeLength(stroke)
    sNorm = GeomUtils.strokeNormalizeSpacing(stroke, int(len(stroke.Points) * 1.5)) #Normalize to ten pixel spacing
    graph = {}
    #Graph structure looks like 
    #   { <point (x, y)> : {'kids' : <set of Points>, 'thickness' : <number>} }
    #Find self intersections
    intersections = {}
    for i in range(len(sNorm.Points) - 1):
        seg1 = (sNorm.Points[i], sNorm.Points[i+1])
        for j in range(i+1, len(sNorm.Points) - 1 ):
            seg2 = (sNorm.Points[j], sNorm.Points[j+1])
            cross = GeomUtils.getLinesIntersection( seg1, seg2)
            #Create a new node at the intersection
            if cross != None \
                and cross != seg1[0] \
                and cross != seg2[0]:
                    crossPt = (cross.X, cross.Y)
                    intDict = intersections.setdefault(crossPt, {'kids' : set(), 'thickness' : 1})
                    for pt in seg1 + seg2: #Add the segment endpoints as kids
                        coords = (int(pt.X), int(pt.Y))
                        if coords != crossPt:
                            intDict['kids'].add(coords)
            
    prevPt = None
    #for i in range(1, len(sNorm.Points)):
    for pt in sNorm.Points:
        curPt = (int(pt.X), int(pt.Y))
        if prevPt != None:
            #prevPt = (pt.X, pt.Y)
            graph[curPt] = {'kids' : set([prevPt]), 'thickness':1}
            graph[prevPt]['kids'].add(curPt)
        else:
            graph[curPt] = {'kids' : set(), 'thickness' :1 }
        prevPt = curPt
    for pt, ptDict in intersections.items():
        for k in graph.get(pt, {'kids' : []})['kids']:
            ptDict['kids'].add(k)
            graph[k]['kids'].add(pt)
        for k in ptDict['kids']:
            graph[k]['kids'].add(pt)
        graph[pt] = ptDict
    strokeList = ImageStrokeConverter.graphToStrokes(graph)
    if len(strokeList) > 1:
        #logger.debug("Stroke tracing split into multiple strokes")
        strokeList.sort(key=(lambda s: -len(s.points)))

    retPts = []
    
    if len(strokeList) > 0:
        for pt in strokeList[0].points:
            #logger.debug("Adding point %s" % (str(pt)))
            retPts.append(Point(pt[0], pt[1]))

    #logger.debug("Stroke out, %s points" % len(retPts))
    retStroke = Stroke(retPts)
    #saver = StrokeStorage.StrokeStorage()
    #saver.saveStrokes([stroke, retStroke])
    return retStroke


    

def _initializeBoard(board):
    """Board initialization code, conveniently placed at the beginning of the file for easy modification"""

    from Observers import DebugObserver
    from Observers import RubineObserver
    from Bin import BinObserver, EqualsObserver, PlusObserver, MinusObserver, DivideObserver, MultObserver, ExpressionObserver, EquationObserver, DirectedLine
    from Observers import NumberObserver

    """
    from Observers import CircleObserver
    from Observers import ArrowObserver
    from Observers import DiGraphObserver
    from Observers import TuringMachineObserver
    from Observers import LineObserver
    from Observers import TextObserver
    from Observers import RaceTrackObserver
    from Observers import TemplateObserver
    from Observers import TestAnimObserver
    """

    if board is not None:
        DataManager.DataManagerVisualizer(board)
        """
        RubineObserver.RubineMarker(board, "RubineData.xml", debug=True)
        #Rubine.RubineVisualizer(board)

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

        CircleObserver.CircleMarker(board)
        CircleObserver.CircleVisualizer(board)
        ArrowObserver.ArrowMarker(board)
        ArrowObserver.ArrowVisualizer(board)
        LineObserver.LineMarker(board)
        LineObserver.LineVisualizer(board)
        TextObserver.TextCollector(board)
        TextObserver.TextVisualizer(board)
        DiGraphObserver.DiGraphMarker(board)
        DiGraphObserver.DiGraphVisualizer(board)
        DiGraphObserver.DiGraphExporter(board)
        TuringMachineObserver.TuringMachineCollector(board)
        TuringMachineObserver.TuringMachineExporter(board)
        TuringMachineObserver.TuringMachineVisualizer(board)

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
        #top_menu.add_command(label="Strokes From Image", command = (lambda :self.LoadStrokesFromImage() or self.Redraw()), underline=1 )

        # code that loads the data manager
        self.dataManager_menu = Menu(top_menu)
        top_menu.add_cascade(label="Data Manager", menu=self.dataManager_menu)
        self.dataManager_menu.add_command(label="Load Data Manager", command = (lambda :self.loadDataManaer() or self.Redraw()), underline=1 )
        self.dataManager_menu.add_command(label="Next Participant", command = (lambda :self.nextParticipant() or self.Redraw()), underline=1 )
        self.dataManager_menu.add_command(label="Prev Participant", command = (lambda :self.prevParticipant() or self.Redraw()), underline=1 )
        self.dataManager_menu.add_command(label="Next Diagram", command = (lambda :self.nextDiagram() or self.Redraw()), underline=1 )
        self.dataManager_menu.add_command(label="Prev Diagram", command = (lambda :self.prevDiagram() or self.Redraw()), underline=1 )

    def nextParticipant(self):
        if self.participant + 1 >= len(self.dataset.participants):
            self.participant = 0
        else:
            self.participant += 1
        self.displayDataManager()

    def prevParticipant(self):
        if self.participant - 1 <= -1:
            self.participant = len(self.dataset.participants) - 1
        else:
            self.participant -= 1
        self.displayDataManager()

    def nextDiagram(self):
        p = self.participant
        if self.diagram + 1 >= len(self.dataset.participants[p].diagrams):
            self.diagram = 0
        else:
            self.diagram += 1
        self.displayDataManager()

    def prevDiagram(self):
        p = self.participant
        if self.diagram - 1 <= -1:
            self.diagram = len(self.dataset.participants[p].diagrams) - 1
        else:
            self.diagram -= 1
        self.displayDataManager()
        
    def loadDataManaer(self):

        # the string is the xml file you want to load.
        fname = askopenfilename(initialdir='./')
        if fname == "":
           return

        elif fname.strip().split(".")[-1] == "p":
            try:
                self.dataset = pickle.load(open(fname, "rb"))
            except Exception as e:
               print traceback.format_exc()
               logger.debug( "Error loading data from file '%s':\n %s" % (fname, e))
               return
        else:
            try:
                self.dataset = DataManager.loadDataset(fname)
            except Exception as e:
               print traceback.format_exc()
               logger.debug( "Error loading data from file '%s':\n %s" % (fname, e))
               return
        self.participant = 0
        self.diagram = 0
        self.displayDataManager()
        logger.debug( "Loaded data from '%s'" % (fname))

    def displayDataManager(self):
        """Paint whatever the display manager wants on the board"""
        global HEIGHT, WIDTH, BOARDSCALE
        self.ResetBoard()
        print self.dataset.participants[self.participant].diagrams[self.diagram].type

        xMax = 0
        yMax = 0
        xMin = sys.maxint
        yMin = sys.maxint

        par = self.participant
        dig = self.diagram


        # Finds the min and max points so we can scale the data to fit on the screen
        for stkNum, inkStroke in self.dataset.participants[par].diagrams[dig].InkStrokes.items():
            stroke = traceStroke(inkStroke.stroke)
            ul,br = GeomUtils.strokelistBoundingBox([stroke])
            xMax = max(ul.X, br.X, xMax)
            yMax = max(ul.Y, br.Y, yMax)
            xMin = min(ul.X, br.X, xMin)
            yMin = min(ul.Y, br.Y, yMin)

        # Find the distance that the strokes take up
        # the "+ 20" is so we can have a 10 pixle buffer around the edges

        setBoardScale(xMax, yMax)


        labelStrokeMap = {} #Maps groupLabel : set(strokes)
        for stkNum, inkStroke in self.dataset.participants[par].diagrams[dig].InkStrokes.items():
            #print inkStroke.id
            stroke = inkStroke.stroke
            for groupLabel in self.dataset.participants[par].diagrams[dig].groupLabels:
                if stroke.id in groupLabel.ids:
                    labelStrokeMap.setdefault(groupLabel, set()).add(stroke)
            points = []
            
            """
            # scale each point to it's new position
            for p in stroke.Points:
                x = (p.X - xMin) * scaleFactor + 10 # the "+10 is for the 10 pixle boarder
                # y axis points in the data manager are inverted compaired to our screen
                # so we invert them
                y = HEIGHT - ((p.Y - yMin) * scaleFactor + 10)
                points.append(Point(x,y))
            """

            # create a new stroke out of the scaled points and add it to the board.
            #s = Stroke(points)
            s = inkStroke.stroke
            self.Board.AddStroke(s)
            self.StrokeList.append(s)
            # Annotate the stroke with the type given in the data manager

        for groupLabel, strokeSet in labelStrokeMap.items():
            self.Board.AnnotateStrokes(list(strokeSet), 
                                       DataManager.DataManagerAnnotation(groupLabel.type))



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
      maxX = maxY = 0
      for stroke in self.StrokeLoader.loadStrokes():
         maxX = max(stroke.BoundBottomRight.X, maxX)
         maxY = max(stroke.BoundTopLeft.Y, maxY)
         self.Board.AddStroke(stroke)
         self.StrokeList.append(stroke)
      setBoardScale(maxX, maxY)

    def SaveStrokes(self):
      self.StrokeLoader.saveStrokes(self.StrokeList)
        
    """
    def LoadStrokesFromImage(self):
        fname = askopenfilename(initialdir='/home/jbrowne/src/sketchvision/images/')
        if fname == "":
           return

        try:
           logger.debug( "Loading strokes...")
           strokes = imageToStrokes(fname)
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
    """

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
        x, y = _p2b(event.x, event.y)
        t = time.time()
        self.CurrentPointList.append(Point(x,y,t))
        
        if self.p_x != None and self.p_y != None:
            px = self.p_x
            py = self.p_y
            self.drawLine(px, py, x, y, width=2, color="blue")
        self.p_x = x
        self.p_y = y



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
        
        x, y = _p2b(event.x, event.y)
        t = time.time()
        self.CurrentPointList.append(Point(x,y,t))
        if self.p_x != None and self.p_y != None:
            px = self.p_x
            py = self.p_y
            self.drawLine(px, py, x, y, width=2, color="gray")

        self.p_x = x
        self.p_y = y



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
        
        
        x, y = _p2b(event.x, event.y)
        t = time.time()
        self.CurrentPointList.append(Point(x,y,t))
        if self.p_x != None and self.p_y != None:
            px = self.p_x
            py = self.p_y
            self.drawLine(px, py, x, y, width=2, color="#000000")

        self.p_x = x
        self.p_y = y


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
        for obs in observers:
           obs.drawMyself()

    def drawCircle(self, x, y, radius=1, color="#000000", fill="", width=1.0):
         "Draw a circle on the canvas at (x,y) with radius rad. Color should be 24 bit RGB string #RRGGBB. Empty string is transparent"
         x, y = _b2p(x,y)
         self.BoardCanvas.create_oval(x-radius,y-radius,x+radius,y+radius,width=width, fill=fill, outline = "#BBBBBB")
         self.BoardCanvas.create_oval(x-radius,y-radius,x+radius,y+radius,width=width-1, fill=fill, outline = color)
         
    def drawLine(self, x1, y1, x2, y2, width=2, color="#000000"):
         "Draw a line on the canvas from (x1,y1) to (x2,y2). Color should be 24 bit RGB string #RRGGBB"
         x1, y1 = _b2p(x1,y1)
         x2, y2 = _b2p(x2, y2)
         self.BoardCanvas.create_line(x1, y1, x2 ,y2, fill="#BBBBBB", width = width+1)
         self.BoardCanvas.create_line(x1, y1, x2 ,y2, fill=color, width = width)

    def drawStroke(self, stroke, width = 2, color="#000000", erasable = False):
        if len(stroke.Points) > 0:
            prevPt = stroke.Points[0]
            px, py = _b2p(prevPt.X, prevPt.Y)
            for pt in stroke.Points[1:]:
                x, y = _b2p(pt.X, pt.Y)
                self.BoardCanvas.create_line(px, py, x ,y, fill="#BBBBBB", width = width) #Fake anti-aliasing
                self.BoardCanvas.create_line(px, py, x ,y, fill=color, width = width - 1)
                (px, py) = (x,y)

    def drawText (self, x, y, InText="", size=10, color="#000000"):
        "Draw some text (InText) on the canvas at (x,y). Color as defined by 24 bit RGB string #RRGGBB"
        x, y = _b2p(x,y)
        text_font = ("times", size, "")
        self.BoardCanvas.create_text(x,y,text = InText, fill = color, font = text_font, anchor=NW) 



if __name__ == "__main__":
    TkSketchFrame()



