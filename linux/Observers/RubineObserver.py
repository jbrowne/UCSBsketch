"""
filename: Rubine.py

description:
   Using the Rubine classifier to detect strokes

Doctest Examples:

>>> t = TextMarker()

"""

#-------------------------------------

import pdb
import math
from Utils import Logger
from Utils import GeomUtils
from Utils import Rubine

from Observers import CircleObserver
from Observers import LineObserver
from Observers import ObserverBase

from SketchFramework.Point import Point
from SketchFramework.Stroke import Stroke
from SketchFramework.Board import BoardObserver
from SketchFramework.Annotation import Annotation, AnnotatableObject

from xml.etree import ElementTree as ET

from numpy  import *

logger = Logger.getLogger('TextObserver', Logger.WARN )

#-------------------------------------

class RubineAnnotation(Annotation):
    def __init__(self, type, scale, accuracy):
        "Create a Rubin annotation."
        Annotation.__init__(self)
        self.type = type # a string for the text
        self.accuracy = accuracy
        self.scale = scale # an approximate "size" for the object
    
    def xml(self):
        root = Annotation.xml(self)
        root.attrib["type"] = self.type
        root.attrib['scale'] = str(self.scale)
        root.attrib['accuracy'] = str(self.accuracy)
        return root

#------------------------------------------------------------

class RubineMarker( BoardObserver ):
    """Classifies strokes based on the Rubine classifier"""

    def __init__(self, board, fname, debug=False):
        """ Initiates the Rubine classifier. fname is the name of a file containing the training data to be used. """
        BoardObserver.__init__(self, board)
        #featureSet = Rubine.RubineFeatureSet()
        #featureSet = Rubine.BCPFeatureSet()
        rubineDataFile = open(fname, "r")
        featureSet = Rubine.BCPFeatureSet()
        self.classifier = Rubine.RubineClassifier(featureSet = featureSet, debug = debug)
        self.classifier.loadWeights(rubineDataFile)
        rubineDataFile.close()
        self.getBoard().AddBoardObserver( self , [RubineAnnotation])
        self.getBoard().RegisterForStroke( self )

    def onStrokeAdded(self, stroke):
        """ Attempts to classify a stroke using the given training data """

        name = self.classifier.classifyStroke(stroke)
        if name == None:
            return
        height = stroke.BoundTopLeft.Y - stroke.BoundBottomRight.Y        
        self.getBoard().AnnotateStrokes( [stroke],  RubineAnnotation(name, height , 0))

    def onStrokeRemoved(self, stroke):
        for rb_anno in stroke.findAnnotations(RubineAnnotation):
            self.getBoard().RemoveAnnotation(rb_anno)



#------------------------------------------------------------

class RubineVisualizer( ObserverBase.Visualizer ):

    def __init__(self, board):
        ObserverBase.Visualizer.__init__( self, board,  RubineAnnotation )

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
        """
        self.getBoard().getGUI().drawBox(ul, br, color="#a0a0a0")
        """
        gui = self.getBoard().getGUI()
        color = "#0C00F0"
        gui.drawText( br.X - 15, br.Y, a.type , size=15, color=color )
        for s in a.Strokes:
            gui.drawStroke(s, width = 3, color = color)
            gui.drawStroke(s, width = 1, color = "#000000")
#-------------------------------------
# if executed by itself, run all the doc tests

if __name__ == "__main__":
    Logger.setDoctest(logger)
    import doctest
    doctest.testmod()

