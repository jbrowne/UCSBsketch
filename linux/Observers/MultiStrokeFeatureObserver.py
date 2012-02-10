"""
filename: MultiStrokeFeatureObserver.py

description:


Doctest Examples:

"""

#-------------------------------------
import os
import math
import pdb
from Utils import GeomUtils
from Utils import Logger

from SketchFramework import Point
from SketchFramework import Stroke

from SketchFramework.Annotation import Annotation
from SketchFramework.Board import BoardObserver


logger = Logger.getLogger('MultiStrokeObserver', Logger.DEBUG )

#-------------------------------------

class MultiStrokeAnnotation(Annotation):
    def __init__(self, tag):
        Annotation.__init__(self)
        self.name = tag
        
#-------------------------------------

class MultiStrokeMarker( BoardObserver ):
    "Compares all strokes with templates and annotates strokes with any template within some threshold."
    def __init__(self):
        
        self.getBoard().AddBoardObserver( self , [MultiStrokeAnnotation])
        self.getBoard().RegisterForStroke( self )
        self._features = {} # To be: { stroke : (feature_vector) }
        self._matchVector = None
        self.overlaps = {} 
        
    def onStrokeAdded( self, stroke ):
        "Compare this stroke to all templates, and annotate those matching within some threshold."
        logger.debug("Scoring stroke")
        #strokeVector = ( len(stroke.Points), GeomUtils.pointListOrientationHistogram(GeomUtils.strokeNormalizeSpacing(stroke, numpoints = len(stroke.Points) / 3.0).Points) )
        strokeVector = generateFeatureVector(stroke)
        logger.debug("Stroke Vector: %s" % (str(strokeVector)))
        if self._matchVector == None:
            self._matchVector = strokeVector
        else:
            bb1 = GeomUtils.strokelistBoundingBox([stroke])
            for prevStk in self._features.keys():
                bb2 = GeomUtils.strokelistBoundingBox([prevStk])
                if GeomUtils.boundingboxOverlap(bb1, bb2):
                    self.overlaps.setdefault(stroke, set()).add(prevStk)
                    self.overlaps.setdefault(prevStk, set()).add(stroke)
            self._features[stroke] = strokeVector
            score = scoreVector(self._matchVector, strokeVector)
            logger.debug("  Distance %s from baseline" % (score) )
            if score < 0.02:
                self.getBoard().AnnotateStrokes([stroke], MultiStrokeAnnotation("Match"))

            for stk in self.overlaps.get(stroke, []):
                multiVect = addVectors( [self._features[stroke], self._features[stk] ] )
                logger.debug("Multiple vector: %s" % (str(multiVect)))
                score = scoreVector(self._matchVector, multiVect)
                logger.debug("  Distance %s from baseline" % (score) )
                if score < 0.02:
                    self.getBoard().AnnotateStrokes([stroke, stk], MultiStrokeAnnotation("Match"))


    def onStrokeRemoved(self, stroke):
        "When a stroke is removed, remove circle annotation if found"
        for anno in stroke.findAnnotations(MultiStrokeAnnotation, True):
            self.getBoard().RemoveAnnotation(anno)

def generateFeatureVector(stroke):
    finalVector = {}
    finalVector['len'] = GeomUtils.strokeLength(stroke)
    sNorm = GeomUtils.strokeNormalizeSpacing( stroke, max(finalVector['len'] / 4.0, 1) )
    finalVector['orientations'] = GeomUtils.pointListOrientationHistogram(sNorm.Points)
    return finalVector
        
    
def addVectors(vectList):
    logger.debug("Adding Vectors")
    for v in vectList:
        logger.debug("   %s" % (str(v)))
    retVect = {}
    total = sum([v['len'] for v in vectList])
    retVect['len'] = total
    orientations = len(vectList[0]['orientations']) * [0]
    if total > 0:
        for i in range(len(vectList)):
            w = vectList[i]['len'] / float(total)
            for j in range(len(orientations)):
                orientations[j] += w * vectList[i]['orientations'][j]
    retVect['orientations'] = tuple(orientations)
    logger.debug("-->%s" % (str(retVect)))
    return retVect
                

def scoreVector(baseline, tester):
    #orientations
    orientationDist = 1.0
    if len(baseline['orientations']) == len(tester['orientations']):
        dist = 0.0
        for i in range(len(baseline['orientations'])):
            dist += (baseline['orientations'][i] - tester['orientations'][i]) ** 2
        math.sqrt(dist)
        orientationDist = dist / math.sqrt(2)
    return orientationDist
    
