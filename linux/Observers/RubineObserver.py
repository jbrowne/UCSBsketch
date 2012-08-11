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

logger = Logger.getLogger('RubineObserver', Logger.DEBUG )

#-------------------------------------

class RubineAnnotation(Annotation):
    def __init__(self, scores):
        "Create a Rubin annotation."
        Annotation.__init__(self)
        #self.type = type # Deprecated
        #self.accuracy = accuracy Deprecated
        #self.scale = scale # Deprecated
        self.scores = scores
        self.name = ""
        if len(self.scores) > 0:
            self.name = scores[0]['symbol']
    
    def xml(self):
        root = Annotation.xml(self)
        root.attrib['name'] = self.name
        #root.attrib["type"] = self.type
        #root.attrib['scale'] = str(self.scale)
        #root.attrib['accuracy'] = str(self.accuracy)
        return root

#------------------------------------------------------------

class RubineMarker( BoardObserver ):
    """Classifies strokes based on the Rubine classifier"""

    def __init__(self, board, fname, debug=False):
        """ Initiates the Rubine classifier. fname is the name of a file containing the training data to be used. """
        BoardObserver.__init__(self, board)
        #featureSet = Rubine.RubineFeatureSet()
        rubineDataFile = open(fname, "r")
        featureSet = Rubine.BCPFeatureSet()
        #featureSet = Rubine.BCPFeatureSet_Combinable()
        self.classifier = Rubine.RubineClassifier(featureSet = featureSet, debug = debug)
        logger.debug("Loading weights from %s" % (fname))
        self.classifier.loadWeights(rubineDataFile)
        rubineDataFile.close()
        self.getBoard().AddBoardObserver( self , [RubineAnnotation])
        self.getBoard().RegisterForStroke( self )

        self.allStrokes = {} #Dict of {<stroke> : <set of connected strokes>}

    def onStrokeAdded(self, stroke):
        """ Attempts to classify a stroke using the given training data """
        bbox1 = (stroke.BoundTopLeft, stroke.BoundBottomRight)
        s1_eps = (stroke.Points[0], stroke.Points[-1]) #Stroke 1 endpoints
        matchStks = set()
        for stk2, connectStrokes in self.allStrokes.items():
            bbox2 = (stroke.BoundTopLeft, stroke.BoundBottomRight)
            s2_eps = (stk2.Points[0], stk2.Points[-1]) #Stroke 2 endpoints

            for ep in s1_eps: #Do any of the stroke's endpoints overlap stroke2?
                if GeomUtils.pointInBox(ep, bbox2[0], bbox2[1]):
                    if ep in stk2.Points:
                        matchStks.update(connectStrokes)
                        break
            if len(connectStrokes) > 0:
                break

            for ep in s2_eps: #Do any of stroke2's endpoints overlap stroke?
                if GeomUtils.pointInBox(ep, bbox1[0], bbox1[1]):
                    if ep in stroke.Points:
                        matchStks.update(connectStrokes)
                        break
            if len(connectStrokes) > 0:
                break

        matchStks.add(stroke) #Update the connected strokes list
        for stk in matchStks:
            self.allStrokes[stk] = matchStks

        strokeList = list(matchStks)
        scores = self.classifier.classifyStrokeList(strokeList)
        #Remove the previous annotations
        for stk in strokeList:
            annotations = stk.findAnnotations(annoType = RubineAnnotation)
            for anno in annotations:
                self.getBoard().RemoveAnnotation(anno)
        if len(scores) > 0:
            height = stroke.BoundTopLeft.Y - stroke.BoundBottomRight.Y        
            best = scores[0]['symbol']
            self.getBoard().AnnotateStrokes( strokeList,  RubineAnnotation(scores))

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
        #left_x = midpointX - a.scale / 2.0
        #right_x = midpointX + a.scale / 2.0
        """
        self.getBoard().getGUI().drawBox(ul, br, color="#a0a0a0")
        """
        gui = self.getBoard().getGUI()
        color = "#0C00F0"
        gui.drawText( br.X - 15, br.Y, a.name , size=15, color=color )
        for s in a.Strokes:
            gui.drawStroke(s, width = 3, color = color)
            gui.drawStroke(s, width = 1, color = "#000000")
#-------------------------------------
# if executed by itself, run all the doc tests

if __name__ == "__main__":
    Logger.setDoctest(logger)
    import doctest
    doctest.testmod()

