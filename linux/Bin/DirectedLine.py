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

from SketchFramework.Point import Point
from SketchFramework.Stroke import Stroke
from SketchFramework.Board import BoardObserver
from SketchFramework.Annotation import Annotation, AnnotatableObject

from xml.etree import ElementTree as ET

logger = Logger.getLogger('TextObserver', Logger.WARN )

class DirectedLineAnnotation(LineObserver.LineAnnotation):
    def __init__(self, linearity, angle, start_point, end_point):
        "Create a Directed annotation"
        LineObserver.LineAnnotation.__init__(self, linearity, angle, start_point, end_point)
    def xml(self):
        root = Annotation.xml(self)
        return root

class H_LineAnnotation(DirectedLineAnnotation):
    def __init__(self, linearity, angle, start_point, end_point):
        "Create a Horizontal Line annotation."
        DirectedLineAnnotation.__init__(self, linearity, angle, start_point, end_point)

class V_LineAnnotation(DirectedLineAnnotation):
    def __init__(self, linearity, angle, start_point, end_point):
        "Create a Vertical Line annotation."
        DirectedLineAnnotation.__init__(self, linearity, angle, start_point, end_point)

class TB_LineAnnotation(DirectedLineAnnotation):
    def __init__(self, linearity, angle, start_point, end_point):
        "Create a Diaganal Line annotation, where the line goes from top to bottom (left to right)."
        DirectedLineAnnotation.__init__(self, linearity, angle, start_point, end_point)

class BT_LineAnnotation(DirectedLineAnnotation):
    def __init__(self, linearity, angle, start_point, end_point):
        "Create a Diaganal Line annotation, where the line goes from bottom to top (left to right)."
        DirectedLineAnnotation.__init__(self, linearity, angle, start_point, end_point)


l_logger = Logger.getLogger('DirectedLineMarker', Logger.WARN)
class DirectedLineMarker( BoardObserver ):
    """Takes a line and annotates it with direction"""

    def __init__(self, board):
        BoardObserver.__init__(self, board)
        self.getBoard().AddBoardObserver( self, [H_LineAnnotation, V_LineAnnotation, TB_LineAnnotation, BT_LineAnnotation] )
        self.getBoard().RegisterForAnnotation( LineObserver.LineAnnotation, self )

    def onAnnotationAdded( self, strokes, annotation ):
        threshold = 10
        d_threshold = 15
        
        a = annotation.angle
        l = annotation.linearity
        sp = annotation.start_point
        ep = annotation.end_point


        if a == 180.0:
            a = 0.0

        print a

        if a > 0 - threshold and a < 0 + threshold:
            self.getBoard().AnnotateStrokes( strokes, H_LineAnnotation(l, a, sp ,ep) )
            print "H-Line"
        elif a > 90 - threshold or a < -90 + threshold:
            self.getBoard().AnnotateStrokes( strokes, V_LineAnnotation(l, a, sp ,ep) )
            print "V-Line"
        elif a > 45 - d_threshold and a < 45 + d_threshold:
            self.getBoard().AnnotateStrokes( strokes, BT_LineAnnotation(l, a, sp ,ep) )
            print "BT-Line"
        elif a > -45 - d_threshold and a < -45 + d_threshold:
            self.getBoard().AnnotateStrokes( strokes, TB_LineAnnotation(l, a, sp ,ep) )
            print "TB-Line"
