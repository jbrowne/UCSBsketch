"""
filename: CircleObserver.py

description:
   This module implements 3 classes, CircleAnnotation (which is applied to any 
   annotableObjects to describe it as a circle), CircleMarker (which watches
   for strokes that looks like circles and adds the circle annotation), and
   CircleVisualizer (that watches for circle annotations and draws the appropriate
   circles to the screen)


Doctest Examples:

>>> c = CircleMarker()

example of something not a circle
>>> linepoints = [Point(x,2*x) for x in range(1,5)] 
>>> c.onStrokeAdded(Stroke(linepoints))

example of something is a circle
>>> circlepoints = [(int(math.sin(math.radians(x))*100+200),int(math.cos(math.radians(x))*100)+200) for x in range(0,360,20)]
>>> c.onStrokeAdded(Stroke(circlepoints))

"""

#-------------------------------------

import math
import sys
from SketchFramework import SketchGUI

from Utils import Logger
from Utils import GeomUtils
from SketchFramework.Point import Point
from SketchFramework.Stroke import Stroke
from SketchFramework.Board import BoardObserver, BoardSingleton
from SketchFramework.Annotation import Annotation, AnnotatableObject

from xml.etree import ElementTree as ET

logger = Logger.getLogger('CircleObserver', Logger.WARN )

#-------------------------------------

class CircleAnnotation(Annotation):
    def __init__(self, circ, cen, avgDist):
        Annotation.__init__(self)
        self.circularity = circ # float
        self.center = cen # Point
        self.radius = avgDist # float

    def xml( self ):
        "Returns an element tree object for the XML serialization of this annotation"
        root = Annotation.xml(self)

        root.attrib['circularity'] = str(self.circularity)
        root.attrib['x'] = str(self.center.X)
        root.attrib['y'] = str(self.center.Y)
        root.attrib['radius'] = str(self.radius)

        return root

#-------------------------------------

class CircleMarker( BoardObserver ):
    "Watches for Circle, and annotates them with the circularity, center and the radius"
    def __init__(self, circularity_threshold=0.90):
        # TODO: we may wish to add the ability to expose/centralize these thresholds
        # so that they can be tuned differently for various enviornments
        BoardSingleton().AddBoardObserver( self )
        BoardSingleton().RegisterForStroke( self )
	self.threshold = circularity_threshold;

    def onStrokeAdded( self, stroke ):
        "Watches for Strokes with Circularity > threshold to Annotate"
        # need at least 6 points to be a circle
	if stroke.length()<6:
            return
	s_norm = GeomUtils.strokeNormalizeSpacing( stroke, 20 ) 
	s_chop = GeomUtils.strokeChopEnds( s_norm, 0.20 ) 
        circ_norm = GeomUtils.strokeCircularity( s_norm ) 
        circ_chop = GeomUtils.strokeCircularity( s_chop ) 

        logger.debug( "stroke: %s", [str(p) for p in s_norm.Points] )
        logger.debug( "potential circles (%f,%f) <> %f", circ_norm, circ_chop, self.threshold )

        if( circ_norm>self.threshold or circ_chop>self.threshold):
            cen = stroke.Center
            avgDist = GeomUtils.averageDistance( cen, stroke.Points )
            anno = CircleAnnotation( circ_norm, cen, avgDist )
            BoardSingleton().AnnotateStrokes( [stroke],  anno)


    def onStrokeRemoved(self, stroke):
	"When a stroke is removed, remove circle annotation if found"
    	for anno in stroke.findAnnotations(CircleAnnotation, True):
            BoardSingleton().RemoveAnnotation(anno)

#-------------------------------------

class CircleVisualizer( BoardObserver ):
    "Watches for Circle annotations, draws them"
    def __init__(self):
        BoardSingleton().AddBoardObserver( self )
        BoardSingleton().RegisterForAnnotation( CircleAnnotation, self )
        self.annotation_list = []

    def onAnnotationAdded( self, strokes, annotation ):
        "Watches for annotations of Circles and prints out the Underlying Data" 
        logger.debug( "A circle was annotated with Circularity, Center and Radius = %f, (%f,%f), %f", \
	 	annotation.circularity, annotation.center.X, annotation.center.Y, annotation.radius )
        self.annotation_list.append(annotation)

    def onAnnotationRemoved(self, annotation):
        "Watches for annotations to be removed" 
        logger.debug( "A circle annotation was removed with Circularity, Center and Radius = %f, (%f,%f), %f", \
	 	annotation.circularity, annotation.center.X, annotation.center.Y, annotation.radius )
        self.annotation_list.remove(annotation)

    def drawMyself( self ):
	for a in self.annotation_list:
            SketchGUI.drawCircle( a.center.X,a.center.Y, radius=a.radius, color="#bbbbff", width=2.0)

#-------------------------------------
# if executed by itself, run all the doc tests

if __name__ == "__main__":
    Logger.setDoctest(logger) 
    import doctest
    doctest.testmod()
