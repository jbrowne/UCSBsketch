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
    def __init__(self, text, stroke_letter_map, scale):
        """Create a Text annotation. text is the string, stroke_letter_map bins 
        strokes according to the letter they're associated with, 
        e.g. "Hi" : [ [<strokes for 'H'>], [<strokes for 'i'>] ]. 
        scale is an appropriate size"""
        Annotation.__init__(self)
        self.text = text # a string for the text
        self.letter2strokesMap = stroke_letter_map
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
        BoardSingleton().AddBoardObserver( self , [TextAnnotation])
        BoardSingleton().RegisterForStroke( self )

    def _makeZeroAnnotation(self, strokelist):
        """Take in a list of strokes and return a TextAnnotation with them marked as "0"""
        bb = GeomUtils.strokelistBoundingBox(strokelist)
        height = bb[0].Y - bb[1].Y
        oAnnotation = TextAnnotation("0", [strokelist], height)
        return oAnnotation

    def _makeOneAnnotation(self, strokelist):
        bb = GeomUtils.strokelistBoundingBox(strokelist)
        height = bb[0].Y - bb[1].Y
        oneAnnotation = TextAnnotation("1", [strokelist], height)
        return oneAnnotation
    
    def _makeDashAnnotation(self, strokelist):
        bb = GeomUtils.strokelistBoundingBox(strokelist)
        width = bb[1].X - bb[0].X 
        dashAnnotation = TextAnnotation("-", [strokelist], width * 1.2) #Treat the dash's (boosted) width as its scale 
        return dashAnnotation
        
    def onStrokeAdded(self, stroke):
        "Tags 1's, dashes and 0's as letters (TextAnnotation)"
        strokelist = [stroke]
        if _scoreStrokesForLetter(strokelist, '0') > 0.9:
            oAnnotation = self._makeZeroAnnotation(strokelist)
            l_logger.debug("Annotating %s with %s" % ( stroke, oAnnotation))
            BoardSingleton().AnnotateStrokes( strokelist,  oAnnotation)

        if _scoreStrokesForLetter(strokelist, '1') > 0.9:
            oneAnnotation = self._makeOneAnnotation(strokelist)
            l_logger.debug("Annotating %s with %s" % ( stroke, oneAnnotation.text))
            BoardSingleton().AnnotateStrokes( strokelist,  oneAnnotation)

        if _scoreStrokesForLetter(strokelist, '-') > 0.9:
            dashAnnotation = self._makeDashAnnotation(strokelist)
            l_logger.debug("Annotating %s with %s" % ( stroke, dashAnnotation.text))
            BoardSingleton().AnnotateStrokes( strokelist,  dashAnnotation)

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

def _getAllConfidenceScores(strokelist):
    """Get the per-letter confidence scores for a group of strokes, normalized 0.0 - 1.0.
    Returned as a dict {<letter> : <score>}"""
    confidenceDict = {}
    for letter in ['0', '1', '-']:
        confidenceDict[letter] = _scoreStrokesForLetter(strokelist, letter)
    return confidenceDict
        
def _scoreStrokesForLetter(strokelist, letter):
    """Get the confidence score for a group of strokes matching a letter, normalized [0.0-1.0]"""
    retConfidence = 0.0
    #Recognition thresholds
    closedDistRatio = 0.22
    circularityThresh_0 = 0.80
    circularityThresh_1 = 0.20
    maxStraightCurvature = 0.6

    if len(strokelist) == 0:
        return 0.0
    #Recognize a zero
    if letter.upper() == "0":
        stroke = strokelist[0]
        strokeLen = max(GeomUtils.strokeLength(stroke), 1)
        normDist = max(3, strokeLen / 5) #granularity of point spacing -- at least 3
        head, tail = stroke.Points[0], stroke.Points[-1]

        endDist = GeomUtils.pointDistance(head.X, head.Y, tail.X, tail.Y)
        #If the endpoints are 1/thresh apart, actually close the thing
        isClosedShape = GeomUtils.pointDistanceSquared(head.X, head.Y, tail.X, tail.Y) \
                        < ( (strokeLen * closedDistRatio) ** 2 )

        if isClosedShape: #Close the shape back up
            s_norm = GeomUtils.strokeNormalizeSpacing( Stroke(stroke.Points + [stroke.Points[0]]) , normDist ) 
        else:
            s_norm = GeomUtils.strokeNormalizeSpacing( stroke , normDist ) 
        #curvatures = GeomUtils.strokeGetPointsCurvature(s_norm)
        circularity = GeomUtils.strokeCircularity( s_norm ) 

        if isClosedShape:
            retConfidence += 0.5
        if circularity > circularityThresh_0:
            retConfidence += 0.5
        return retConfidence
    #Recognize a one
    elif letter.upper() == "1":
        stroke = strokelist[0]
        strokeLen = max(GeomUtils.strokeLength(stroke), 1)
        normDist = max(3, strokeLen / 5) #granularity of point spacing -- at least 3
        s_norm = GeomUtils.strokeNormalizeSpacing( stroke , normDist ) 

        circularity = GeomUtils.strokeCircularity( s_norm ) 
        curvatures = GeomUtils.strokeGetPointsCurvature(s_norm)
        if max(curvatures) < maxStraightCurvature:
            retConfidence += 0.30
        if circularity < circularityThresh_1:
            retConfidence += 0.5
            if stroke.Points[0].X < stroke.Points[-1].X + strokeLen / 2.0 \
            and stroke.Points[0].X > stroke.Points[-1].X - strokeLen / 2.0:
                retConfidence += 0.2
        return retConfidence
    #Recognize a dash
    elif letter.upper() == "-":
        stroke = strokelist[0]
        strokeLen = max(GeomUtils.strokeLength(stroke), 1)
        normDist = max(3, strokeLen / 5) #granularity of point spacing -- at least 3
        s_norm = GeomUtils.strokeNormalizeSpacing( stroke , normDist ) 

        circularity = GeomUtils.strokeCircularity( s_norm ) 
        curvatures = GeomUtils.strokeGetPointsCurvature(s_norm)
        if max(curvatures) < maxStraightCurvature:
            retConfidence += 0.30
        if circularity < circularityThresh_1:
            retConfidence += 0.5
            if stroke.Points[0].Y < stroke.Points[-1].Y + strokeLen / 2.0 \
            and stroke.Points[0].Y > stroke.Points[-1].Y - strokeLen / 2.0:
                retConfidence += 0.2
        return retConfidence
    else:
        return 0.0
#-------------------------------------
tc_logger = Logger.getLogger("TextCollector", Logger.DEBUG)

class TextCollector( ObserverBase.Collector ):
    "Watches for strokes that look like text"
    def __init__(self, circularity_threshold=0.90):
        # FIXME: this is for "binary" text right now
        self.letterMarker = _LetterMarker()
        ObserverBase.Collector.__init__( self, [], TextAnnotation  )

    def onAnnotationSuggested(self, anno_type, strokelist):
        """Called when the a list of strokes are suggested to yield an annotation of type anno_type."""
        tc_logger.debug("Dealing with suggested %s" % (anno_type.__name__))
        assert anno_type == TextAnnotation
        for stk in strokelist:
            annos = stk.findAnnotations(annoType=anno_type)
            if len(annos) > 0:
                continue
            else:
                singleStrokeList = [stk]
                confList = sorted(_getAllConfidenceScores(singleStrokeList).items(), key=lambda pair: pair[1])
                best = confList[-1]
                tc_logger.debug("Letter confidences %s" % (confList))
                if best[0] == "0":
                    oAnnotation = self.letterMarker._makeZeroAnnotation(singleStrokeList)
                    tc_logger.debug("Annotating %s with %s" % ( singleStrokeList, oAnnotation))
                    BoardSingleton().AnnotateStrokes( singleStrokeList,  oAnnotation)

                elif best[0] == "1":
                    oneAnnotation = self.letterMarker._makeOneAnnotation(singleStrokeList)
                    tc_logger.debug("Annotating %s with %s" % ( singleStrokeList, oneAnnotation.text))
                    BoardSingleton().AnnotateStrokes( singleStrokeList,  oneAnnotation)

                elif best[0] == "-":
                    dashAnnotation = self.letterMarker._makeDashAnnotation(singleStrokeList)
                    tc_logger.debug("Annotating %s with %s" % ( singleStrokeList, dashAnnotation.text))
                    BoardSingleton().AnnotateStrokes( singleStrokeList,  dashAnnotation)


    def mergeCollections( self, from_anno, to_anno ):
        "merge from_anno into to_anno if possible"
        # check that they have compatable scales
        vertOverlapRatio = 0
        horizDistRatio = 2.0
        scaleDiffRatio = 2.0
        scale_diff = to_anno.scale / from_anno.scale
        if scale_diff> scaleDiffRatio or 1/float( scale_diff ) > scaleDiffRatio :
            tc_logger.debug("Not merging %s and %s: Scale Diff is %s" % (from_anno.text, to_anno.text, scale_diff))
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
            tc_logger.debug("Not merging %s and %s: horizontal distance too great" % (from_anno.text, to_anno.text))
            return False
        # check y's overlap
        if   bb_from[0].Y - bb_to[1].Y < vertOverlapRatio \
          or bb_to[0].Y - bb_from[1].Y < vertOverlapRatio :
            tc_logger.debug("Not merging %s and %s: vertical overlap too small" % (from_anno.text, to_anno.text))
            return False

        # Order the letters properly from left to right
        out_letter_stroke_map = []
        outText = ""
        from_idx = 0
        to_idx = 0
        while len(outText) < len(from_anno.text) + len(to_anno.text):
            if from_idx < len(from_anno.letter2strokesMap) and from_idx < len(from_anno.text):
                letter_bb_from = GeomUtils.strokelistBoundingBox(from_anno.letter2strokesMap[from_idx])
            else:
                letter_bb_from = None
                
            if to_idx < len(to_anno.letter2strokesMap) and to_idx < len(to_anno.text):
                letter_bb_to = GeomUtils.strokelistBoundingBox(to_anno.letter2strokesMap[to_idx])
            else:
                letter_bb_to = None

            if letter_bb_to is None and letter_bb_from is None:
                logger.warn("Trying to merge beyond available letters")
                break
            elif letter_bb_to is None or \
                   (letter_bb_from is not None and letter_bb_from[0].X < letter_bb_to[0].X ):
                outText += from_anno.text[from_idx]
                out_letter_stroke_map.append(from_anno.letter2strokesMap[from_idx])
                from_idx += 1
            elif letter_bb_from is None or \
                   (letter_bb_to is not None and letter_bb_to[0].X <= letter_bb_from[0].X):
                outText += to_anno.text[to_idx]
                out_letter_stroke_map.append(to_anno.letter2strokesMap[to_idx])
                to_idx += 1

        #Weight the scale per letter
        to_anno.scale = ( to_anno.scale * len(to_anno.text) + from_anno.scale * len(from_anno.text) )\
                        / float(len(to_anno.text) + len(from_anno.text))
        tc_logger.debug("MERGED: %s and %s to %s" % (to_anno.text, from_anno.text, outText))
        to_anno.text = outText
        to_anno.letter2strokesMap = out_letter_stroke_map
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
