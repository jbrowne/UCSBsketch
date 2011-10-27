"""
filename: EquationCollector.py

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


from Bin.BinObserver import BinAnnotation
from Bin.EqualsObserver import EqualsAnnotation
from types import *

logger = Logger.getLogger('TextObserver', Logger.WARN )

#-------------------------------------

class EquationAnnotation(Annotation):
    def __init__(self, scale, type, number = 0):
        "Create a Text annotation. text is the string, and scale is an appropriate size"
        Annotation.__init__(self)
        self.scale = scale # an approximate "size" for the text
        self.type = type
        self.number = number
    def xml(self):
        root = Annotation.xml(self)
        root.attrib['scale'] = str(self.scale)
        return root

#-------------------------------------

l_logger = Logger.getLogger('EqualsMarker', Logger.WARN)

class EquationObserver( BoardObserver ):
    "Watches for binry numbers and equation"
    def __init__(self):
        BoardSingleton().AddBoardObserver( self )
        BoardSingleton().RegisterForAnnotation( EqualsAnnotation, self )
        BoardSingleton().RegisterForAnnotation( BinAnnotation, self )
        #BoardSingleton().RegisterForAnnotation( EquationAnnotation, self )

    binAnnotations = []
    equalsAnnotations = []
    equationAnnotations = []

    def onAnnotationAdded( self, strokes, annotation ):
        '''
        print "Annotation Added:"
        print annotation
        '''

        if annotation.isType(BinAnnotation):

            bb_a = GeomUtils.strokelistBoundingBox( annotation.Strokes )
            center_a = Point( (bb_a[0].X + bb_a[1].X) / 2.0, (bb_a[0].Y + bb_a[1].Y) / 2.0)
            tl = Point (center_a.X - annotation.scale/ 2.0, center_a.Y + (annotation.scale / 2.0) )
            br = Point (center_a.X + annotation.scale/ 2.0, center_a.Y - (annotation.scale / 2.0) )
            bb_a = (tl, br)

            for a in self.equalsAnnotations:
                bb_e = GeomUtils.strokelistBoundingBox( a.Strokes )
                center_e = Point( (bb_e[0].X + bb_e[1].X) / 2.0, (bb_e[0].Y + bb_e[1].Y) / 2.0)
                tl = Point (center_e.X - a.scale/ 2.0, center_e.Y + (a.scale / 2.0) )
                br = Point (center_e.X + a.scale/ 2.0, center_e.Y - (a.scale / 2.0) )
                bb_e = (tl, br)

                if bb_e[0].X < bb_a[1].X:
                    continue

                if   bb_e[0].Y - bb_a[1].Y < 0 \
                    or bb_a[0].Y - bb_e[1].Y < 0 :
                    continue
                
                # we have a matching stroke
                self.equalsAnnotations.remove(a)
                eAnno = EquationAnnotation(annotation.scale, "X", int(annotation.text,2))
                self.equationAnnotations.append(eAnno)
                BoardSingleton().AnnotateStrokes( a.Strokes + strokes, eAnno )
                return
            # No match, so just add it to the list

            self.binAnnotations.append(annotation)
        elif annotation.isType(EqualsAnnotation):

            bb_e = GeomUtils.strokelistBoundingBox( annotation.Strokes )
            center_e = Point( (bb_e[0].X + bb_e[1].X) / 2.0, (bb_e[0].Y + bb_e[1].Y) / 2.0)
            tl = Point (center_e.X - annotation.scale/ 2.0, center_e.Y + (annotation.scale / 2.0) )
            br = Point (center_e.X + annotation.scale/ 2.0, center_e.Y - (annotation.scale / 2.0) )
            bb_e = (tl, br)

            for a in self.binAnnotations:
                bb_a = GeomUtils.strokelistBoundingBox( a.Strokes )
                center_a = Point( (bb_a[0].X + bb_a[1].X) / 2.0, (bb_a[0].Y + bb_a[1].Y) / 2.0)
                tl = Point (center_a.X - a.scale/ 2.0, center_a.Y + (a.scale / 2.0) )
                br = Point (center_a.X + a.scale/ 2.0, center_a.Y - (a.scale / 2.0) )
                bb_a = (tl, br)

                if bb_e[0].X < bb_a[1].X:
                    continue

                if   bb_e[0].Y - bb_a[1].Y < 0 \
                    or bb_a[0].Y - bb_e[1].Y < 0 :
                    continue
                
                # we have a matching stroke
                self.binAnnotations.remove(a)
                eAnno = EquationAnnotation(a.scale, "X", int(a.text,2))
                self.equationAnnotations.append(eAnno)
                BoardSingleton().AnnotateStrokes( a.Strokes + strokes, eAnno )
                return
            # No match, so just add it to the list
            self.equalsAnnotations.append(annotation)

    def onAnnotationRemoved( self, annotation ):
        '''
        print "Annotation Removed:"
        print annotation
        '''

        if annotation.isType(BinAnnotation) and self.binAnnotations.count(annotation) > 0:
            self.binAnnotations.remove(annotation)
        elif annotation.isType(EqualsAnnotation) and self.equalsAnnotations.count(annotation) > 0:
            self.equalsAnnotations.remove(annotation)
        else:
            pass
            #annos = BoardSingleton().FindAnnotations(strokelist = annotation.Strokes);
            #for a in annos:
            #    if a.isType(EquationAnnotation):
            #        self.equationAnnotations.remove(a)
            #        BoardSingleton().RemoveAnnotation(a)


    def onAnnotationUpdated( self, annotation ):
        '''
        print "Annotation Udated:"
        print annotation
        '''

        if annotation.isType(BinAnnotation):
            annos = BoardSingleton().FindAnnotations(strokelist = annotation.Strokes);
            #print annos
            for a in annos:
                if a.isType(EquationAnnotation):
                    eAnno = EquationAnnotation(annotation.scale, "X", int(annotation.text,2))
                    list = annotation.Strokes
                    for i in a.Strokes:
                        if list.count(i) == 0:
                            list.append(i)
                    self.equationAnnotations.append(eAnno)
                    #print list
                    BoardSingleton().AnnotateStrokes( list, eAnno )
                    #print annotation.Strokes + a.Strokes
                    #BoardSingleton().AnnotateStrokes( annotation.Strokes + a.Strokes, eAnno )
                    self.equationAnnotations.remove(a)
                    BoardSingleton().RemoveAnnotation(a)
            

#-------------------------------------

class EquationVisualizer( ObserverBase.Visualizer ):

    def __init__(self):
        ObserverBase.Visualizer.__init__( self, EquationAnnotation )

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
        #print "Drawing " + a.type + " with number " + str(a.number) + " and scale " + str(int(a.scale))
        if a.type == "X": 
            SketchGUI.drawText( br.X + 10, ul.Y, str(a.number), size= int(a.scale), color="#a0a0a0" )

#-------------------------------------
