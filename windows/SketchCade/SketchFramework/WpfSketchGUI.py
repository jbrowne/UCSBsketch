import clr
import sys
import os
import threading
import Queue

clr.AddReference('PresentationCore')
clr.AddReference('PresentationFramework')
clr.AddReference('Microsoft.Scripting')
clr.AddReference('Microsoft.Dynamic')
clr.AddReference('Microsoft.Ink')
#clr.AddReference('Microsoft.Win32')
clr.AddReference('System.Drawing')
clr.LoadAssemblyFromFile('WPFFrameworkElementExtension.dll')

clr.AddReference('WPFFrameworkElementExtension')


from System.Windows.Markup import XamlReader
from System.Windows import Application, FlowDirection
from System.IO import FileStream, FileMode
from System.Windows.Controls import InkCanvas, TextBlock, UIElementCollection, InkCanvasEditingMode
from System.Windows.Media import Brushes, SolidColorBrush, Color, FormattedText, Typeface
from System.Windows.Shapes import Ellipse, Line
from System.Windows.Input import StylusPoint, StylusPointCollection
from System.Windows.Ink import Stroke as MSStroke, StylusTip
from System.Globalization import CultureInfo
from Microsoft.Win32 import OpenFileDialog



from Utils import GeomUtils    #Import GeomUtils first.  Just do it.  Lest Point won't load when being loaded through Board.  Still can't figure out root cause, guessing something with Circular dependencies?
from Utils import Logger

from SketchSystem import initialize
from SketchFramework.Stroke import Stroke
from SketchFramework.Point import Point
from SketchFramework.Board import BoardSingleton
from MSRecognizers import MSAxesObserver
import SketchGUI
from SketchGUI import _SketchGUI
from SketchGUI import SketchGUISingleton

########################################
#Some globals for sanity, set in initialization code
#print SketchGUI.globals()
logger = Logger.getLogger('WPFSketchGUI', Logger.WARN )


def recordEvent(event, filename="playback.txt"):
    mode = "a"
    fp = open(filename, mode)
    print >> fp, "#%s" % (event)
    fp.close()

def recordStroke(stroke, id, filename = "playback.txt"):
    saveStrokes([stroke], filename=filename, overwrite=False, id=id)

def recordStrokeErase( id, filename = "playback.txt"):
    mode = "a"
    fp = open(filename, mode)
    print >> fp, "#Remove %s" % (id)
    fp.close()


        
class _WpfSketchGUI(_SketchGUI):
    #HEIGHT = _SketchGUI.HEIGHT
    Singleton = None
    StrokeCount = 0
    def __init__(self, wpfCanvas, backCanvas = None):
        
        
        self.Board = BoardSingleton(reset = True)
        initialize(self.Board)
        self.Canvas = wpfCanvas
        self.BackCanvas = backCanvas
        self.StrokeMap = {}
        self.StrokeOrderList = []
        self.StrokeIDMap = {}
        self.RestoreStrokes = loadStrokes(filename="Restorefile.txt")
        self._inking = True
        self._lineStrokes = {}
        self._removeStrokes = []


        try:
            os.remove("Restorefile.txt")
        except:
            pass
        try:
            os.remove("playback.txt")
        except:
            pass
        self.Singleton = self
        _WpfSketchGUI.Singleton = self
        _SketchGUI.Singleton = self
        
         
    def InkCanvas_StrokeCollected( self, sender, e ):   #e is a InkCanvasStrokeCollectedEventArgs     
        pointList = []
        #Transform the Canvas's Points into our Points
        for stylusPoint in e.Stroke.StylusPoints:
            px, py = transformBoard_Wpf(stylusPoint.X, stylusPoint.Y, _WpfSketchGUI.HEIGHT)
            pointList.append( Point( px, py ) )        
        newStroke = Stroke( pointList )
        self.StrokeMap[e.Stroke] = newStroke
        self.StrokeOrderList.append(newStroke)
        
        #try:
        self.Board.AddStroke( newStroke )
        strokeId = _WpfSketchGUI.StrokeCount
        _WpfSketchGUI.StrokeCount += 1

        self.StrokeIDMap[newStroke] = strokeId
        recordStroke(newStroke, strokeId)        
        #except Exception as exc:
        #    logger.error("**********ADD STROKE ERROR ********\n %s" % (exc))
        self.Redraw()
        #SketchGUISingleton().drawText(100,100, InText=rec_text(self.StrokeOrderList))
        saveStrokes(self.Board.Strokes, filename="Restorefile.txt", overwrite = True)

    def InkCanvas_StrokeErasing(self, sender, e):
        self._removeStrokes.append(e.Stroke)
        """
        board_stroke = self.StrokeMap.pop(e.Stroke, None)
        if board_stroke is not None: #Stroke is user-drawn
            strokeID = self.StrokeIDMap.get(board_stroke, "")
            recordStrokeErase(strokeID)
            #self.StrokeOrderList.remove(board_stroke)
            self.Board.RemoveStroke(board_stroke)
            self.Redraw()
        """
    def InkCanvas_MouseLeftButtonUp(self, sender, e):
        if self.Canvas.EditingMode == InkCanvasEditingMode.EraseByStroke:
            self.Canvas.EditingMode = InkCanvasEditingMode.Ink
            self.Canvas.Background = SolidColorBrush( color_from_hex("#FFFFFF"))
        for removedStroke in self._removeStrokes:
            board_stroke = self.StrokeMap.pop(removedStroke, None)
            if board_stroke is not None: #Stroke is user-drawn
                strokeID = self.StrokeIDMap.get(board_stroke, "")
                recordStrokeErase(strokeID)
                #self.StrokeOrderList.remove(board_stroke)
                self.Board.RemoveStroke(board_stroke)
        self._removeStrokes = []
        self.Redraw()

    def SaveStrokesClicked(self, sender, e):
        recordEvent("SaveStrokes")
        saveStrokes(self.Board.Strokes, overwrite = True)
        
    def ChooseFileClicked(self, sender, e):
        fd = OpenFileDialog()
        fd.Filter = "Comma Separated Value|*.csv|All Files|*.*"
        if (fd.ShowDialog()):
            MSAxesObserver.SETDATAFILE(fd.FileName)
            print( "Open file %s" % (fd.FileName) )
            recordEvent("Open %s" % (fd.FileName))

            self.ResetBoard()
    def LoadStrokesClicked(self, sender, e):
        for stroke in loadStrokes():
            #self.StrokeMap[stroke] = None
            self.StrokeOrderList.append(stroke)
            self.Board.AddStroke( stroke )
            saveStrokes([stroke], filename="Restorefile.txt", overwrite = False)
        recordEvent("LoadStrokes")

        self.Redraw()
    
    def RestoreClicked(self, sender, e):
        for stroke in self.RestoreStrokes:
            self.StrokeOrderList.append(stroke)
            self.Board.AddStroke( stroke )
        recordEvent("Restored")
        self.Redraw()
        
    def ResetBoard(self, *args, **kargs):
        recordEvent("ResetBoard")
        
        self.Clear()
        self.Board.Reset()
        self.StrokeOrderList = []
        initialize(self.Board)
        
    def Clear(self, *args, **kargs):
        self._lineStrokes = {}
        self.StrokeMap = {}
        for elem in list(self.BackCanvas.Children):
            if elem is not self.Canvas:
                self.BackCanvas.Children.Remove(elem)
        for stk in list(self.Canvas.Strokes):
            self.Canvas.Strokes.Remove(stk)
        
    def ToggleCursorEraser(self, sender, e):
        if self.Canvas.EditingMode == InkCanvasEditingMode.EraseByStroke:
            self.Canvas.EditingMode = InkCanvasEditingMode.Ink
            self.Canvas.Background = SolidColorBrush( color_from_hex("#FFFFFF"))
        else:
            self.Canvas.EditingMode = InkCanvasEditingMode.EraseByStroke
            self.Canvas.Background = SolidColorBrush( color_from_hex("#F8ACAC"))
            

            
    def Redraw(self):
        "Find all the strokes on the board, draw them, then iterate through every object and have it draw itself"
        global HEIGHT, WIDTH
        self.Clear()
        
            
        strokes = self.Board.Strokes
        observers = self.Board.BoardObservers
        
        #try:
        for obs in observers:
            obs.drawMyself()
           
        for s in strokes:
            s.drawMyself()
        #except Exception as exc:
        #    logger.error("************ REDRAW ERROR **************\n%s" % (exc) )
        
        
        
    def drawCircle(self, x, y, radius=1, color="#000000", fill="", width=1.0):
        "Draw a circle on the canvas at (x,y) with radius rad. Color should be 24 bit RGB string #RRGGBB. Empty string is transparent"
        #x,y = transformBoard_Wpf(x,y,height = HEIGHT)
        el = Ellipse()
        el.Width = radius * 2
        el.Height = radius * 2
        el.Stroke = SolidColorBrush(color_from_hex(color))
        el.StrokeThickness = width
        el.IsHitTestVisible = False
        self.BackCanvas.SetBottom(el, y - radius)
        self.BackCanvas.SetLeft(el, x - radius)
#        el.SetValue(InkCanvas.LeftProperty, x - radius)
#        el.SetValue(InkCanvas.TopProperty, y - radius)

        self.BackCanvas.Children.Add(el)

    def drawLine(self, x1, y1, x2, y2, width=2, color="#000000"):
        "Draw a line on the canvas from (x1,y1) to (x2,y2). Color should be 24 bit RGB string #RRGGBB"
        global HEIGHT
        x1, y1 = transformBoard_Wpf(x1, y1, height = _WpfSketchGUI.HEIGHT)
        x2, y2 = transformBoard_Wpf(x2, y2, height = _WpfSketchGUI.HEIGHT)

        line = Line()
        line.Stroke = SolidColorBrush(color_from_hex(color))
        line.StrokeThickness = width
        line.IsHitTestVisible = False
        line.X1 = x1
        line.X2 = x2
        line.Y1 = y1
        line.Y2 = y2
        self.BackCanvas.Children.Add(line)

         #self.Canvas.Background = Brushes.LightGreen
         
    def drawText (self, x, y, InText="", size=10, color="#000000"):
        "Draw some text (InText) on the canvas at (x,y). Color as defined by 24 bit RGB string #RRGGBB"
        #x,y = transformBoard_Wpf(x,y,height = HEIGHT)
        text = TextBlock()
        text.Text = InText
        text.FontSize = size
        text.Foreground = SolidColorBrush(color_from_hex(color))
        text.IsHitTestVisible = False
        
        
        self.BackCanvas.SetBottom(text, y)
        self.BackCanvas.SetLeft(text, x)
        self.BackCanvas.Children.Add(text)
       
    def drawStroke(self, stroke, width = 2, color = "#000000", erasable = False):
        if erasable:
            spc = StylusPointCollection()
            for point in stroke.Points:
                x, y = transformBoard_Wpf(point.X, point.Y, height = _WpfSketchGUI.HEIGHT)
                s_point = StylusPoint(x, y)
                spc.Add(s_point)
            ms_stroke = MSStroke(spc)
            if stroke in self.Board.Strokes:
                self.StrokeMap[ms_stroke] = stroke
        
            ms_stroke.DrawingAttributes.Color = color_from_hex(color)
            ms_stroke.DrawingAttributes.Width = width
            ms_stroke.DrawingAttributes.StylusTip = StylusTip.Ellipse
            ms_stroke.DrawingAttributes.IgnorePressure = True

            self.Canvas.Strokes.Add(ms_stroke)
        else:
            _SketchGUI.drawStroke(self, stroke, width = width, color = color, erasable = erasable)
    
    def drawBox(self, topleft, bottomright, topright = None, bottomleft = None, color="#000000", width=2):
        os = width / 2# Offset to connect the point tips
        if topright is None:
            topright = Point(bottomright.X, topleft.Y)
        if bottomleft is None:
            bottomleft = Point(topleft.X, bottomright.Y)
        self.drawLine(topleft.X + os, topleft.Y - os, topright.X - os, topright.Y - os, color=color, width=width)
        self.drawLine(topright.X - os, topright.Y, bottomright.X - os, bottomright.Y, color=color, width=width)
        self.drawLine(bottomright.X - os, bottomright.Y + os, bottomleft.X + os, bottomleft.Y + os, color=color, width=width)
        self.drawLine(bottomleft.X + os, bottomleft.Y, topleft.X + os, topleft.Y, color=color, width=width)
        
        """
        self.drawLine(topleft.X + 0, topleft.Y - 0, topright.X - 0, topright.Y - 0, color="#000000", width=1)
        self.drawLine(topright.X - 0, topright.Y - 0, bottomright.X - 0, bottomright.Y + 0, color="#000000", width=1)
        self.drawLine(bottomright.X - 0, bottomright.Y + 0, bottomleft.X + 0, bottomleft.Y + 0, color="#000000", width=1)
        self.drawLine(bottomleft.X + 0, bottomleft.Y + 0, topleft.X + 0, topleft.Y - 0, color="#000000", width=1)
        """

        
def WpfSketchGUISingleton():
    if _WpfSketchGUI.Singleton == None:
       print ("Creating new singleton")
       LoadApp()
       
    print("Singleton value %s" % (_WpfSketchGUI.Singleton))
    return _WpfSketchGUI.Singleton



########################################

def color_from_hex(color_string):
    "Convert a color string to a triple of bytes, (r,g,b)"
    if type(color_string) is str:
        clist = []
        color_string = color_string[1:]
        
        for i in range(3):
            hexstr = color_string[2*i: 2*i + 2]
            clist.append(int('0x'+hexstr, 16))
        return Color.FromArgb(0xFF, clist[0], clist[1], clist[2])
    else:
        return None

def transformBoard_Wpf(x, y, height = None):
    return x, height - y

def loadStrokes(filename = "saved_strokes.txt"):
    "Returns a list of strokes saved to filename"
    strokelist = []
    current_stroke = None
    try:
        fp = open(filename, "r")
        for line in fp.readlines():
            if line.startswith("#Stroke"):
                current_stroke = Stroke()
            elif line.startswith("#ENDStroke"):
                if type(current_stroke) is Stroke:
                    strokelist.append(current_stroke)
                current_stroke = None
            else:
                fields = line.split()
                if len(fields) == 3 and type(current_stroke) is Stroke:
                    x = float(fields[0])
                    y = float(fields[1])
                    t = float(fields[2])
                    current_stroke.addPoint(Point(x,y,t))
        fp.close()
    except:
        pass
    logger.debug("Loaded %s strokes" % (len(strokelist) ) )
    return strokelist
                
            
def saveStrokes(strokes, filename = "saved_strokes.txt", overwrite = True, id = ""):
    "Saves a single stroke to filename"
    if overwrite:
        mode = "w"
    else:
        mode = "a"
    fp = open(filename, mode)
    for stk in strokes:
        print >> fp, "#Stroke %s" % (id)
        for point in stk.Points:
            print >> fp, point.X, point.Y, point.T
        print >> fp, "#ENDStroke"
    fp.close()



def LoadApp():
    global HEIGHT, WIDTH
    app = Application()

    #Load the XAML.
    xamlWindow = XamlReader.Load(FileStream('SketchFramework\SketchCade.xaml', FileMode.Open))	#Window object as the root.

    #wsg = _WpfSketchGUI( xamlWindow.InkCanvas )
    #_WpfSketchGUI.Singleton = wsg
    
    _WpfSketchGUI.Singleton = _WpfSketchGUI( xamlWindow.InkCanvas, xamlWindow.BackCanvas )
    

    #Bind the Event Handler
    xamlWindow.InkCanvas.StrokeCollected += _WpfSketchGUI.Singleton.InkCanvas_StrokeCollected
    xamlWindow.InkCanvas.StrokeErasing += _WpfSketchGUI.Singleton.InkCanvas_StrokeErasing
    xamlWindow.InkCanvas.MouseLeftButtonUp += _WpfSketchGUI.Singleton.InkCanvas_MouseLeftButtonUp
    #xamlWindow.InkCanvas.MouseUp += _WpfSketchGUI.Singleton.Canvas_MouseUp
    #xamlWindow.InkCanvas.MouseDown += _WpfSketchGUI.Singleton.Canvas_MouseDown
    xamlWindow.ClearButton.Click += _WpfSketchGUI.Singleton.ResetBoard
    xamlWindow.EraserButton.Click += _WpfSketchGUI.Singleton.ToggleCursorEraser
    xamlWindow.SaveButton.Click += _WpfSketchGUI.Singleton.SaveStrokesClicked
    xamlWindow.LoadButton.Click += _WpfSketchGUI.Singleton.LoadStrokesClicked
    xamlWindow.RestoreButton.Click += _WpfSketchGUI.Singleton.RestoreClicked
    xamlWindow.ChooseFileButton.Click += _WpfSketchGUI.Singleton.ChooseFileClicked
    xamlWindow.InkCanvas.MouseRightButtonUp += _WpfSketchGUI.Singleton.ToggleCursorEraser
    app.Run(xamlWindow)

########################################

if __name__ == "__main__":

    
    LoadApp()
    