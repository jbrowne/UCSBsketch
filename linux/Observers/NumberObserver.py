"""
filename: BinObserver.py

description:
   This module implements 3 classes, TextAnnotation (which is applied to any 
   set of annotableObjects to describe it as a a block of text), TextMarker (which watches
   for strokes that looks like text and adds the text annotation), and
   TextVisualizer (that watches for text annotations and draws the appropriate
   text box to the screen)


Doctest Examples:

>>> t = TextMarker()

"""

#-------------------------------------

import pdb
import math
from Utils import Logger
from Utils import GeomUtils

from Observers import ObserverBase
from Observers import RubineObserver

from SketchFramework import SketchGUI
from SketchFramework.Point import Point
from SketchFramework.Stroke import Stroke
from SketchFramework.Board import BoardObserver, BoardSingleton
from SketchFramework.Annotation import Annotation, AnnotatableObject

from xml.etree import ElementTree as ET


logger = Logger.getLogger('TextObserver', Logger.WARN )

#-------------------------------------

class NumAnnotation(Annotation):
    def __init__(self, text, scale):
        "Create a Bin annotation. text is the string, and scale is an appropriate size"
        Annotation.__init__(self)
        self.text = text # a string for the text
        self.scale = scale # an approximate "size" for the text
        self.alternates = [text]
    def xml(self):
        root = Annotation.xml(self)
        root.attrib["text"] = self.text
        root.attrib['scale'] = str(self.scale)
        for i, a in enumerate(self.alternates):
            textEl = ET.SubElement(root, "alt")
            textEl.attrib['priority'] = str(i)
            textEl.attrib['text'] = str(a)
            root.append(textEl)
        return root

#-------------------------------------

l_logger = Logger.getLogger('LetterMarker', Logger.WARN)
class _NumMarker( BoardObserver ):
    """Class initialized by the TextCollector object"""
    def __init__(self):
        BoardObserver.__init__(self)
        BoardSingleton().AddBoardObserver( self, [NumAnnotation] )
        BoardSingleton().RegisterForAnnotation( RubineObserver.RubineAnnotation, self )
    
    def onAnnotationAdded( self, strokes, annotation ):
        BoardSingleton().AnnotateStrokes(strokes, NumAnnotation(annotation.type, annotation.scale) )        

#-------------------------------------
tc_logger = Logger.getLogger("TextCollector", Logger.WARN)

class NumCollector( ObserverBase.Collector ):
    "Watches for strokes that look like text"
    def __init__(self, circularity_threshold=0.90):
        _NumMarker()
        ObserverBase.Collector.__init__( self, [], NumAnnotation  )

    horizDistRatio = 1.0

    def getSortItem(self, stroke):
        return GeomUtils.strokelistBoundingBox( [stroke] )[0].X

    def isToLeft(self, stroke_to, stroke_from, scale):
        '''
            if from is to the left of to
        '''

        bb_from = GeomUtils.strokelistBoundingBox( [stroke_from] )
        center_from = Point( (bb_from[0].X + bb_from[1].X) / 2.0, (bb_from[0].Y + bb_from[1].Y) / 2.0)

        bb_to = GeomUtils.strokelistBoundingBox( [stroke_to] )
        center_to = Point( (bb_to[0].X + bb_to[1].X) / 2.0, (bb_to[0].Y + bb_to[1].Y) / 2.0)

        if 0 < center_to.X - center_from.X < self.horizDistRatio * scale:
            return True

        return False

    def isToRight(self, stroke_to, stroke_from, scale):
        '''
            if from is to the right of to
        '''

        bb_from = GeomUtils.strokelistBoundingBox( [stroke_from] )
        center_from = Point( (bb_from[0].X + bb_from[1].X) / 2.0, (bb_from[0].Y + bb_from[1].Y) / 2.0)

        bb_to = GeomUtils.strokelistBoundingBox( [stroke_to] )
        center_to = Point( (bb_to[0].X + bb_to[1].X) / 2.0, (bb_to[0].Y + bb_to[1].Y) / 2.0)

        if 0 < center_from.X - center_to.X < self.horizDistRatio * scale:
            return True

        return False

    def merg(self, to_anno, from_anno):

        bb_from = GeomUtils.strokelistBoundingBox( from_anno.Strokes )
        center_from = Point( (bb_from[0].X + bb_from[1].X) / 2.0, (bb_from[0].Y + bb_from[1].Y) / 2.0)
        tl = Point (center_from.X - from_anno.scale/ 2.0, center_from.Y + (from_anno.scale / 2.0) )
        br = Point (center_from.X + from_anno.scale/ 2.0, center_from.Y - (from_anno.scale / 2.0) )
        bb_from = (tl, br)

        bb_to = GeomUtils.strokelistBoundingBox( to_anno.Strokes )
        center_to = Point( (bb_to[0].X + bb_to[1].X) / 2.0, (bb_to[0].Y + bb_to[1].Y) / 2.0)
        tl = Point (center_to.X - to_anno.scale/ 2.0, center_to.Y + (to_anno.scale / 2.0) )
        br = Point (center_to.X + to_anno.scale/ 2.0, center_to.Y - (to_anno.scale / 2.0) )
        bb_to = (tl, br)

        if bb_from[0].X - bb_to[0].X > 0 :
            outText = to_anno.text + from_anno.text
        else :
            outText = from_anno.text + to_anno.text

        #Weight the scale per letter
        to_anno.scale = ( to_anno.scale * len(to_anno.text) + from_anno.scale * len(from_anno.text) )\
                        / float(len(to_anno.text) + len(from_anno.text))
        tc_logger.debug("MERGED: %s and %s to %s" % (to_anno.text, from_anno.text, outText))
        to_anno.text = outText
        to_anno.alternates = []

        return True

    def mergeCollections( self, from_anno, to_anno ):
        "merge from_anno into to_anno if possible"
        #FIXME: New annotation assumed to be to the right. (Does not handle inserting text in the middle)
        # check that they have compatable scales
        vertOverlapRatio = 0
        scaleDiffRatio = 1.5
        scale_diff = to_anno.scale / from_anno.scale
        if scale_diff> scaleDiffRatio or 1/float( scale_diff ) > scaleDiffRatio :
            tc_logger.debug("Not merging %s and %s: Scale Diff is %s" % (to_anno.text, from_anno.text, scale_diff))
            return False
        # check that they are not overlapping
        bb_from = GeomUtils.strokelistBoundingBox( from_anno.Strokes )
        center_from = Point( (bb_from[0].X + bb_from[1].X) / 2.0, (bb_from[0].Y + bb_from[1].Y) / 2.0)
        tl = Point (center_from.X - from_anno.scale/ 2.0, center_from.Y + (from_anno.scale / 2.0) )
        br = Point (center_from.X + from_anno.scale/ 2.0, center_from.Y - (from_anno.scale / 2.0) )
        bb_from = (tl, br)

        bb_to = GeomUtils.strokelistBoundingBox( to_anno.Strokes )
        center_to = Point( (bb_to[0].X + bb_to[1].X) / 2.0, (bb_to[0].Y + bb_to[1].Y) / 2.0)
        tl = Point (center_to.X - to_anno.scale/ 2.0, center_to.Y + (to_anno.scale / 2.0) )
        br = Point (center_to.X + to_anno.scale/ 2.0, center_to.Y - (to_anno.scale / 2.0) )
        bb_to = (tl, br)
        """
        if not GeomUtils.boundingboxOverlap( bb_from, bb_to ):
            tc_logger.debug("Not merging Bounding boxes don't overlap")
            return False
        """

        #  bb[0]-------+
        #   |          |
        #   |          |
        #   | (0,0)    |
        #   +--------bb[1]

        # check y's overlap
        if   bb_from[0].Y - bb_to[1].Y < vertOverlapRatio \
          or bb_to[0].Y - bb_from[1].Y < vertOverlapRatio :
            tc_logger.debug("Not merging: vertical overlap too small")
            return False

        # sort the strokes so they are in order from left to right
        to_anno.Strokes.sort(key = self.getSortItem);
        from_anno.Strokes.sort(key = self.getSortItem);
        first = from_anno.Strokes[0] # left most
        last = from_anno.Strokes[len(from_anno.Strokes)-1] # right most

        # check if from to the left of to?
        if self.isToLeft(to_anno.Strokes[0], last, to_anno.scale):
            return self.merg(to_anno, from_anno)

        # check if from is to the right of to?
        if self.isToRight(to_anno.Strokes[len(to_anno.Strokes)-1], first, to_anno.scale):
            return self.merg(to_anno, from_anno)

        '''
        # check if from is inserted somewhere inside to
        for i in range(len(to_anno.Strokes)):
            if self.isToRight(to_anno.Strokes[i], first, to_anno.scale)\
            and self.isToLeft(to_anno.Strokes[i+1], last, to_anno.scale):
                return self.merg(to_anno, from_anno)
        '''

        return False


#-------------------------------------

class NumVisualizer( ObserverBase.Visualizer ):

    def __init__(self):
        ObserverBase.Visualizer.__init__( self, NumAnnotation )

    def onAnnotationRemoved(self, annotation):
        "Watches for annotations to be removed"
        if annotation in self.annotation_list:
            self.annotation_list.remove(annotation)

    def drawAnno( self, a ):
        ul,br = GeomUtils.strokelistBoundingBox( a.Strokes )
        logger.debug(a.Strokes)
        height = ul.Y - br.Y
        midpointY = (ul.Y + br.Y) / 2
        midpointX = (ul.X + br.X) / 2
        left_x = midpointX - a.scale / 2.0
        right_x = midpointX + a.scale / 2.0
        #SketchGUI.drawLine( left_x, midpointY, right_x, midpointY, color="#a0a0a0")
        y = br.Y
        SketchGUI.drawText( br.X, y, a.text, size=15, color="#a0a0a0" )

#-------------------------------------
# if executed by itself, run all the doc tests

if __name__ == "__main__":
    Logger.setDoctest(logger)
    import doctest
    doctest.testmod()

