"""
filename: DivideObserver.py

description:
   This module looks for Divide signs

Doctest Examples:

>>> t = TextMarker()

""" 

#-------------------------------------

import pdb
import math
from Utils import Logger
from Utils import GeomUtils

from Observers import CircleObserver
from Observers import LineObserver
from Observers import ObserverBase

from SketchFramework import SketchGUI
from SketchFramework.Point import Point
from SketchFramework.Stroke import Stroke
from SketchFramework.Board import BoardObserver, BoardSingleton
from SketchFramework.Annotation import Annotation, AnnotatableObject

from xml.etree import ElementTree as ET

from Bin import DirectedLine

logger = Logger.getLogger('TextObserver', Logger.WARN )

#-------------------------------------

class DivideAnnotation(Annotation):
    def __init__(self, scale):
        "Create a Divide annotation. text is the string, and scale is an appropriate size"
        Annotation.__init__(self)
        self.scale = scale # an approximate "size" for the text
    def xml(self):
        root = Annotation.xml(self)
        root.attrib['scale'] = str(self.scale)
        return root

#-------------------------------------

l_logger = Logger.getLogger('DivideMarker', Logger.WARN)
class DivideMarker( BoardObserver ):
    """Looks for Divide signes"""
    
    def __init__(self):
        BoardObserver.__init__(self)
        BoardSingleton().AddBoardObserver( self, [DivideAnnotation])
        BoardSingleton().RegisterForAnnotation( DirectedLine.BT_LineAnnotation, self )
    def onAnnotationAdded( self, strokes, annotation ):
        "Checks to see if an divide sign has been added"

        ul,br = GeomUtils.strokelistBoundingBox(strokes)
        height = ul.Y - br.Y
        BoardSingleton().AnnotateStrokes( strokes, DivideAnnotation(height))
        return

#-------------------------------------

class DivideVisualizer( ObserverBase.Visualizer ):

    def __init__(self):
        ObserverBase.Visualizer.__init__( self, DivideAnnotation )

    def drawAnno( self, a ):
        ul,br = GeomUtils.strokelistBoundingBox( a.Strokes )
        spaceing = 5
        ul.X -= spaceing
        ul.Y += spaceing
        br.X += spaceing
        br.Y -= spaceing

        logger.debug(a.Strokes)
        height = ul.Y - br.Y
        midpointY = (ul.Y + br.Y) / 2
        midpointX = (ul.X + br.X) / 2
        left_x = midpointX - a.scale / 2.0
        right_x = midpointX + a.scale / 2.0
        SketchGUI.drawBox(ul, br, color="#a0a0a0");
        
        SketchGUI.drawText( br.X - 15, br.Y, "/", size=15, color="#a0a0a0" )

#-------------------------------------
# if executed by itself, run all the doc tests

if __name__ == "__main__":
    Logger.setDoctest(logger)
    import doctest
    doctest.testmod()



