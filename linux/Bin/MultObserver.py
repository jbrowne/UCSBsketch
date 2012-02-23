"""
filename: MultObserver.py

description:
   This module looks for multtiply signs

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

from SketchFramework.Point import Point
from SketchFramework.Stroke import Stroke
from SketchFramework.Board import BoardObserver
from SketchFramework.Annotation import Annotation, AnnotatableObject

from xml.etree import ElementTree as ET

from Bin import DirectedLine

logger = Logger.getLogger('TextObserver', Logger.WARN )

#-------------------------------------

class MultAnnotation(Annotation):
    def __init__(self, scale):
        "Create a Text annotation. text is the string, and scale is an appropriate size"
        Annotation.__init__(self)
        self.scale = scale # an approximate "size" for the text
    def xml(self):
        root = Annotation.xml(self)
        root.attrib['scale'] = str(self.scale)
        return root

#-------------------------------------

l_logger = Logger.getLogger('MultMarker', Logger.WARN)
class MultMarker( BoardObserver ):
    """Looks for plus signes"""
    possibleAnnotations_BT = []
    possibleAnnotations_TB = []

    def __init__(self, board):
        BoardObserver.__init__(self, board)
        self.getBoard().AddBoardObserver( self, [MultAnnotation])
        self.getBoard().RegisterForAnnotation( DirectedLine.BT_LineAnnotation, self )
        self.getBoard().RegisterForAnnotation( DirectedLine.TB_LineAnnotation, self )
    def onAnnotationAdded( self, strokes, annotation ):
        "Checks to see if an multiply sign has been added"

        # Find the midpoints         
        ul,br = GeomUtils.strokelistBoundingBox( strokes )
        midpointY = (ul.Y + br.Y) / 2
        midpointX = (ul.X + br.X) / 2
        strokeLen = GeomUtils.strokeLength(strokes[0])

        if annotation.isType(DirectedLine.BT_LineAnnotation):
            possibleAnnotations = self.possibleAnnotations_TB
            otherPossibleAnnotations = self.possibleAnnotations_BT
        elif annotation.isType(DirectedLine.TB_LineAnnotation):
            possibleAnnotations = self.possibleAnnotations_BT
            otherPossibleAnnotations = self.possibleAnnotations_TB

        print len(possibleAnnotations)

        for a in possibleAnnotations:
            s = a.Strokes[0]
            prevStrokeLen = GeomUtils.strokeLength(s)

            # test the the two segments are of similar length
            lengthRange = 0.4
            if prevStrokeLen * (1-lengthRange) < strokeLen < prevStrokeLen * (1+lengthRange):
                pass # were the right length
            else: # not the right length, so lets start again
                continue

            ul,br = GeomUtils.strokelistBoundingBox( [s] )
            prevMidpointY = (ul.Y + br.Y) / 2
            prevMidpointX = (ul.X + br.X) / 2

            # Test that the two segments are close enough horizontally
            if GeomUtils.pointDistance(midpointX, 0, prevMidpointX, 0) < prevStrokeLen * 0.25:
                pass # there are close enough horizontally
            else: # we start again
                continue

            # Test that the two segments are close enough vertically
            if GeomUtils.pointDistance(0,midpointY, 0, prevMidpointY) < prevStrokeLen * 0.25:
                pass # there are close enough vertically
            else: # we start again
                continue

            # we found a match
            possibleAnnotations.remove(a)

            annos = s.findAnnotations()

            annos += self.getBoard().FindAnnotations(strokelist = strokes)

            for i in annos:
                self.getBoard().RemoveAnnotation(i)

            ul,br = GeomUtils.strokelistBoundingBox( strokes + [s] )
            height = ul.Y - br.Y
            self.getBoard().AnnotateStrokes( strokes + [s],  MultAnnotation(height))
            return


        # no match was found, add to the list of possible
        otherPossibleAnnotations.append(annotation)
        return
                    

#-------------------------------------

class MultVisualizer( ObserverBase.Visualizer ):

    def __init__(self, board):
        ObserverBase.Visualizer.__init__(self, board, MultAnnotation )

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
        self.getBoard().getGUI().drawBox(ul, br, color="#a0a0a0");
        
        self.getBoard().getGUI().drawText( br.X - 15, br.Y, "X", size=15, color="#a0a0a0" )

#-------------------------------------
# if executed by itself, run all the doc tests

if __name__ == "__main__":
    Logger.setDoctest(logger)
    import doctest
    doctest.testmod()



