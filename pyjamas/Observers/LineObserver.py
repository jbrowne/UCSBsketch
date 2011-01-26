"""
filename: LineObserver.py

description:
   This module implements 3 classes, LineAnnotation (which is applied to any 
   annotableObjects to describe it as a straight line), LineMarker (which watches
   for strokes that looks like lines and adds the line annotation), and
   LineVisualizer (that watches for line annotations and draws the appropriate
   line to the screen)


Doctest Examples:

>>> c = LineMarker()

example of something that is a line
>>> linepoints = [Point(x,2*x) for x in range(1,5)] 
>>> c.onStrokeAdded(Stroke(linepoints))

example of something is not a line
>>> circlepoints = [(int(math.sin(math.radians(x))*100+200),int(math.cos(math.radians(x))*100)+200) for x in range(0,360,20)]
>>> c.onStrokeAdded(Stroke(circlepoints))

"""

#-------------------------------------

import math
from Utils import Logger
from Utils import GeomUtils

from SketchFramework import SketchGUI
from SketchFramework.Point import Point
from SketchFramework.Stroke import Stroke
from SketchFramework.Board import BoardObserver, BoardSingleton
from SketchFramework.Annotation import Annotation, AnnotatableObject

logger = Logger.getLogger('LineObserver', Logger.WARN )

#-------------------------------------

class LineAnnotation(Annotation):
    def __init__(self, linearity, angle, start_point, end_point ):
        Annotation.__init__(self) 
        self.linearity = linearity
        self.angle = angle
        self.start_point = start_point
        self.end_point = end_point

#-------------------------------------

class LineMarker( BoardObserver ):
    "Watches for lines, and annotates them with the linearity and angle"
    def __init__(self, linearity_threshold=0.85):
        BoardSingleton().AddBoardObserver( self )
        BoardSingleton().RegisterForStroke( self )
	self.threshold = linearity_threshold;

    def onStrokeAdded( self, stroke ):
        "Watches for Strokes with Circularity > threshold to Annotate"
        # need at least 6 points to be a line
        if stroke.get_length()<6:
            return

        linearity = GeomUtils.strokeLinearity( stroke )
        angle = GeomUtils.strokeOrientation( stroke )
        
        if( linearity > self.threshold ):
            lanno = LineAnnotation( linearity, angle, stroke.Points[0], stroke.Points[-1] )
            BoardSingleton().AnnotateStrokes( [stroke], lanno )

    def onStrokeRemoved(self, stroke):
	"When a stroke is removed, remove line annotation if found"
    	for anno in stroke.findAnnotations(LineAnnotation, True):
            BoardSingleton().RemoveAnnotation(anno)

#-------------------------------------

class LineVisualizer( BoardObserver ):
    "Watches for Line annotations, draws them"
    def __init__(self):
        BoardSingleton().AddBoardObserver( self )
        BoardSingleton().RegisterForAnnotation( LineAnnotation, self )
        self.annotation_list = []

    def onAnnotationAdded( self, strokes, annotation ):
        "Watches for annotations of Lines and tracks them" 
        logger.debug( "A Line was annotated with (lin=%f, ang=%f)", annotation.linearity, annotation.angle )
        self.annotation_list.append(annotation)

    def onAnnotationRemoved(self, annotation):
        "Watches for annotations to be removed" 
        self.annotation_list.remove(annotation)

    def drawMyself( self ):
	for a in self.annotation_list:
            SketchGUI.drawLine( a.start_point.X, a.start_point.Y, a.end_point.X, a.end_point.Y,  color="#ddaaff", width=2.0)

#-------------------------------------
# if executed by itself, run all the doc tests

if __name__ == "__main__":
    Logger.setDoctest(logger) 
    import doctest
    doctest.testmod()
