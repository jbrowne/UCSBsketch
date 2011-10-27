"""
filename: EqualsObserver.py

description:
   This module looks for equal signs

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

logger = Logger.getLogger('TextObserver', Logger.WARN )

#-------------------------------------

class EqualsAnnotation(Annotation):
    def __init__(self, scale):
        "Create a Text annotation. text is the string, and scale is an appropriate size"
        Annotation.__init__(self)
        self.scale = scale # an approximate "size" for the text
    def xml(self):
        root = Annotation.xml(self)
        root.attrib['scale'] = str(self.scale)
        return root

#-------------------------------------

l_logger = Logger.getLogger('EqualsMarker', Logger.WARN)
class EqualsMarker( BoardObserver ):
    """Looks for equals signes"""
    possibleStrokes = []
    def __init__(self):
        BoardObserver.__init__(self)
        BoardSingleton().AddBoardObserver( self )
        BoardSingleton().RegisterForStroke( self )
    def onStrokeAdded(self, stroke):
        "Checks to see if an equals sign has been added"
        
        strokeLen = max(GeomUtils.strokeLength(stroke), 1)
        closedDistRatio = 0.22
        head, tail = stroke.Points[0], stroke.Points[-1]
        isClosedShape = GeomUtils.pointDistanceSquared(head.X, head.Y, tail.X, tail.Y) \
                        < (strokeLen * closedDistRatio) ** 2

        if isClosedShape:
            return

        # check if we have a horizontal line
        if not stroke.Points[0].Y < stroke.Points[-1].Y + strokeLen / 2.0 \
        or not stroke.Points[0].Y > stroke.Points[-1].Y - strokeLen / 2.0 \
        or strokeLen == 1:
            l_logger.debug("-: Not a horizontal line")
        else: # Awesome, we have a horizontal line
                
            # Find the midpoints         
            ul,br = GeomUtils.strokelistBoundingBox( [stroke] )
            midpointY = (ul.Y + br.Y) / 2
            midpointX = (ul.X + br.X) / 2

            for s in self.possibleStrokes:
                preStrokeLen = GeomUtils.strokeLength(s)

                # test the the two segments are of similar length
                lengthRange = 0.4
                if preStrokeLen * (1-lengthRange) < strokeLen < preStrokeLen * (1+lengthRange):
                    pass # were the right lenght
                else: # not the right length, so lets start again
                    continue

                ul,br = GeomUtils.strokelistBoundingBox( [s] )
                prevMidpointY = (ul.Y + br.Y) / 2
                prevMidpointX = (ul.X + br.X) / 2

                # Test that the two segments are close enough horizontally
                if GeomUtils.pointDistance(midpointX, 0, prevMidpointX, 0) < preStrokeLen * 0.4:
                    pass # there are close enough horizontally
                else: # we start again
                    continue

                # Test that the two segments are close enough vertically
                if GeomUtils.pointDistance(0,midpointY, 0, prevMidpointY) < preStrokeLen * 0.5:
                    pass # there are close enough vertically
                else: # we start again
                    continue

                # we found a match
                self.possibleStrokes.remove(s)
                BoardSingleton().AnnotateStrokes( [stroke, s],  EqualsAnnotation(1))
                return

            # no match was found, add to the list of possible
            self.possibleStrokes.append(stroke)
            return
                    

#-------------------------------------

class EqualsVisualizer( ObserverBase.Visualizer ):

    def __init__(self):
        ObserverBase.Visualizer.__init__( self, EqualsAnnotation )

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
        
        SketchGUI.drawText( br.X - 15, br.Y, "=", size=15, color="#a0a0a0" )

#-------------------------------------
# if executed by itself, run all the doc tests

if __name__ == "__main__":
    Logger.setDoctest(logger)
    import doctest
    doctest.testmod()



