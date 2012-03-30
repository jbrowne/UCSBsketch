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
#from Observers.RubineObserver import RubineAnnotation
from Utils import Rubine

from SketchFramework.Point import Point
from SketchFramework.Stroke import Stroke
from SketchFramework.Board import BoardObserver
from SketchFramework.Annotation import Annotation, AnnotatableObject

from xml.etree import ElementTree as ET

logger = Logger.getLogger('TextObserver', Logger.WARN )

#-------------------------------------

class TextAnnotation(Annotation):
    def __init__(self, text, alternates, stroke_letter_map, scale):
        """Create a Text annotation. text is the string, stroke_letter_map bins 
        strokes according to the letter they're associated with, 
        e.g. "Hi" : [ [<strokes for 'H'>], [<strokes for 'i'>] ]. 
        scale is an appropriate size
        alternates is a tuple (indexed by letter) of a list of that letter's alternates"""
        Annotation.__init__(self)
        self.text = text # a string for the text
        assert len(stroke_letter_map) == len(text)
        self.letter2strokesMap = stroke_letter_map
        assert scale > 0.0
        self.scale = scale # an approximate "size" for the text
        self.alternates = alternates #([],) * len(text) # a tuple (indexed per letter) of lists of alternate letters

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
    def __repr__(self):
        return 'Text("%s":%0.2f)' % (self.text, self.scale)

#-------------------------------------
l_logger = Logger.getLogger('LetterMarker', Logger.WARN)
class _LetterMarker( BoardObserver ):
    """Class initialized by the TextCollector object"""
    def __init__(self, board):
        BoardObserver.__init__(self, board) 
        fname = "RL10dash.xml"
        self.getBoard().AddBoardObserver( self , [TextAnnotation])
        self.getBoard().RegisterForStroke( self )
        #self.getBoard().RegisterForAnnotation(  RubineAnnotation , self)

        rubineDataFile = open(fname, "r")
        featureSet = Rubine.BCPFeatureSet()
        self.classifier = Rubine.RubineClassifier(featureSet = featureSet)
        self.classifier.loadWeights(rubineDataFile)
        rubineDataFile.close()


    def _makeLetterAnnotation(self, strokelist, char, alternates):
        bb = GeomUtils.strokelistBoundingBox(strokelist)
        height = bb[0].Y - bb[1].Y
        width = bb[1].X - bb[0].X 
        retAnnotation = TextAnnotation(char,  (alternates,), [strokelist],max(height, width))
        return retAnnotation
    def onStrokeAdded(self, stroke):
        "Tags 1's, dashes and 0's as letters (TextAnnotation)"

        scores = self.classifier.classifyStroke(stroke)
        if len(scores) > 0:
            best = scores[0]['symbol']
            if best in ('R', 'L', '1', '0', '-', 'L'):
                logger.debug("Saw a %s" % (best))
                rAnnotation = self._makeLetterAnnotation( [stroke], best, [s['symbol'] for s in scores])
                l_logger.debug("Annotating %s with %s" % ( stroke, rAnnotation))
                self.getBoard().AnnotateStrokes( [stroke],  rAnnotation)


    def onStrokeRemoved(self, stroke):
        all_text_annos = set(stroke.findAnnotations(TextAnnotation))
        all_text_strokes = set([])
        for ta in all_text_annos:
            all_text_strokes.update(ta.Strokes)
            self.getBoard().RemoveAnnotation(ta)

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
    strokesBB = GeomUtils.strokelistBoundingBox(strokelist)

    if len(strokelist) == 0:
        return 0.0

    #The case of a single point
    if strokesBB[0].X == strokesBB[1].X and strokesBB[0].Y == strokesBB[1].Y:
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
tc_logger = Logger.getLogger("TextCollector", Logger.WARN)

class TextCollector( ObserverBase.Collector ):
    "Watches for strokes that look like text"
    def __init__(self, board, circularity_threshold=0.90):
        # FIXME: this is for "binary" text right now
        self.letterMarker = _LetterMarker(board)
        ObserverBase.Collector.__init__( self, board, [], TextAnnotation  )

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
                    self.getBoard().AnnotateStrokes( singleStrokeList,  oAnnotation)

                elif best[0] == "1":
                    oneAnnotation = self.letterMarker._makeOneAnnotation(singleStrokeList)
                    tc_logger.debug("Annotating %s with %s" % ( singleStrokeList, oneAnnotation.text))
                    self.getBoard().AnnotateStrokes( singleStrokeList,  oneAnnotation)

                elif best[0] == "-":
                    dashAnnotation = self.letterMarker._makeDashAnnotation(singleStrokeList)
                    tc_logger.debug("Annotating %s with %s" % ( singleStrokeList, dashAnnotation.text))
                    self.getBoard().AnnotateStrokes( singleStrokeList,  dashAnnotation)


    def mergeCollections( self, from_anno, to_anno ):
        "merge from_anno into to_anno if possible"
        vertOverlapRatio = 0
        horizDistRatio = 2.3
        scaleDiffRatio = 2.0
        #if from_anno.scale > 0:
            #scale_diff = to_anno.scale / from_anno.scale
            #if scale_diff > scaleDiffRatio or scale_diff < 1/ float(scaleDiffRatio) :
                #tc_logger.debug("Not merging %s and %s: Scale Diff is %s" % (from_anno.text, to_anno.text, scale_diff))
                #return False
            #else:
                #return False

        #  bb[0]-------+
        #   |          |
        #   |          |
        #   | (0,0)    |
        #   +--------bb[1]
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

        # check that they are next to each other
        if    abs( bb_from[1].X - bb_to[0].X ) > to_anno.scale * horizDistRatio \
          and abs( bb_from[0].X - bb_to[1].X ) > to_anno.scale * horizDistRatio \
          and abs( bb_from[1].X - bb_to[0].X ) > from_anno.scale * horizDistRatio \
          and abs( bb_from[0].X - bb_to[1].X ) > from_anno.scale * horizDistRatio:
            #tc_logger.debug("Not merging %s and %s: horizontal distance too great" % (from_anno.text, to_anno.text))
            return False

        # check y's overlap
        if   bb_from[0].Y - bb_to[1].Y < vertOverlapRatio \
          or bb_to[0].Y - bb_from[1].Y < vertOverlapRatio :
            #tc_logger.debug("Not merging %s and %s: vertical overlap too small" % (from_anno.text, to_anno.text))
            return False

        # check that they have compatible scales
        scale_diff1 = to_anno.scale / from_anno.scale
        scale_diff2 = from_anno.scale / to_anno.scale
        if scale_diff1 > scaleDiffRatio or scale_diff2 > scaleDiffRatio:
            tc_logger.debug("Not merging %s and %s: Scale Diff is %s" % (from_anno, to_anno, scale_diff1))
            return False

        # Order the letters properly from left to right
        out_letter_stroke_map = []
        outText = ""
        from_idx = 0
        to_idx = 0
        all_alternates = []
        while len(outText) < len(from_anno.text) + len(to_anno.text):
            #Get the BB for the next letter in from_anno
            if from_idx < len(from_anno.letter2strokesMap) and from_idx < len(from_anno.text):
                letter_bb_from = GeomUtils.strokelistBoundingBox(from_anno.letter2strokesMap[from_idx])
            else:
                letter_bb_from = None
                
            #Get the BB for the next letter in to_anno
            if to_idx < len(to_anno.letter2strokesMap) and to_idx < len(to_anno.text):
                letter_bb_to = GeomUtils.strokelistBoundingBox(to_anno.letter2strokesMap[to_idx])
            else:
                letter_bb_to = None

            if letter_bb_to is None and letter_bb_from is None:
                logger.warn("Trying to merge beyond available letters")
                break
            elif letter_bb_to is None or \
                   (letter_bb_from is not None and letter_bb_from[0].X < letter_bb_to[0].X ):
                #The next letter belongs to from_anno. Merge it
                outText += from_anno.alternates[from_idx][0]
                all_alternates.append(from_anno.alternates[from_idx]) #Merge the alternates for this letter, too
                out_letter_stroke_map.append(from_anno.letter2strokesMap[from_idx])
                from_idx += 1
            elif letter_bb_from is None or \
                   (letter_bb_to is not None and letter_bb_to[0].X <= letter_bb_from[0].X):
                #The next letter belongs to to_anno. Merge it
                outText += to_anno.alternates[to_idx][0]
                all_alternates.append(to_anno.alternates[to_idx]) #Merge the alternates for this letter, too
                out_letter_stroke_map.append(to_anno.letter2strokesMap[to_idx])
                to_idx += 1

        #Weight the scale per letter
        to_anno.scale = ( to_anno.scale * len(to_anno.text) + from_anno.scale * len(from_anno.text) )\
                        / float(len(to_anno.text) + len(from_anno.text))
        tc_logger.debug("MERGED: %s and %s to %s" % (to_anno.text, from_anno.text, outText))
        to_anno.text = outText
        to_anno.letter2strokesMap = out_letter_stroke_map
        to_anno.alternates = tuple(all_alternates)
        return True

#-------------------------------------

class TextVisualizer( ObserverBase.Visualizer ):

    def __init__(self, board):
        ObserverBase.Visualizer.__init__( self, board,  TextAnnotation )

    def drawAnno( self, a ):
        if len(a.text) > 0:
            ul,br = GeomUtils.strokelistBoundingBox( a.Strokes )
            logger.debug(a.Strokes)
            height = ul.Y - br.Y
            midpointY = (ul.Y + br.Y) / 2
            midpointX = (ul.X + br.X) / 2
            left_x = midpointX - a.scale / 2.0
            right_x = midpointX + a.scale / 2.0
            self.getBoard().getGUI().drawLine( left_x, midpointY, right_x, midpointY, color="#a0a0a0")
            x = br.X
            y = br.Y
            self.getBoard().getGUI().drawText( br.X, y, a.text, size=15, color="#a0a0a0" )
            """
            for letterList in a.alternates:
                y = br.Y
                for level, text in enumerate(letterList):
                    self.getBoard().getGUI().drawText( x, y, text, size=10, color="#a0a0a0" )
                    y -= 15
                x += 10
            """

#-------------------------------------
# if executed by itself, run all the doc tests

if __name__ == "__main__":
    Logger.setDoctest(logger) 
    import doctest
    doctest.testmod()
