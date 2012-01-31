"""
filename: ExpressionCollector.py

description:
   This module looks for expressions

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


from Observers.NumberObserver import NumAnnotation
from Bin.PlusObserver import PlusAnnotation
from Bin.MinusObserver import MinusAnnotation
from Bin.DivideObserver import DivideAnnotation
from Bin.MultObserver import MultAnnotation
from Bin.EqualsObserver import EqualsAnnotation
from types import *

logger = Logger.getLogger('TextObserver', Logger.WARN )

#-------------------------------------

class ExpressionAnnotation(Annotation):
    def __init__(self, scale):
        "Create a Text annotation. text is the string, and scale is an appropriate size"
        Annotation.__init__(self)
        self.scale = scale # an approximate "size" for the text
        self.number = None
        self.parent = None
        self.left = None
        self.right = None
        self.op = None

    def getValue(self):
        if self.op == None:
            return float(self.number.text)
        elif self.op.isType(PlusAnnotation):
            return self.left.getValue() + self.right.getValue()
        elif self.op.isType(MinusAnnotation):
            return self.left.getValue() - self.right.getValue()
        elif self.op.isType(DivideAnnotation):
            return self.left.getValue() / self.right.getValue()
        elif self.op.isType(MultAnnotation):
            return self.left.getValue() * self.right.getValue()

    def xml(self):
        root = Annotation.xml(self)
        root.attrib['scale'] = str(self.scale)
        return root

#-------------------------------------

l_logger = Logger.getLogger('EqualsMarker', Logger.WARN)


class ExpressionObserver( BoardObserver ):
    "Watches for binry numbers and equation"
    def __init__(self):
        BoardSingleton().AddBoardObserver( self, [ExpressionAnnotation] )
        BoardSingleton().RegisterForAnnotation( PlusAnnotation, self )
        BoardSingleton().RegisterForAnnotation( MinusAnnotation, self )
        BoardSingleton().RegisterForAnnotation( DivideAnnotation, self )
        BoardSingleton().RegisterForAnnotation( MultAnnotation, self )
        BoardSingleton().RegisterForAnnotation( NumAnnotation, self )
        BoardSingleton().RegisterForAnnotation( ExpressionAnnotation, self )

    expressionAnnotations = []
    opAnnotations = []


    def onAnnotationAdded( self, strokes, annotation ):
        '''
        print "Annotation Added:"
        print annotation
        '''
       
        if annotation.isType(ExpressionAnnotation):
            # check to see if there is an operation to the right of the num
            # and then an expression to the right of that operation
            left = None
            right = None
            op = self.findOnRight(annotation, self.opAnnotations)
            if op != None:
                right = self.findOnRight(op, self.expressionAnnotations)
                if right != None:
                    left = annotation
                    self.expressionAnnotations.remove(right)
            
            # if no expression was found to the right, search to the left
            if left == None:
                op = self.findOnLeft(annotation, self.opAnnotations)
                if op != None:
                    left = self.findOnLeft(op, self.expressionAnnotations)
                    if left != None:
                        right = annotation
                        self.expressionAnnotations.remove(left)
                
            if left != None:
                #print "Num Found"
                #print num
                s =  left.Strokes + op.Strokes + right.Strokes
                ul, br = GeomUtils.strokelistBoundingBox(s)
                e = ExpressionAnnotation(ul.Y - br.Y)
                left.parent = e
                right.parent = e
                e.left = left
                e.right = right
                e.op = op
                self.opAnnotations.remove(op)
                BoardSingleton().AnnotateStrokes(s, e)
                #annotation.scale = ul.Y - br.Y
                #annotation.number = annotation.number + num.number
                #BoardSingleton().UpdateAnnotation(annotation, s)
                #BoardSingleton().RemoveAnnotation(num)
                return

            # This expression can't be added to any of the other parts
            # so we will properly order it then add it to the list of annotations
            top = self.order(annotation)
            print top
            self.expressionAnnotations.append(top)

        elif annotation.isType(NumAnnotation):
            e = ExpressionAnnotation(annotation.scale)
            e.number = annotation
            BoardSingleton().AnnotateStrokes(strokes, e)

        elif annotation.isType(PlusAnnotation):
            self.opAnnotations.append(annotation)
        elif annotation.isType(MinusAnnotation):
            self.opAnnotations.append(annotation)
        elif annotation.isType(DivideAnnotation):
            self.opAnnotations.append(annotation)
        elif annotation.isType(MultAnnotation):
            self.opAnnotations.append(annotation)

    def onAnnotationRemoved( self, annotation ):
        
        print "Annotation Removed:"
        print annotation

        if annotation.isType(NumAnnotation):
            annos = BoardSingleton().FindAnnotations(strokelist = annotation.Strokes)
            for a in annos:
                if a.isType(ExpressionAnnotation) and (a.number == annotation):
                    BoardSingleton().RemoveAnnotation(a)
                    print "removed"
                    break
        if annotation.isType(ExpressionAnnotation):
            if annotation in self.expressionAnnotations:
                self.expressionAnnotations.remove(annotation)

        if annotation.isType(PlusAnnotation):
            if annotation in self.opAnnotations:
                self.opAnnotations.remove(annotation)
        elif annotation.isType(MinusAnnotation):
            if annotation in self.opAnnotations:
                self.opAnnotations.remove(annotation)
        elif annotation.isType(DivideAnnotation):
            if annotation in self.opAnnotations:
                self.opAnnotations.remove(annotation)
        elif annotation.isType(MultAnnotation):
            if annotation in self.opAnnotations:
                self.opAnnotations.remove(annotation) 

    def onAnnotationUpdated( self, annotation ):
        print "Annotation Updated:"
        print annotation
        

        
        if annotation.isType(NumAnnotation):
            annos = BoardSingleton().FindAnnotations(strokelist = annotation.Strokes)
            for a in annos:
                if a.isType(ExpressionAnnotation) and (a.number == annotation):
                    BoardSingleton().UpdateAnnotation(a, annotation.Strokes)
                    break
        
    def findOnRight( self, anno, list):
        bb_e = GeomUtils.strokelistBoundingBox( anno.Strokes )
        center_e = Point( (bb_e[0].X + bb_e[1].X) / 2.0, (bb_e[0].Y + bb_e[1].Y) / 2.0)

        v_offset = anno.scale / 4
        h_offset = anno.scale / 2

        for a in list:
            bb_a = GeomUtils.strokelistBoundingBox( a.Strokes )
            center_a = Point( (bb_a[0].X + bb_a[1].X) / 2.0, (bb_a[0].Y + bb_a[1].Y) / 2.0)

            # is it vertically alligned?
            if not ((center_e.Y < center_a.Y + v_offset) and (center_e.Y > center_a.Y - v_offset)):
                continue

            # is it to the right?
            if center_e.X >= center_a.X:
                continue

            return a

        return None

    def findOnLeft( self, anno, list):
        bb_e = GeomUtils.strokelistBoundingBox( anno.Strokes )
        center_e = Point( (bb_e[0].X + bb_e[1].X) / 2.0, (bb_e[0].Y + bb_e[1].Y) / 2.0)

        v_offset = anno.scale / 4
        h_offset = anno.scale / 2

        for a in list:
            bb_a = GeomUtils.strokelistBoundingBox( a.Strokes )
            center_a = Point( (bb_a[0].X + bb_a[1].X) / 2.0, (bb_a[0].Y + bb_a[1].Y) / 2.0)

            # is it vertically alligned?
            if not ((center_e.Y < center_a.Y + v_offset) and (center_e.Y > center_a.Y - v_offset)):
                continue

            # is it to the Left?
            if center_e.X <= center_a.X:
                continue

            return a

        return None       

    def order(self, anno):
        # if we are a num then we are ordered
        if anno.op == None:
            return anno

        self.order(anno.left)
        self.reverseOrder(anno.right)
        return self.compound(anno)

    def compound(self, anno):
        # The right child is a num so now we are ordered
        if anno.right.op == None:
            return anno

        newParent = anno.right
        newParent.parent = anno.parent

        # this should be the number that is directly to the right of the op for anno
        child = anno.right.left
        newParent.left = anno
        
        anno.right = child
        child.parent = anno
        strokes = anno.left.Strokes + anno.op.Strokes + anno.right.Strokes
        anno.parent = newParent
        
        BoardSingleton().UpdateAnnotation(anno, new_strokes=strokes)

        strokes = newParent.left.Strokes + newParent.op.Strokes + newParent.right.Strokes
        BoardSingleton().UpdateAnnotation(newParent, new_strokes=strokes)

        return self.compound(newParent)

    def reverseOrder(self, anno):
        # if we are a num then we are ordered
        if anno.op == None:
            return anno

        self.order(anno.left)
        self.reverseOrder(anno.right)
        return self.reverseCompound(anno)

    def reverseCompound(self, anno):
        # The left child is a num so now we are ordered
        if anno.left.op == None:
            return anno

        newParent = anno.left
        newParent.parent = anno.parent

        # this should be the number that is directly to the right of the op for anno
        child = anno.left.right
        newParent.right = anno
        
        anno.left = child
        child.parent = anno
        strokes = anno.left.Strokes + anno.op.Strokes + anno.right.Strokes
        anno.parent = newParent
        
        BoardSingleton().UpdateAnnotation(anno, new_strokes=strokes)

        strokes = newParent.left.Strokes + newParent.op.Strokes + newParent.right.Strokes
        BoardSingleton().UpdateAnnotation(newParent, new_strokes=strokes)

        return self.reverseCompound(newParent)

#-------------------------------------

class ExpressionVisualizer( ObserverBase.Visualizer ):

    def __init__(self):
        ObserverBase.Visualizer.__init__( self, ExpressionAnnotation )

    def onAnnotationRemoved(self, annotation):
        "Watches for annotations to be removed" 
        if annotation in self.annotation_list:
            self.annotation_list.remove(annotation)

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
        if a.parent == None:
            if a.getValue().is_integer():
                SketchGUI.drawText( br.X + 10, ul.Y, str(int(a.getValue())), size= int(a.scale), color="#a0a0a0" )
            else:
                SketchGUI.drawText( br.X + 10, ul.Y, str(a.getValue()), size= int(a.scale), color="#a0a0a0" )

#-------------------------------------
