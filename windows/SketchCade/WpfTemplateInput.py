#!/usr/bin/python

import time
import math
import pdb
from Utils import GeomUtils
from SketchFramework import Stroke
from SketchFramework import Point
from SketchFramework.WpfSketchGUI import _WpfSketchGUI, transformBoard_Wpf

import clr

clr.AddReference('PresentationCore')
clr.AddReference('PresentationFramework')
clr.AddReference('WPFFrameworkElementExtension.dll')

from System.Windows import Application
from System.Windows.Markup import XamlReader
from System.IO import FileStream, FileMode




# Constants
TEMPLATE_FILE = "board_templates.templ"
TEMPLATE_SAMPLE = 9 #num points in a template
TEMPLATE_TEXT = None

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
    pass
"""
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
           assert len(fields) == 3
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
          
"""
def storeTemplate(normStroke, numStrokes, tag=None, filename = TEMPLATE_FILE, overwrite = False):
    print "Saving template %s to: %s" % (tag, filename)
    if overwrite:
       fp = open (filename, "w")
    else:
       fp = open (filename, "a")

    if type(tag) is str:
       print >> fp, "#TEMPLATE %s %s" % (tag, numStrokes)
       for p in normStroke.Points:
          print >> fp, "%s %s" % (p.X, p.Y)
       print >>fp, "#END %s" % (tag)
    fp.close()


class TemplateInput(_WpfSketchGUI):
    def __init__(self, wpfCanvas, **kargs):
        self.Canvas = wpfCanvas   
        self.CurrentPointList = []
        self.StrokeList = []
        self.templates = {}

    def SaveTemplate(self, sender, e, numSamples = TEMPLATE_SAMPLE):
        if len(self.StrokeList) > 0:
            #last_stroke = self.StrokeList[-1]
            pts = []
            for stk in self.StrokeList:
                pts.extend(stk.Points)
            templ_stroke = Stroke.Stroke(points= pts)
            template_name = TEMPLATE_TEXT.Text 
            if template_name.strip() == '':
                template_name = 'Blob'
            sNorm = GeomUtils.strokeNormalizeSpacing(templ_stroke, numSamples * len(self.StrokeList))
            centroid = GeomUtils.centroid(sNorm.Points)
            sNorm = sNorm.translate(-1*centroid.X, -1 * centroid.Y)
            storeTemplate(sNorm, len(self.StrokeList), tag=template_name)
        self.Clear()

    def Clear(self, *args, **kargs):
        _WpfSketchGUI.Clear(self)
        self.StrokeList = []
        
    def LoadTemplates(self, sender, e):
        self.templates = loadTemplates()

    def CanvasMouseUp(self, sender, e):
        "Finish the stroke and add it to the board"
        for stylusPoint in e.Stroke.StylusPoints:
            px, py = transformBoard_Wpf(stylusPoint.X, stylusPoint.Y, HEIGHT)
            self.CurrentPointList.append( Point.Point( px, py ) )
        #start a new stroke
        new_stroke = Stroke.Stroke(self.CurrentPointList)
        self.StrokeList.append(new_stroke)
        
        #Clear state for next stroke
        self.CurrentPointList = []

        for tag, templ in self.templates.items():
            print( "Stroke to template %s: %s" % (tag, scoreStroke(new_stroke, templ)))

    def drawPoint(self, point):
        self.drawCircle(point.X, point.Y, rad = 3)

    def drawStroke(self, stroke, LineWidth = 2, color="#000000"):
        prev_p = None
        for next_p in stroke.Points:
            if prev_p is not None:
                self.drawLine(prev_p.X, prev_p.Y, next_p.X, next_p.Y, LineWidth=LineWidth, color=color)
            prev_p = next_p


def LoadApp():
    global TEMPLATE_TEXT
    app = Application()

    #Load the XAML.
    xamlWindow = XamlReader.Load(FileStream('TemplateInput.xaml', FileMode.Open))	#Window object as the root.

    #wsg = _WpfSketchGUI( xamlWindow.InkCanvas )
    #_WpfSketchGUI.Singleton = wsg
    
    TemplateInputGUI = TemplateInput( xamlWindow.InkCanvas )
    

    #Bind the Event Handler
    xamlWindow.InkCanvas.StrokeCollected += TemplateInputGUI.CanvasMouseUp
    xamlWindow.StoreButton.Click += TemplateInputGUI.SaveTemplate
    xamlWindow.LoadButton.Click += TemplateInputGUI.LoadTemplates
    xamlWindow.ClearButton.Click += TemplateInputGUI.Clear
    TEMPLATE_TEXT = xamlWindow.TemplateNameBox
    #xamlWindow.InkCanvas.MouseUp += _WpfSketchGUI.Singleton.Canvas_MouseUp
    #xamlWindow.InkCanvas.MouseDown += _WpfSketchGUI.Singleton.Canvas_MouseDown
    
    app.Run(xamlWindow)
if __name__ == "__main__":
    LoadApp()



