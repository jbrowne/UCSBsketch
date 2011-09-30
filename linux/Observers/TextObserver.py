"""
filename: TextObserver.py

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

from SketchFramework import SketchGUI
from SketchFramework.Point import Point
from SketchFramework.Stroke import Stroke
from SketchFramework.Board import BoardObserver, BoardSingleton
from SketchFramework.Annotation import Annotation, AnnotatableObject

from xml.etree import ElementTree as ET

logger = Logger.getLogger('TextObserver', Logger.WARN )

#-------------------------------------

class TextAnnotation(Annotation):
    def __init__(self, text, scale):
        "Create a Text annotation. text is the string, and scale is an appropriate size"
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
class _LetterMarker( BoardObserver ):
    """Class initialized by the TextCollector object"""
    def __init__(self):
        BoardObserver.__init__(self)
        BoardSingleton().AddBoardObserver( self )
        BoardSingleton().RegisterForStroke( self )
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
            oAnnotation = TextAnnotation("0", height)
            l_logger.debug("Annotating %s with %s" % ( stroke, oAnnotation))
            BoardSingleton().AnnotateStrokes( [stroke],  oAnnotation)
            l_logger.debug(" Afterward: %s.annotations is %s" % ( stroke, stroke.Annotations))

        elif len(stroke.Points) >= 2 \
            and max(curvatures) < 0.5 \
            and circularity < circularityThresh_1:
                if stroke.Points[0].X < stroke.Points[-1].X + strokeLen / 2.0 \
                and stroke.Points[0].X > stroke.Points[-1].X - strokeLen / 2.0:
                    height = stroke.BoundTopLeft.Y - stroke.BoundBottomRight.Y
                    oneAnnotation = TextAnnotation("1", height)
                    l_logger.debug("Annotating %s with %s" % ( stroke, oneAnnotation.text))
                    BoardSingleton().AnnotateStrokes( [stroke],  oneAnnotation)
                    l_logger.debug(" Afterward: %s.annotations is %s" % ( stroke, stroke.Annotations))
                elif stroke.Points[0].Y < stroke.Points[-1].Y + strokeLen / 2.0 \
                and stroke.Points[0].Y > stroke.Points[-1].Y - strokeLen / 2.0:
                    width = stroke.BoundBottomRight.X - stroke.BoundTopLeft.X 
                    dashAnnotation = TextAnnotation("-", width * 1.5) #Treat the dash's (boosted) width as its scale 
                    l_logger.debug("Annotating %s with %s" % ( stroke, dashAnnotation.text))
                    BoardSingleton().AnnotateStrokes( [stroke],  dashAnnotation)
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
        all_text_annos = set(stroke.findAnnotations(TextAnnotation))
        all_text_strokes = set([])
        for ta in all_text_annos:
            all_text_strokes.update(ta.Strokes)
            BoardSingleton().RemoveAnnotation(ta)

        for s in all_text_strokes:
            if s is not stroke:
                self.onStrokeAdded(s)
        #Handled by collectors
#-------------------------------------
tc_logger = Logger.getLogger("TextCollector", Logger.WARN)

class TextCollector( ObserverBase.Collector ):
    "Watches for strokes that look like text"
    def __init__(self, circularity_threshold=0.90):
        # FIXME: this is for "binary" text right now
        _LetterMarker()
        ObserverBase.Collector.__init__( self, [], TextAnnotation  )

    def mergeCollections( self, from_anno, to_anno ):
        "merge from_anno into to_anno if possible"
        #FIXME: New annotation assumed to be to the right. (Does not handle inserting text in the middle)
        # check that they have compatable scales
        vertOverlapRatio = 0
        horizDistRatio = 2.0
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

        # check that they are next to each other
        if    abs( bb_from[1].X - bb_to[0].X ) > to_anno.scale * horizDistRatio \
          and abs( bb_from[0].X - bb_to[1].X ) > to_anno.scale * horizDistRatio \
          and abs( bb_from[1].X - bb_to[0].X ) > from_anno.scale * horizDistRatio \
          and abs( bb_from[0].X - bb_to[1].X ) > from_anno.scale * horizDistRatio:
            tc_logger.debug("Not merging: horizontal distance too great")
            return False
        # check y's overlap
        if   bb_from[0].Y - bb_to[1].Y < vertOverlapRatio \
          or bb_to[0].Y - bb_from[1].Y < vertOverlapRatio :
            tc_logger.debug("Not merging: vertical overlap too small")
            return False

        # now we know that we want to merge these text annotations
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

#-------------------------------------

class TextVisualizer( ObserverBase.Visualizer ):

    def __init__(self):
        ObserverBase.Visualizer.__init__( self, TextAnnotation )

    def drawAnno( self, a ):
        if len(a.text) > 1:
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
            y -= 15
            for idx, text in enumerate(a.alternates):
                SketchGUI.drawText( br.X, y, text, size=10, color="#a0a0a0" )
                y -= 10

#-------------------------------------
# if executed by itself, run all the doc tests

if __name__ == "__main__":
    Logger.setDoctest(logger) 
    import doctest
    doctest.testmod()
