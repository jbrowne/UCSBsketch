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

from Observers import CircleObserver
from Observers import LineObserver
from Observers import ObserverBase

from SketchFramework.Point import Point
from SketchFramework.Stroke import Stroke
from SketchFramework.Board import BoardObserver
from SketchFramework.Annotation import Annotation, AnnotatableObject

from xml.etree import ElementTree as ET


logger = Logger.getLogger('TextObserver', Logger.WARN )

#-------------------------------------

class BinAnnotation(Annotation):
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
class _BinMarker( BoardObserver ):
    """Class initialized by the TextCollector object"""
    def __init__(self, board):
        BoardObserver.__init__(self, board)
        self.getBoard().AddBoardObserver( self )
        self.getBoard().RegisterForStroke( self )
    def onStrokeAdded(self, stroke):
        "Tags 1's and 0's as letters (TextAnnotation)"
        closedDistRatio = 0.22
        circularityThresh_0 = 0.80
        circularityThresh_1 = 0.20
        strokeLen = max(GeomUtils.strokeLength(stroke), 1)
        normDist = max(3, strokeLen / 5)
        head, tail = stroke.Points[0], stroke.Points[-1]

        endDist = GeomUtils.pointDistance(head.X, head.Y, tail.X, tail.Y)
        #If the endpoints are 1/thresh apart, actually close the thing
        isClosedShape = GeomUtils.pointDistanceSquared(head.X, head.Y, tail.X, tail.Y) \
                        < (strokeLen * closedDistRatio) ** 2

        if isClosedShape: #Close the shape back up
            s_norm = GeomUtils.strokeNormalizeSpacing( Stroke(stroke.Points + [stroke.Points[0]]) , normDist )
        else:
            s_norm = GeomUtils.strokeNormalizeSpacing( stroke , normDist )
        curvatures = GeomUtils.strokeGetPointsCurvature(s_norm)
        circularity = GeomUtils.strokeCircularity( s_norm )

        if isClosedShape and circularity > circularityThresh_0:
            height = stroke.BoundTopLeft.Y - stroke.BoundBottomRight.Y
            oAnnotation = BinAnnotation("0", height)
            l_logger.debug("Annotating %s with %s" % ( stroke, oAnnotation))
            self.getBoard().AnnotateStrokes( [stroke],  oAnnotation)

        elif len(stroke.Points) >= 2 \
            and max(curvatures) < 0.5 \
            and circularity < circularityThresh_1:
                if stroke.Points[0].X < stroke.Points[-1].X + strokeLen / 2.0 \
                and stroke.Points[0].X > stroke.Points[-1].X - strokeLen / 2.0:
                    height = stroke.BoundTopLeft.Y - stroke.BoundBottomRight.Y
                    oneAnnotation = BinAnnotation("1", height)
                    l_logger.debug("Annotating %s with %s" % ( stroke, oneAnnotation.text))
                    self.getBoard().AnnotateStrokes( [stroke],  oneAnnotation)
                elif stroke.Points[0].Y < stroke.Points[-1].Y + strokeLen / 2.0 \
                and stroke.Points[0].Y > stroke.Points[-1].Y - strokeLen / 2.0:
                    # we don't care about "-" (yet)
                    return
        else:
            if not isClosedShape:
                l_logger.debug("0: Not a closed shape")
            if not (circularity > circularityThresh_0):
                l_logger.debug("0: Not circular enough: %s" % (circularity))
            if not len(stroke.Points) >= 2:
                l_logger.debug("1: Not enough points")
            if not (circularity < circularityThresh_1):
                l_logger.debug("1: Too circular")
            if not (max(curvatures) < 0.5):
                l_logger.debug("1: Max curvature too big %s" % max(curvatures))
            if not ( stroke.Points[0].X < stroke.Points[-1].X + strokeLen / 3 \
               and   stroke.Points[0].X > stroke.Points[-1].X - strokeLen / 3):
                l_logger.debug("1: Not vertical enough: \nX1 %s, \nX2 %s, \nLen %s" % (stroke.Points[0].X, stroke.Points[-1].X, strokeLen))


    def onStrokeRemoved(self, stroke):
        all_text_annos = set(stroke.findAnnotations(BinAnnotation))
        all_text_strokes = set([])
        for ta in all_text_annos:
            all_text_strokes.update(ta.Strokes)
            self.getBoard().RemoveAnnotation(ta)

        for s in all_text_strokes:
            if s is not stroke:
                self.onStrokeAdded(s)
        #Handled by collectors
#-------------------------------------
tc_logger = Logger.getLogger("TextCollector", Logger.WARN)

class BinCollector( ObserverBase.Collector ):
    "Watches for strokes that look like text"
    def __init__(self, board, circularity_threshold=0.90):
        _BinMarker()
        ObserverBase.Collector.__init__(self, board, [], BinAnnotation  )

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

        # check if from is inserted somewhere inside to
        for i in range(len(to_anno.Strokes)):
            if self.isToRight(to_anno.Strokes[i], first, to_anno.scale)\
            and self.isToLeft(to_anno.Strokes[i+1], last, to_anno.scale):
                return self.merg(to_anno, from_anno)

        return False


#-------------------------------------

class BinVisualizer( ObserverBase.Visualizer ):

    def __init__(self, board):
        ObserverBase.Visualizer.__init__( self, board, BinAnnotation )

    def drawAnno( self, a ):
        ul,br = GeomUtils.strokelistBoundingBox( a.Strokes )
        logger.debug(a.Strokes)
        height = ul.Y - br.Y
        midpointY = (ul.Y + br.Y) / 2
        midpointX = (ul.X + br.X) / 2
        left_x = midpointX - a.scale / 2.0
        right_x = midpointX + a.scale / 2.0
        #self.getBoard().getGUI().drawLine( left_x, midpointY, right_x, midpointY, color="#a0a0a0")
        y = br.Y
        self.getBoard().getGUI().drawText( br.X, y, a.text, size=15, color="#a0a0a0" )

#-------------------------------------
# if executed by itself, run all the doc tests

if __name__ == "__main__":
    Logger.setDoctest(logger)
    import doctest
    doctest.testmod()

