"""

description:
   Using the Rubine classifier to detect strokes

Doctest Examples:

>>> t = TextMarker()

"""

#-------------------------------------

import pdb
import sys
import math
import traceback
import random
import time
from Utils import Logger
from Utils import GeomUtils
from Utils.Timer import Timed

from SketchFramework.Point import Point
from SketchFramework.Stroke import Stroke

from xml.etree import ElementTree as ET

from numpy  import *

rb_logger = Logger.getLogger('Rubine', Logger.WARN )

#------------------------------------------------------------
class FeatureSet(object):
    """An abstract class for running sets of feature methods on strokes"""
    def __init__(self):
        rb_logger.debug("Using Feature set %s" % (self.__class__.__name__))
        pass
    def generateVector(strokeList):
        """This method takes in a list of strokes and returns a tuple of floats for the scores of each feature"""
        return (0.0)
    def __len__(self):
        """Return how many feature values are in a vector"""
        return 0

#------------------------------------------------------------
bcp_logger = Logger.getLogger('BCPFeatureSet', Logger.WARN )
class BCPFeatureSet(FeatureSet):
    """Feature set found to be best for Rubine's classifier in
    Blagojevic, et al. "The Power of Automatic Feature Selection: 
    Rubine on Steroids" 2010"""
    def __init__(self):
        FeatureSet.__init__(self)
        self.rubineSet = RubineFeatureSet()

    def __len__(self):
        return 28


    def generateVector(self, strokeList):
        """Assemble the vector of feature scores from a list of strokes, presumed to
        make up a single symbol."""
        retVector = []

        #Set up the common data
        if len(strokeList) > 1:
            bcp_logger.warn("Concatenating multiple strokes")
            stroke = Stroke( [ p for stk in strokeList for p in stk.Points ])
        elif len(strokeList) == 1:
            stroke = strokeList[0]

        convexHull = Stroke(GeomUtils.convexHull(stroke.Points))
        strokeLength = GeomUtils.strokeLength(stroke)
        strokeNorm = GeomUtils.strokeNormalizeSpacing(stroke, numpoints = max(1,strokeLength))
        boundingBox = (stroke.BoundTopLeft, stroke.BoundBottomRight)
        curvatureList = GeomUtils.strokeGetPointsCurvature(
                            GeomUtils.strokeSmooth(stroke, width = max(1, int(strokeLength*0.05))
                        ))

        anglesVector = GeomUtils.pointlistAnglesVector(stroke.Points)
        #Generate the vector
        #Basic Features
        retVector = [ self.f1_12(stroke, strokeLength) , \
                     self.f1_16(strokeNorm) , \
                     self.f2_6(strokeLength, convexHull) , \
                     self.f2_8(strokeLength, boundingBox) , \
                     self.f5_1(stroke), \
                     self.f7_2(boundingBox) , \
                     self.f7_7(convexHull, boundingBox) , \
                     self.f7_10(strokeLength) , \
                     self.f7_16(convexHull) , \
                     self.f7_17(convexHull) \
                    ]
        #The Rest
        retVector.extend([
                     self.f1_01(strokeNorm, strokeLength), \
                     self.f1_07(boundingBox), \
                     self.f1_09(stroke), \

                     self.f1_17(stroke, boundingBox), \
                     self.f1_23(stroke), \
                     self.f7_05(boundingBox), \
                     self.f7_11(boundingBox), \

                     self.f1_04(stroke), \
                     self.f1_11(anglesVector), \
                     self.f1_13(stroke), \
                     self.f7_13(strokeLength), \
                     self.f7_14(boundingBox), \

                     self.f1_06(strokeNorm), \
                     self.f1_18(stroke), \
                     self.f1_19(stroke), \
                     self.f1_21(stroke), \
                     self.f10_05(stroke), \

                     self.f1_03(stroke), \
                     #self.f4_01(stroke), \
                    ])
        #random.seed(0xDEADBEEF)
        #random.shuffle(retVector)
        assert len(retVector) == len(self) 
        return retVector

    #-----------------------------------------------
    #   Features common to all symbol classes
    #-----------------------------------------------
    #@Timed
    def f1_12(self, stroke, strokeLen): #NOT COMMUTATIVE
        """Distance from the first point of the stroke to the 
        last point of the stroke [Rub91]"""
        if strokeLen > 0:
            return GeomUtils.pointDist(stroke.Points[0], stroke.Points[-1]) / strokeLen
        else:
            return 0.0

    #@Timed
    def f1_16(self, sNorm):
        """Number of fragments in a stroke, according to its corners [BSH04]"""
        #pre = time.time()
        #sNorm = GeomUtils.strokeNormalizeSpacing(stroke, numpoints = max(1,strokeLen/30))
        sNorm = Stroke([sNorm.Points[i] for i in range(0,len(sNorm.Points),30)])
        angles = GeomUtils.pointlistAnglesVector(sNorm.Points)
        positive = angles[0] >= 0.0
        segments = 2
        for i in range(len(angles)):
            if positive == None:
                if angle[i] > 0:
                    positive = True
                elif angle[i] < 0:
                    positive = False 
                continue
            if positive and angles[i] < -0.18:
                segments += 1
                positive = False
            elif not positive and angles[i] > 0.18:
                segments += 1
                positive = True
        #bcp_logger.debug("%s time %s" % (sys._getframe(-1).f_code.co_name, 1000 * (time.time() - pre) ))
        
        return segments

    #@Timed
    def f2_6(self, strokeLen, cvxHull):
        """Stroke length / perimeter of the stroke's convex hull [FPJ02]"""
        cvx_perimeter = GeomUtils.strokeLength(cvxHull)
        if cvx_perimeter > 0.0:
            return strokeLen / cvx_perimeter
        else:
            return 1.0

    #@Timed
    def f2_8(self, strokeLen, bbox):
        """Length of the stroke divided by the length of the bounding box
        diagonal. Adapted from [Rub91]"""
        diagDist = GeomUtils.pointDist( bbox[0], bbox[1])
        if diagDist > 0:
            return strokeLen / float(diagDist)
        else:
            return 1.0

    #@Timed
    def f5_1(self, stroke):
        """Number of self intersections at the endpoints of the stroke, adapted
        from [Qin05]"""
        #pre = time.time()
        selfIntersections = 0
        length = GeomUtils.strokeLength(stroke)
        for i in range(len(stroke.Points)-1):
            seg1 = (stroke.Points[i], stroke.Points[i+1])
            for j in range(i+1, len(stroke.Points)/3) + \
                     range(len(stroke.Points)/3, len(stroke.Points)-1):
                seg2 = (stroke.Points[j], stroke.Points[j+1])
                cross = GeomUtils.getLinesIntersection( seg1, seg2 )
                if cross is not None \
                    and cross != seg1[0] \
                    and cross != seg2[0] :
                    selfIntersections += 1
	bcp_logger.debug("Self Intersections: %s" % (selfIntersections))
        #bcp_logger.debug("%s time %s" % (sys._getframe(-1).f_code.co_name, 1000 * (time.time() - pre) ))
        return selfIntersections
 

    #@Timed
    def f7_2(self, bbox):
        """Aspect: ( 45*pi/180 - angle of bounding box diagonal ) [LLR*00] """
        left = bbox[0].X
        top = bbox[0].Y
        right = bbox[1].X
        bottom = bbox[1].Y
        if right - left != 0:
            diagAngle = math.atan( (top - bottom) / float(right - left) )
        else:
            diagAngle = 1.570795 #pi / 2.0
        return 0.785398 - diagAngle #45 * pi / 180
    
    #@Timed
    def f7_7(self, cvxHull, bbox):
        """Ratio of area of convex hull to area of the enclosing rect of the 
        stroke [FPJ02]"""
        left = bbox[0].X
        top = bbox[0].Y
        right = bbox[1].X
        bottom = bbox[1].Y

        cvxArea = GeomUtils.area(cvxHull.Points)
        bboxArea = GeomUtils.area([Point(left, bottom),
                                   Point(left, top),
                                   Point(right, top),
                                   Point(right, bottom)])
        if bboxArea > 0:
            return cvxArea / bboxArea
        else:
            return 0.0
    
    #@Timed
    def f7_10(self, strokeLen):
        """Total length of the stroke [Rub91]"""
        return strokeLen


    #@Timed
    def f7_16(self, cvxHull):
        """Perimeter efficiency: 2 * sqrt( pi * convex hull area ) / convex hull perimeter
        [LC02]"""
        cvxArea = GeomUtils.area(cvxHull.Points)
        cvxPerim = GeomUtils.strokeLength(cvxHull)

        if cvxPerim > 0.0:
            return 2 * math.sqrt( math.pi * cvxArea) / cvxPerim 
        else:
            return 1.0

    #@Timed
    def f7_17(self, cvxHull):
        """Ratio of perimeter to area of the stroke's convex hull [FPJ02]"""
        #pre = time.time()
        cvxArea = GeomUtils.area(cvxHull.Points)
        cvxPerim = GeomUtils.strokeLength(cvxHull)
        #bcp_logger.debug("%s time %s" % (sys._getframe(-1).f_code.co_name, 1000 * (time.time() - pre) ))
        if cvxPerim > 0.0:
            return cvxArea / float(cvxPerim)
        else:
            return 1.0

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Features that work great for Basic Shapes
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #@Timed
    def f1_01(self, sNorm, strokeLen):
        """The number of bezier cusps. [PPG 07]"""
        #pre = time.time()
        numCusps = 0
        sNorm = Stroke([sNorm.Points[i] for i in range(0,len(sNorm.Points),3)])
        while len(sNorm.Points) < 3:
            sNorm.addPoint(sNorm.Points[-1])
        curves = GeomUtils.strokeApproximateCubicCurves(sNorm, strokeLen)
        #bcp_logger.debug("%s time %s" % (sys._getframe(-1).f_code.co_name, 1000 * (time.time() - pre) ))

        for curve in curves:
            cPts = curve.getControlPoints()
            seg1dist = GeomUtils.pointDist(cPts[0], cPts[1])
            seg2dist = GeomUtils.pointDist(cPts[2], cPts[3])
            cStk = curve.toStroke()
            if seg1dist + seg2dist > GeomUtils.strokeLength(cStk):
                numCusps += 1
        bcp_logger.debug("Number of Bezier cusps: %s" % (numCusps))
        #bcp_logger.debug("%s time %s" % (sys._getframe(-1).f_code.co_name, 1000 * (time.time() - pre) ))
        return numCusps


    #@Timed
    def f1_03(self, stroke):
        """The number of polyline cusps [PPG 07]"""
        pre = time.time()
        polyLine = GeomUtils.strokeApproximatePolyLine(stroke)
        angleList = GeomUtils.pointlistAnglesVector(polyLine.Points)
        i = 1
        cuspIdx = []
        numCusps = 0
        while i < len(angleList) - 1:
            totalAngle = sum(angleList[i-1:i+2]) * 57 
            if totalAngle > 90 or totalAngle < -90:
                numCusps += 1
                #cuspIdx.append(i)
                i = i + 2
            i+=1
        #bcp_logger.debug("%s time %s" % (sys._getframe(-1).f_code.co_name, 1000 * (time.time() - pre) ))
        bcp_logger.debug("PolyLine Cusps: %s" % (numCusps))
        return numCusps

    #@Timed
    def f1_07(self, bbox):
        """Angle of bbox diagonal. [Rubine]"""
        return self.rubineSet.f04(bbox)

    #@Timed
    def f1_09(self, stroke):
        """Cosine of the angle from first point to last point [Rubine91]"""
        return self.rubineSet.f01(stroke)

    #@Timed
    def f1_17(self, stroke, bbox):
        """Openness: Distance from 1st to last point of stroke / size 
        of strokes bbox. [LLR00]"""
        bboxSize = GeomUtils.pointDist(bbox[0], bbox[1])
        ptDist = GeomUtils.pointDist(stroke.Points[0], stroke.Points[-1])
        if ptDist > 0:
            openness = bboxSize / float(ptDist)
        else:
            openness = 0
        bcp_logger.debug("Openness: %s" % (openness))
        return openness

    #@Timed
    def f1_23(self, stroke):
        """Total angle / sum of |Angle at each point| [LLR00]"""
        #pre = time.time()
        retVal = self.rubineSet.f09(stroke) / float(self.rubineSet.f10(stroke))
        #bcp_logger.debug("%s time %s" % (sys._getframe(-1).f_code.co_name, 1000 * (time.time() - pre) ))
        return retVal

    #@Timed
    def f4_01(self, stroke):
        """Divider result. Results of text/shape divider on current stroke"""
        bcp_logger.warn("Using Unimplemented feature f4_01")
        #~~~~~~~~~~~~~~~~~~~
        #NOT IMPLEMENTED
        #~~~~~~~~~~~~~~~~~~~
        return GeomUtils.strokeLength(stroke)

    #@Timed
    def f7_05(self, bbox):
        """Height of bounding box [FPJ02]"""
        bboxHeight = bbox[0].Y - bbox[1].Y
        bcp_logger.debug("BoundingBox Height %s" % (bboxHeight))
        return bboxHeight

    #@Timed
    def f7_11(self, bbox):
        """Log area. Log of the stroke's bounding box area[LLR00]"""
        h = bbox[0].Y - bbox[1].Y
        w = bbox[1].X - bbox[0].X
        if h*w > 0:
            logBboxArea = math.log( h*w)
        else:
            logBboxArea = -1000000
        bcp_logger.debug("Log Bbox Area: %s" % (logBboxArea))
        return logBboxArea

    #@Timed
    def f7_13(self, strokeLen): 
        """Log of the total length of the stroke. [LLR*00, MFN93]"""
        if strokeLen > 0.0:
            return math.log(strokeLen)
        else:
            return 0.0
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Features that work great for Class Diagrams
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    
    #def f1_03(self) Also in Basic Shapes

    #@Timed
    def f1_04(self, stroke):
        """Sum of the absolute value of the angle at each point [Rubine91]"""
        #pre = time.time()
        retVal = self.rubineSet.f10(stroke) / len(stroke.Points)
        bcp_logger.debug("F1_04: Sum of abs angle value: %s" % (retVal) )
        #bcp_logger.debug("%s time %s" % (sys._getframe(-1).f_code.co_name, 1000 * (time.time() - pre) ))
        return retVal


    #def f1_07(self) Also in Basic Shapes

    #@Timed
    def f1_11(self, anglesVector):
        """Curviness. Sum of absolute value of the angle at each stroke point below 19deg 
            threshold [LLR01]"""
        curviness = 0.0
        for angle in anglesVector:
            aval = 57.0 *math.fabs(angle)
            if aval < 19:
                curviness+= aval
        return curviness
            

    #@Timed
    def f1_13(self, stroke):
        """(Orthogonal distance squared between the least squares fitted line
        and the stroke points) / stroke length [PRD08, SSD01]"""
        #pre = time.time()
        linRegLine = GeomUtils.pointListLinearRegression(stroke.Points)

        sumDists = 0
        for pt in stroke.Points:
            sumDists += GeomUtils.pointDistanceFromLine(pt, linRegLine)

        sumDists /= float(len(stroke.Points))
        #bcp_logger.debug("%s time %s" % (sys._getframe(-1).f_code.co_name, 1000 * (time.time() - pre) ))
        bcp_logger.debug("Orthogonal distance to linear regression / stroke length: %s" % (sumDists))
        return sumDists

    #def f7_11(self) Also in Basic Shapes

    #def f7_13(self, strokeLen): #Also in Basic Shapes

    #@Timed
    def f7_14(self, bbox):
        """Log of the length of the longest side of the stroke's bounding box [MFN93]"""
        h = bbox[0].Y - bbox[1].Y
        w = bbox[0].X - bbox[1].X
        longest = max(h, w)
        if longest > 0:
            return math.log(longest)
        else:
            return -10000000

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Features that work great for Graphs
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    #def f1_04(self, strokeLen): Also in Class

    #@Timed
    def f1_06(self, sNorm):
        """The total absolute curvature of the largest fragment [BSH04]"""
        #pre = time.time()
        sNorm = Stroke([sNorm.Points[i] for i in range(0,len(sNorm.Points),30)])
        #sNorm = GeomUtils.strokeNormalizeSpacing(stroke, numpoints = max(1,strokeLen/30))
        angles = GeomUtils.pointlistAnglesVector(sNorm.Points)
        positive = angles[0] >= 0.0
        segments = 2
        curSegCurv = 0.0
        curSegLen = 0
        maxSegLen = 0
        maxSegCurv = 0.0
        for i in range(len(angles)):
            #print angles[i] * 57, 
            curSegCurv += angles[i]
            curSegLen += 1
            if curSegLen > maxSegLen:
                maxSegCurv = curSegCurv
                maxSegLen = curSegLen
            if positive == None:
                if angles[i] > 0:
                    positive = True
                elif angles[i] < 0:
                    positive = False 
                continue
            if positive and angles[i] < -0.18:
                curSegCurv = 0.0
                curSegLen = 0
                positive = False
                #print "\tSEG",
            elif not positive and angles[i] > 0.18:
                curSegCurv = 0.0
                curSegLen = 0
                positive = True
                #print "\tSEG",
            #print ""
        #print maxSegLen, maxSegCurv * 57
        #bcp_logger.debug("%s time %s" % (sys._getframe(-1).f_code.co_name, 1000 * (time.time() - pre) ))
        return maxSegCurv * math.pi / 180.0

    #def f1_09(self, strokeLen): # Also in Basic Shapes

    #def f1_11(self, strokeLen): # Also in Class

    #def f1_13(self): #Also in class

    #@Timed
    def f1_18(self, stroke):
        """Overtracing: Total angle / 2pi [PH08]"""
        bcp_logger.debug("Overtracing")
        #pre = time.time()
        retVal = self.rubineSet.f09(stroke) / (math.pi * 2)
        #bcp_logger.debug("%s time %s" % (sys._getframe(-1).f_code.co_name, 1000 * (time.time() - pre) ))
        return retVal

    #@Timed
    def f1_19(self, stroke):
        """Sin of the angle between the first and last ponts [Rubine91]"""
        retVal =  self.rubineSet.f02(stroke)    
        return retVal
    #@Timed
    def f1_21(self, stroke):
        """Total angle traversed by the stroke[Rubine91]"""
        #pre = time.time()
        retVal =  self.rubineSet.f09(stroke)
        #bcp_logger.debug("%s time %s" % (sys._getframe(-1).f_code.co_name, 1000 * (time.time() - pre) ))
        return retVal
    #@Timed
    def f10_05(self, stroke):
        """Minimum speed when drawing the stroke. Assume one point captured every time unit"""
        if len(stroke.Points) > 0:
            minSpeed = GeomUtils.strokeLength(stroke) #Assume it was all drawn at once
            for i in xrange(1, len(stroke.Points)):
                dist = GeomUtils.pointDist(stroke.Points[i - 1], stroke.Points[i])
                minSpeed = min(dist, minSpeed)
        else:
            minSpeed = 0 # Very slow writing zero points
        bcp_logger.debug("Minimum speed %s" %( minSpeed))
        return minSpeed

#------------------------------------------------------------
class BCPFeatureSet_Combinable(BCPFeatureSet):
    def __init__(self):
        BCPFeatureSet.__init__(self)
    def __len__(self):
        return 13
    def generateVector(self, strokeList):
        """Assemble the vector of feature scores from a list of strokes, presumed to
        make up a single symbol."""
        retVector = []

        #---------------------------------
        #Set up the common data
        #---------------------------------
        stroke = strokeList[0]
        convexHull = Stroke(GeomUtils.convexHull(stroke.Points))
        strokeLength = GeomUtils.strokeLength(stroke)
        strokeNorm = GeomUtils.strokeNormalizeSpacing(stroke, numpoints = max(1,strokeLength))
        boundingBox = (stroke.BoundTopLeft, stroke.BoundBottomRight)
        anglesVector = GeomUtils.pointlistAnglesVector(stroke.Points)
        curvatureList = GeomUtils.strokeGetPointsCurvature(
                            GeomUtils.strokeSmooth(stroke, width = max(1, int(strokeLength*0.05))
                        ))

        if len(strokeList) > 1:
            bcp_logger.warn("Concatenating multiple strokes")
            concatStroke = Stroke( [ p for stk in strokeList for p in stk.Points ])
            concatConvexHull = Stroke(GeomUtils.convexHull(stroke.Points))
            concatStrokeLength = GeomUtils.strokeLength(stroke)
            concatBoundingBox = (stroke.BoundTopLeft, stroke.BoundBottomRight)
        elif len(strokeList) == 1:
            concatStroke = stroke
            concatConvexHull = convexHull
            concatStrokeLength = strokeLength
            concatBoundingBox = boundingBox

        #---------------------------------
        #Features that work the same over a concatenated stroke
        #---------------------------------
        concatFeats = [
                     self.f2_6(concatStrokeLength, concatConvexHull) , \
                     self.f2_8(concatStrokeLength, concatBoundingBox) , \
                     self.f7_2(concatBoundingBox) , \
                     self.f7_7(concatConvexHull, concatBoundingBox) , \
                     self.f7_10(concatStrokeLength) , \
                     self.f7_16(concatConvexHull) , \
                     self.f7_17(concatConvexHull), \
                     self.f1_07(concatBoundingBox), \
                     self.f7_05(concatBoundingBox), \
                     self.f7_11(concatBoundingBox), \
                     self.f7_13(concatStrokeLength), \
                     self.f1_13(stroke), \
                     self.f7_14(concatBoundingBox)
                     ]
        """
        retVector = [ 
                     #self.f1_12(stroke, strokeLength) , \
                     self.f1_16(strokeNorm) , \
                     self.f5_1(stroke), \
                    ]
        #The Rest
        retVector.extend([
                     self.f1_01(strokeNorm, strokeLength), \
                     #self.f1_09(stroke), \

                     #self.f1_17(stroke, boundingBox), \
                     self.f1_23(stroke), \

                     self.f1_04(stroke), \
                     self.f1_11(anglesVector), \

                     self.f1_06(strokeNorm), \
                     self.f1_18(stroke), \
                     #self.f1_19(stroke), \
                     self.f1_21(stroke), \
                     #self.f10_05(stroke), \

                     self.f1_03(stroke), \
                     #self.f4_01(stroke), \
                    ])
        #random.seed(0xDEADBEEF)
        #random.shuffle(retVector)
        """
        retVector = concatFeats
        assert len(retVector) == len(self) , "%s != %s" % (len(retVector), len(self))
        return retVector

#------------------------------------------------------------
class BCP_ShapeFeatureSet(BCPFeatureSet):
    """This class implements all of the features found to be in the top 20
    for the Baisc Shapes dataset"""
    def __init__(self):
        BCPFeatureSet.__init__(self)

    def __len__(self):
        return 19
    
    def generateVector(self, strokeList):
        """Assemble the vector of feature scores from a list of strokes, presumed to
        make up a single symbol."""
        retVector = []

        #Set up the common data
        if len(strokeList) > 1:
            bcp_logger.warn("Concatenating multiple strokes")
            stroke = Stroke( [ p for stk in strokeList for p in stk.Points ])
        elif len(strokeList) == 1:
            stroke = strokeList[0]

        convexHull = Stroke(GeomUtils.convexHull(stroke.Points))
        strokeLength = GeomUtils.strokeLength(stroke)
        strokeNorm = GeomUtils.strokeNormalizeSpacing(stroke, numpoints = max(1,strokeLength))
        boundingBox = (stroke.BoundTopLeft, stroke.BoundBottomRight)
        curvatureList = GeomUtils.strokeGetPointsCurvature(
                            GeomUtils.strokeSmooth(stroke, width = max(1, int(strokeLength*0.05))
                        ))

        anglesVector = GeomUtils.pointlistAnglesVector(stroke.Points)
        #Generate the vector
        #Basic Features
        retVector = [ self.f1_12(stroke, strokeLength) , \
                     self.f1_16(strokeNorm) , \
                     self.f2_6(strokeLength, convexHull) , \
                     self.f2_8(strokeLength, boundingBox) , \
                     self.f5_1(stroke), \
                     self.f7_2(boundingBox) , \
                     self.f7_7(convexHull, boundingBox) , \
                     self.f7_10(strokeLength) , \
                     self.f7_16(convexHull) , \
                     self.f7_17(convexHull) \
                    ]
        #Specific to Shape
        retVector.extend([
                     self.f1_01(strokeNorm, strokeLength), \
                     self.f1_07(boundingBox), \
                     self.f1_09(stroke), \

                     self.f1_17(stroke, boundingBox), \
                     self.f1_23(stroke), \
                     self.f7_05(boundingBox), \
                     self.f7_11(boundingBox), \
                     self.f7_13(strokeLength), \

                     self.f1_03(stroke), \
                     #self.f4_01(stroke), \
                    ])
        #random.seed(0xDEADBEEF)
        #random.shuffle(retVector)
        assert len(retVector) == len(self) 
        return retVector
#------------------------------------------------------------
class BCP_ShapeFeatureSet_Combinable(BCPFeatureSet):
    """This class implements all of the features found to be in the top 20
    for the Baisc Shapes dataset"""
    def __init__(self):
        BCPFeatureSet.__init__(self)

    def __len__(self):
        return 16
    
    def generateVector(self, strokeList):
        """Assemble the vector of feature scores from a list of strokes, presumed to
        make up a single symbol."""
        retVector = []

        #Set up the common data
        if len(strokeList) > 1:
            bcp_logger.warn("Concatenating multiple strokes")
            stroke = Stroke( [ p for stk in strokeList for p in stk.Points ])
        elif len(strokeList) == 1:
            stroke = strokeList[0]

        convexHull = Stroke(GeomUtils.convexHull(stroke.Points))
        strokeLength = GeomUtils.strokeLength(stroke)
        strokeNorm = GeomUtils.strokeNormalizeSpacing(stroke, numpoints = max(1,strokeLength))
        boundingBox = (stroke.BoundTopLeft, stroke.BoundBottomRight)
        curvatureList = GeomUtils.strokeGetPointsCurvature(
                            GeomUtils.strokeSmooth(stroke, width = max(1, int(strokeLength*0.05))
                        ))

        anglesVector = GeomUtils.pointlistAnglesVector(stroke.Points)
        #Generate the vector
        #Basic Features
        retVector = [ 
                     #self.f1_12(stroke, strokeLength) , \
                     self.f1_16(strokeNorm) , \
                     self.f2_6(strokeLength, convexHull) , \
                     self.f2_8(strokeLength, boundingBox) , \
                     self.f5_1(stroke), \
                     self.f7_2(boundingBox) , \
                     self.f7_7(convexHull, boundingBox) , \
                     self.f7_10(strokeLength) , \
                     self.f7_16(convexHull) , \
                     self.f7_17(convexHull) \
                    ]
        #Specific to Shape
        retVector.extend([
                     self.f1_01(strokeNorm, strokeLength), \
                     self.f1_07(boundingBox), \
                     #self.f1_09(stroke), \

                     #self.f1_17(stroke, boundingBox), \
                     self.f1_23(stroke), \
                     self.f7_05(boundingBox), \
                     self.f7_11(boundingBox), \
                     self.f7_13(strokeLength), \

                     self.f1_03(stroke), \
                     #self.f4_01(stroke), \
                    ])
        #random.seed(0xFEEDBEEF)
        #random.shuffle(retVector)
        assert len(retVector) == len(self) 
        return retVector
        
#------------------------------------------------------------
class BCP_ClassFeatureSet(BCPFeatureSet):
    """This class implements all of the features found to be in the top 20
    for the Class diagram dataset"""
    def __init__(self):
        BCPFeatureSet.__init__(self)

    def __len__(self):
        return 20
    
    def generateVector(self, strokeList):
        """Assemble the vector of feature scores from a list of strokes, presumed to
        make up a single symbol."""
        retVector = []

        #Set up the common data
        if len(strokeList) > 1:
            bcp_logger.warn("Concatenating multiple strokes")
            stroke = Stroke( [ p for stk in strokeList for p in stk.Points ])
        elif len(strokeList) == 1:
            stroke = strokeList[0]

        convexHull = Stroke(GeomUtils.convexHull(stroke.Points))
        strokeLength = GeomUtils.strokeLength(stroke)
        strokeNorm = GeomUtils.strokeNormalizeSpacing(stroke, numpoints = max(1,strokeLength))
        boundingBox = (stroke.BoundTopLeft, stroke.BoundBottomRight)
        curvatureList = GeomUtils.strokeGetPointsCurvature(
                            GeomUtils.strokeSmooth(stroke, width = max(1, int(strokeLength*0.05))
                        ))

        anglesVector = GeomUtils.pointlistAnglesVector(stroke.Points)
        #Generate the vector
        #Basic Features
        retVector = [ self.f1_12(stroke, strokeLength) , \
                     self.f1_16(strokeNorm) , \
                     self.f2_6(strokeLength, convexHull) , \
                     self.f2_8(strokeLength, boundingBox) , \
                     self.f5_1(stroke), \
                     self.f7_2(boundingBox) , \
                     self.f7_7(convexHull, boundingBox) , \
                     self.f7_10(strokeLength) , \
                     self.f7_16(convexHull) , \
                     self.f7_17(convexHull) \
                    ]
        #Specific to Class diagrams
        retVector.extend([

                     #Class
                     self.f1_04(stroke), \
                     self.f1_07(boundingBox), \
                     self.f1_11(anglesVector), \
                     self.f1_13(stroke), \
                     self.f1_17(stroke, boundingBox), \
                     self.f7_11(boundingBox), \
                     self.f7_13(strokeLength), \
                     self.f7_14(boundingBox), \
                     self.f10_05(stroke), \
                     self.f1_03(stroke), \
                    ])
        assert len(retVector) == len(self) 
        return retVector
#------------------------------------------------------------
class BCP_ClassFeatureSet_Combinable(BCPFeatureSet):
    """This class implements all of the features found to be in the top 20
    for the Class diagram dataset"""
    def __init__(self):
        BCPFeatureSet.__init__(self)

    def __len__(self):
        return 17
    
    def generateVector(self, strokeList):
        """Assemble the vector of feature scores from a list of strokes, presumed to
        make up a single symbol."""
        retVector = []

        #Set up the common data
        if len(strokeList) > 1:
            bcp_logger.warn("Concatenating multiple strokes")
            stroke = Stroke( [ p for stk in strokeList for p in stk.Points ])
        elif len(strokeList) == 1:
            stroke = strokeList[0]

        convexHull = Stroke(GeomUtils.convexHull(stroke.Points))
        strokeLength = GeomUtils.strokeLength(stroke)
        strokeNorm = GeomUtils.strokeNormalizeSpacing(stroke, numpoints = max(1,strokeLength))
        boundingBox = (stroke.BoundTopLeft, stroke.BoundBottomRight)
        curvatureList = GeomUtils.strokeGetPointsCurvature(
                            GeomUtils.strokeSmooth(stroke, width = max(1, int(strokeLength*0.05))
                        ))

        anglesVector = GeomUtils.pointlistAnglesVector(stroke.Points)
        #Generate the vector
        #Basic Features
        retVector = [ 
                     #self.f1_12(stroke, strokeLength) , \
                     self.f1_16(strokeNorm) , \
                     self.f2_6(strokeLength, convexHull) , \
                     self.f2_8(strokeLength, boundingBox) , \
                     self.f5_1(stroke), \

                     self.f7_2(boundingBox) , \
                     self.f7_7(convexHull, boundingBox) , \
                     self.f7_10(strokeLength) , \
                     self.f7_16(convexHull) , \
                     self.f7_17(convexHull) \
                    ]
        #Specific to Class diagrams
        retVector.extend([

                     #Class
                     self.f1_04(stroke), \
                     self.f1_07(boundingBox), \
                     self.f1_11(anglesVector), \
                     self.f1_13(stroke), \
                     #self.f1_17(stroke, boundingBox), \
                     self.f7_11(boundingBox), \
                     self.f7_13(strokeLength), \
                     self.f7_14(boundingBox), \
                     #self.f10_05(stroke), \
                     self.f1_03(stroke), \
                    ])
        #random.seed(0xDEADBEEF)
        #random.shuffle(retVector)
        assert len(retVector) == len(self) 
        return retVector


#------------------------------------------------------------
class BCP_GraphFeatureSet(BCPFeatureSet):
    """This class implements all of the features found to be in the top 20
    for the Graphs dataset"""
    def __init__(self):
        BCPFeatureSet.__init__(self)

    def __len__(self):
        return 19
    
    def generateVector(self, strokeList):
        """Assemble the vector of feature scores from a list of strokes, presumed to
        make up a single symbol."""
        retVector = []

        #Set up the common data
        if len(strokeList) > 1:
            bcp_logger.warn("Concatenating multiple strokes")
            stroke = Stroke( [ p for stk in strokeList for p in stk.Points ])
        elif len(strokeList) == 1:
            stroke = strokeList[0]

        convexHull = Stroke(GeomUtils.convexHull(stroke.Points))
        strokeLength = GeomUtils.strokeLength(stroke)
        strokeNorm = GeomUtils.strokeNormalizeSpacing(stroke, numpoints = max(1,strokeLength))
        boundingBox = (stroke.BoundTopLeft, stroke.BoundBottomRight)
        curvatureList = GeomUtils.strokeGetPointsCurvature(
                            GeomUtils.strokeSmooth(stroke, width = max(1, int(strokeLength*0.05))
                        ))

        anglesVector = GeomUtils.pointlistAnglesVector(stroke.Points)
        #Generate the vector
        #Basic Features
        retVector = [ self.f1_12(stroke, strokeLength) , \
                     self.f1_16(strokeNorm) , \
                     self.f2_6(strokeLength, convexHull) , \
                     self.f2_8(strokeLength, boundingBox) , \
                     self.f5_1(stroke), \
                     self.f7_2(boundingBox) , \
                     self.f7_7(convexHull, boundingBox) , \
                     self.f7_10(strokeLength) , \
                     self.f7_16(convexHull) , \
                     self.f7_17(convexHull) \
                    ]
        #The Rest
        retVector.extend([
                     self.f1_04(stroke), \
                     self.f1_06(strokeNorm), \
                     self.f1_09(stroke), \
                     self.f1_11(anglesVector), \
                     self.f1_13(stroke), \
                     self.f1_18(stroke), \
                     self.f1_19(stroke), \
                     self.f1_21(stroke), \
                     self.f1_23(stroke), \
                     #NotImplemented
                     #self.f4_01(stroke), \
                    ])
        #random.seed(0xDEADBEEF)
        #random.shuffle(retVector)
        assert len(retVector) == len(self) 
        return retVector
#------------------------------------------------------------
class BCP_GraphFeatureSet_Combinable(BCPFeatureSet):
    """This class implements all of the features found to be in the top 20
    for the Graphs dataset"""
    def __init__(self):
        BCPFeatureSet.__init__(self)

    def __len__(self):
        return 17
    
    def generateVector(self, strokeList):
        """Assemble the vector of feature scores from a list of strokes, presumed to
        make up a single symbol."""
        retVector = []

        #Set up the common data
        if len(strokeList) > 1:
            bcp_logger.warn("Concatenating multiple strokes")
            stroke = Stroke( [ p for stk in strokeList for p in stk.Points ])
        elif len(strokeList) == 1:
            stroke = strokeList[0]

        convexHull = Stroke(GeomUtils.convexHull(stroke.Points))
        strokeLength = GeomUtils.strokeLength(stroke)
        strokeNorm = GeomUtils.strokeNormalizeSpacing(stroke, numpoints = max(1,strokeLength))
        boundingBox = (stroke.BoundTopLeft, stroke.BoundBottomRight)
        curvatureList = GeomUtils.strokeGetPointsCurvature(
                            GeomUtils.strokeSmooth(stroke, width = max(1, int(strokeLength*0.05))
                        ))

        anglesVector = GeomUtils.pointlistAnglesVector(stroke.Points)
        #Generate the vector
        #Basic Features
        retVector = [
                     #self.f1_12(stroke, strokeLength) , \
                     self.f1_16(strokeNorm) , \
                     self.f2_6(strokeLength, convexHull) , \
                     self.f2_8(strokeLength, boundingBox) , \
                     self.f5_1(stroke), \
                     self.f7_2(boundingBox) , \
                     self.f7_7(convexHull, boundingBox) , \
                     self.f7_10(strokeLength) , \
                     self.f7_16(convexHull) , \
                     self.f7_17(convexHull) \
                    ]
        #The Rest
        retVector.extend([
                     self.f1_04(stroke), \
                     self.f1_06(strokeNorm), \
                     self.f1_09(stroke), \
                     self.f1_11(anglesVector), \
                     self.f1_13(stroke), \
                     self.f1_18(stroke), \
                     #self.f1_19(stroke), \
                     self.f1_21(stroke), \
                     self.f1_23(stroke), \
                     #NotImplemented
                     #self.f4_01(stroke), \
                    ])
        #random.seed(0xDEADBEEF)
        #random.shuffle(retVector)
        assert len(retVector) == len(self) 
        return retVector

#------------------------------------------------------------

#------------------------------------------------------------
class RubineFeatureSet(FeatureSet):
    def __init__(self):
        FeatureSet.__init__(self)
        self._strokeFeatures = [self.f01, self.f02, self.f05, self.f06, self.f07, self.f08, self.f09, self.f10, self.f11]
        self._bboxFeatures = [self.f03, self.f04]

    def __len__(self):
        return len(self._strokeFeatures) + len(self._bboxFeatures)

    def generateVector(self, strokeList):
        """Generate the Rubine feature vector for the list of strokes. Multiple strokes are simply concatenated."""
        retList = []
        if len(strokeList) > 1:
            stroke = Stroke( [ p for stk in strokeList for p in stk.Points ])
        elif len(strokeList) == 1:
            stroke = strokeList[0]
        else:
            return tuple([0.0] * (len(self._strokeFeatures) + len(self._bboxFeatures)) )
        # normalize the stroke
        ul,br = GeomUtils.strokelistBoundingBox( [stroke] )
        sNorm = GeomUtils.strokeNormalizeSpacing(GeomUtils.strokeSmooth(stroke))
        for point in sNorm.Points:
            point.X -= ul.X
            point.Y -= br.Y

        for feat in self._strokeFeatures:
            retList.append(feat(stroke))
        for feat in self._bboxFeatures:
            retList.append(feat( (ul, br) ))

        assert len(self) == len(retList)
        return tuple(retList)


    #-----------------------
    # Stroke-based features
    #-----------------------

    def f01(self, stroke):
        # The first feature is the cosine of the inital angle
        # The second feature is the sine of the inital angle
        pointList = stroke.Points
        if len(pointList) > 2 and GeomUtils.pointDist(pointList[0], pointList[2]) != 0:
            f1 = (pointList[2].X - pointList[0].X) / GeomUtils.pointDist(pointList[0], pointList[2])
        else:
            f1 = 0
        return f1

    def f02(self, stroke):
        # The first feature is the cosine of the inital angle
        # The second feature is the sine of the inital angle
        pointList = stroke.Points
        if len(pointList) > 2 and GeomUtils.pointDist(pointList[0], pointList[2]) != 0:
            f2 = (pointList[2].Y - pointList[0].Y) / GeomUtils.pointDist(pointList[0], pointList[2])
        else:
            f2 = 0
        return f2
    

    def f05(self, stroke):
        # 5th is the length between the first and last point
        pointList = stroke.Points
        f5 = GeomUtils.pointDist(pointList[0], pointList[-1])
        return f5

    def f06(self, stroke):
        # the 6th and 7th are the cosine and sine of the angle between the first and last point
        pointList = stroke.Points
        if GeomUtils.pointDist(pointList[0], pointList[-1]) != 0:
            f6 = (pointList[-1].X - pointList[0].X) / GeomUtils.pointDist(pointList[0], pointList[-1])
        else:
            f6 = 0 #You might make the claim that this should be 1, since as they get closer to each other, the delta_x better approximates the pointDist(p1,p2)
        return f6

    def f07(self, stroke):
        # the 6th and 7th are the cosine and sine of the angle between the first and last point
        pointList = stroke.Points
        if GeomUtils.pointDist(pointList[0], pointList[-1]) != 0:
            f7 = (pointList[-1].Y - pointList[0].Y) / GeomUtils.pointDist(pointList[0], pointList[-1])
        else:
            f7 = 0
        return f7

    def f08(self, stroke):
        # 8th and 9th are the sum of the lengths and angles
        return GeomUtils.strokeLength(stroke)

    def f09(self, stroke):
        #Sum of the angle traversed
        totalAngle = sum(GeomUtils.pointlistAnglesVector(stroke.Points)) 
        rb_logger.debug("Total Angle traversed: %s" %(57 *totalAngle))
        return totalAngle

    def f10(self, stroke):
        # 10th and 11th are the sum of the absolute value of the angels and to sum of the angles squared
        totalAbsAngles = sum([math.fabs(angle) for angle in GeomUtils.pointlistAnglesVector(stroke.Points)])
        rb_logger.debug("Total AbsAngle traversed: %s" %(57 *totalAbsAngles))
        return totalAbsAngles

    def f11(self, stroke):
        # 10th and 11th are the sum of the absolute value of the angels and to sum of the angles squared
        pointList = stroke.Points
        f11 = 0 # sum of the angle squared
        for i in range(len(pointList) -2):
            dxp = pointList[i+1].X - pointList[i].X   # delta x sub p
            dyp = pointList[i+1].Y - pointList[i].Y   # delta y sub p

            if i != 0:
                dxpOld = pointList[i].X - pointList[i-1].X   # delta x sub (p-1)
                dypOld = pointList[i].Y - pointList[i-1].Y   # delta y sub (p-1)
                if (dxp * dxpOld) + (dxp * dxpOld) != 0:
                    angle = math.atan(((dxp * dypOld) - (dxpOld * dyp)) / ((dxp * dxpOld) + (dxp * dxpOld)))
                    f11 += angle*angle
        return f11
    #-----------------------
    # Bounding box-based features
    #-----------------------
    def f03(self, bbox):
        # the third is the length of the diagonal of the bb
        f3 = GeomUtils.pointDist(bbox[0], bbox[1])
        return f3

    def f04(self, bbox):
        # 4th is the angle of the bounding box diagonal
        ul, br = bbox
        if (br.X - ul.X) != 0:
            f4 = math.atan((ul.Y - br.Y)/ (br.X - ul.X))
        else:
            f4 = math.pi/2.0  #Should this be pi/2? (lim of f4 as delta_x -> 0)
        return f4

#------------------------------------------------------------
#------------------------------------------------------------
logger = Logger.getLogger("RubineClassifier", Logger.WARN)
class SymbolClass (object):
    COUNT = 0
    def __init__(self, featureSet, name = None):
        """Initialize a new symbol class without any examples"""
        logger.debug("SymbolClass intantiated: %s" % (name))
        self.featureSet = featureSet
        #self.examples = []
        self.featureVectors = []
        if name == None:
            self.name = str(SymbolClass.COUNT)
        else:
            self.name = name
        SymbolClass.COUNT += 1
        self.weights = None
        self.weight0 = None

    def addStrokes(self, strokeList):
        """Add an example list of strokes to this class"""
        #self.examples.append(stroke)
        self.featureVectors.append(self.featureSet.generateVector(strokeList))

    def __len__(self):
        """The length of this SymbolClass (the number of examples given to it)"""
        return len(self.featureVectors)

    def getCovarianceMatrix(self, avgFeatureVals= None):
        """ Calculates the covariance matrix for a class. For Internal use only """
        numFeatures = len(self.featureSet)
        cmc = mat( zeros( (numFeatures, numFeatures))  ) 

        if avgFeatureVals is None:
            avgFeatureVals = self.getAverageFeatureValues()

        #cmc = mat(zeros((len(self.features[0][0]),len(self.features[0][0]))))
        #for i in range(len(self.features[c][0])): #Number of features
            #for j in range(len(self.features[c][0])):

        for f_i in range (numFeatures):
            for f_j in range (f_i, numFeatures):
                for sVect in self.featureVectors:
                    ijInc = (sVect[f_i] - avgFeatureVals[f_i]) * ( sVect[f_j] - avgFeatureVals[f_j])
                    cmc[f_i,f_j] += ijInc
                    cmc[f_j,f_i] += ijInc
        return cmc

    def getAverageFeatureValues(self):
        """ Given list of example stroke feature vectors, calculates the averages 
        feature values for a class. Returns list of averages indexed by feature 
        number. For Internal use only """
        averages = zeros(len(self.featureSet))
        for fvect in self.featureVectors: 
            for i in range(len(self.featureSet)):
                averages[i] += fvect[i]
        
        for i in range(len(self.featureSet)):
            averages[i] /= len(self.featureVectors)

        return averages

    def calculateWeights(self, invCovMatrix, avgFeatureVals):
        """Calculate this class's weights based on the common inverser covariance
        matrix."""
        numFeatures = len(self.featureSet)
        self.weight0 = 0.0
        self.weights = zeros( numFeatures )
        for w_idx in range(numFeatures):
            for f_i in range(numFeatures):
                self.weights[w_idx] += invCovMatrix[w_idx, f_i] * avgFeatureVals[f_i]
            self.weight0 +=  self.weights[w_idx] * avgFeatureVals[w_idx]
        self.weight0 *= -0.5

    def getWeights(self):
        """Return the weights for this class. If they're unset, it will be None"""
        if self.weight0 is not None and self.weights is not None:
            return [self.weight0] + list(self.weights)
        else:
            return None
#------------------------------------------------------------
class ShellSymbolClass(SymbolClass):
    """This is a semi-functional symbol class used for classification only"""
    def __init__(self, featureSet, name = None):
        self.weight0 = None
        self.weights = []
        self.averages = []
        
    def fromXML(self, elem):
        """Parses in this element from XML"""
        self.name = elem.get("name")
        self.weight0 = float(elem.find("weight0").text)
        weights = elem.findall("weight")
        for w_elem in weights:
            self.weights.append(float(w_elem.text))
        averages = elem.findall("average")
        for a_elem in averages:
            self.averages.append(float(a_elem.text))

        logger.debug("Name :%s\nWeights:%s\nAvgs%s" % (self.name, [self.weight0] + self.weights, self.averages))

    def getAverageFeatureValues(self):
        """ Given list of example stroke feature vectors, calculates the averages 
        feature values for a class. Returns list of averages indexed by feature 
        number. For Internal use only """
        return self.averages

#------------------------------------------------------------

class RubineClassifier():
    """Takes training data to create a file representing a rubine classifier.
        To use:
            Create a new class with "newClass(ClassName)"
            Then add strokes to the class with "addStroke(Stroke, ClassName)"
            repeat till all the classes are created and strokes are added
            Then call calculateWeights to generate the clasifier data
            Finally save the data to a file using "saveWeights(fileName)"
            This file can then be used to initate the rubine classifier
    """

    def __init__(self, debug = False, featureSet = BCPFeatureSet()):
        """Initiates the rubine trainer."""
        self.debug = debug
        self.reset()
        self.featureSet = featureSet

        self.count = -1
        self.symbolClasses = {}
        self.averages = {}
        self.covarianceMatrixInverse = None

    def reset(self):
        """ Resets the trainer """
        self.count = -1
        self.symbolClasses = {}
        self.averages = {}
        self.covarianceMatrixInverse = None

    def newClass(self, name = None):
        """ Creates a new class for the trainer. Name must be a string.
            If no name is provided, the class name defaults to the index number of the new class
        """
        logger.debug("Creating new class: %s" % (name))
        symCls = SymbolClass(self.featureSet, name = name)
        self.symbolClasses[symCls.name] = symCls

        #self.count += 1;
        #self.features.append([])
        #if name == None:
            #name = str(self.count)
        #self.names.append(name)
        return symCls.name

    def addStroke(self, stroke, clsName):
        """ Adds a stroke to the class given by the class name Class. If no class name is provided then
            the stroke is added to the most recently created class. If the class has not been created yet
            then it is created.
        """
        if len(stroke.Points) < 3:
            raise Exception("Not enough points in this stroke: %s" % (len(stroke.Points)))

        if clsName != None and clsName in self.symbolClasses:
            if clsName in self.symbolClasses:
                symCls = self.symbolClasses[clsName]
            else:
                symCls = self.symbolClasses[clsName] =  SymbolClass(self.featureSet, name = clsName) 
        else:
            raise Exception("Cannot add stroke to Symbol 'None'")
        #we need at least three points

        symCls.addStrokes([stroke])

        logger.debug("Stroke added to class: " + symCls.name)

    def calculateWeights(self):
        """ Creates teh training data based on the current classes. Call this before saving the weights """
        numFeatures = len(self.featureSet)
        dividor = - len(self.symbolClasses)
        self.averages = {}
        for name, symCls in self.symbolClasses.items():
            logger.debug("Class %s: %s examples" % (name, len(symCls)))
            dividor += len(symCls) #Number of examples
        if dividor == 0:
            raise Exception("Not enough examples across the classes")


        covMatrices = {}
        avgCovMat =  mat(zeros((numFeatures, numFeatures))) #Store the weighted average covariance matrix
        for symCls in self.symbolClasses.values():
            self.averages[symCls.name] = symCls.getAverageFeatureValues()
            covMat = symCls.getCovarianceMatrix(self.averages[symCls.name])
            for fi in range(numFeatures):
                for fj in range(numFeatures):
                    avgCovMat[fi, fj] += covMat[fi, fj] * len(symCls) / float(dividor)
            covMatrices[symCls.name] = covMat
        origMat = avgCovMat

        while linalg.det(avgCovMat) == 0.0: #While not invertible
            logger.warn("Singular Matrix!!!!!!!!!!!!!!!!!!!!")
            avgCovMat = origMat.copy()
            """
            fp = open("ERROR.txt", "a")
            print >> fp, avgCovMat
            for symCls in self.symbolClasses.values():
                print >>fp, symCls.name
                covMat = symCls.getCovarianceMatrix(self.averages[symCls.name])
                print >> fp, covMat
                for featVect in symCls.featureVectors:
                    print >> fp,  "\t".join([str(f) for f in featVect])
                print >>fp, "END", symCls.name
            fp.close()

            """
            """
            x = random.randint(0, len(self.featureSet) - 1)
            y = random.randint(0, len(self.featureSet) - 1)
            for i in range(len(self.featureSet)): #Swap the rows
                temp = avgCovMat[x,i]
                avgCovMat[x,i] = avgCovMat[y,i]
                avgCovMat[y,i] = temp
            for j in range(len(self.featureSet)): #Swap the columns
                temp = avgCovMat[j,x]
                avgCovMat[j,x] = avgCovMat[j,y]
                avgCovMat[j,y] = temp
            """
            for i in range(len(self.featureSet)):
                for j in range(len(self.featureSet)):
                    if avgCovMat[i,j] > 1:
                        factor = math.e ** (math.log(avgCovMat[i,j]) - 15)
                        avgCovMat[i,j] += factor * random.random()
        """
        except Exception as e:
            #Singular Matrix
            fp = open("ERROR.txt", "w")
            print traceback.format_exc()
            print e
            print >> fp, avgCovMat
            for symCls in self.symbolClasses.values():
                print symCls.name

                covMat = symCls.getCovarianceMatrix(self.averages[symCls.name])
                print >> fp, covMat
                for featVect in symCls.featureVectors:
                    print >> fp,  "\t".join([str(f) for f in featVect])
                print "END", symCls.name
            #exit(1)
            logger.warn("Noising matrix!")
            #Noise!
            i = random.randint(0, len(self.featureSet) - 1)
            j = random.randint(0, len(self.featureSet) - 1)
            avgCovMat[i,j] += random.random()
        """

        self.covarianceMatrixInverse = invCovMatrix = avgCovMat.I

        """
        fp = open("MATRIX_%s_%s.txt" % (type(self.featureSet).__name__, time.time()), "a")
        print >> fp, self.covarianceMatrixInverse
        for symCls in self.symbolClasses.values():
            print >>fp, symCls.name
            covMat = symCls.getCovarianceMatrix(self.averages[symCls.name])
            print >> fp, covMat
            for featVect in symCls.featureVectors:
                print >> fp,  "\t".join([str(f) for f in featVect])
            print >>fp, "END", symCls.name
        fp.close()
        """

        for symCls in self.symbolClasses.values():
            symCls.calculateWeights(invCovMatrix, self.averages[symCls.name])


    def classifyStroke(self, stroke):
        """*DEPRECATED*Classify a single stroke. """
        logger.warn("DEPRECATED classifyStroke")
        return self.classifyStrokeList([stroke])

    def classifyStrokeList(self, strokeList):
        """ Attempts to classify a stroke using the given training data. Returns a list of 
        tuples: (SymbolClass, score), or empty if it's rejected."""
        #we need at least three points
        #if len(stroke.Points) < 3:
            #return []
        rubineVector =  self.featureSet.generateVector(strokeList)
        maxScore = None
        maxCls = None
        classScores = []
        for symCls in self.symbolClasses.values():
            clsWeights = symCls.getWeights()
            if clsWeights is None: #Have not run calculateWeights yet
                bcp_logger.warn("Class weights are not set")
                continue
            val = clsWeights[0]
            for f_idx in range(len(self.featureSet)):
                val += rubineVector[f_idx] * clsWeights[f_idx+1]
            classScores.append({'symbol': symCls.name, 'score': val})
            if maxScore is None or (val > maxScore):
                maxScore = val
                maxCls = symCls
        maxScore = math.fabs(maxScore)
        classScores.sort(key = (lambda x: - x['score']) ) #Sort by the score
        sum = 0

        # Mahalanobis distance
        if self.debug:
            logger.debug("Mahalanobis distance")
        if maxCls is not None:
            delta = 0
            for j in range(len(self.featureSet)):
                for k in range(len(self.featureSet)):
                    delta += self.covarianceMatrixInverse[j,k] * (rubineVector[j] - self.averages[maxCls.name][j]) * (rubineVector[k] - self.averages[maxCls.name][k])

            if delta > len(self.featureSet) **2 / 2.0:
                logger.debug( "REJECT")
                return []# pass # print "DON'T RECOGNISE!"
            return classScores
        return []
        #self.getBoard().AnnotateStrokes( [stroke],  RubineAnnotation(self.names[maxIndex], height , 0))

    def saveWeights(self, fileName):
        """ Saves the current trainning data to a file given by fileName. This file can then be loaded by the rubine classifier """
        
        self.calculateWeights()

        if self.debug:
            logger.info("Saving training data to file: " + fileName)
        
        TB = ET.TreeBuilder()
        TB.start("rubine", {})

        for symCls in self.symbolClasses.values():
            TB.start("class", {'name':symCls.name})
            TB.start("weight0", {})
            TB.data(str(symCls.weight0))
            TB.end("weight0") # weight0

            for j in symCls.weights:
                TB.start("weight", {})
                TB.data(str(j))
                TB.end("weight")

            for j in self.averages[symCls.name]:
                TB.start("average", {})
                TB.data(str(j))
                TB.end("average")
            TB.end("class") # class

        TB.start("covariance", {})
        for i in range(len(self.featureSet)):
            TB.start("row", {})
            for j in range(len(self.featureSet)):
                TB.start("col", {})
                TB.data(str(self.covarianceMatrixInverse[i,j]))
                TB.end("col")

            TB.end("row")

        TB.end("covariance")
        TB.end("rubine") # rubine

        elem = TB.close()

        #ET.dump(elem)
        fd = open(fileName, "w")
        print >> fd, ET.tostring(elem)
        fd.close()

    def loadWeights(self, file):
        """ Loads the training data in the file. File is a file name """
        et = ET.parse(file)
        classes = et.findall("class")

        self.symbolClasses = {}
        self.averages = {}
        logger.debug("Loading %s classes" % (len(classes)))
        logger.debug("Using %s features" % (len(self.featureSet)))
        for cls_elem in classes:
            cls = ShellSymbolClass(self.featureSet)
            cls.fromXML(cls_elem)
            assert len(cls.weights) == len(self.featureSet), "Error, wrong featureset used! Loading %s features, expecting %s" % (len(cls.weights), len(self.featureSet))
            self.symbolClasses[cls.name] = cls
            self.averages[cls.name] = cls.getAverageFeatureValues()
            
        """
        for i in classes:
            
            self.names.append(i.get("name"))
            self.weight0.append(float(i.find("weight0").text))
            self.count += 1
            self.weights.append([])
            for j in i.findall("weight"):
                self.weights[self.count].append(float(j.text))
            self.averages.append([])
            for j in i.findall("average"):
                self.averages[self.count].append(float(j.text))
        """

        dims = (len(self.featureSet), len(self.featureSet))
        self.covarianceMatrixInverse = mat(zeros( dims ))
        covariance = et.find("covariance")
        rows = covariance.findall("row")
        for i in range(len(rows)):
            cols = rows[i].findall("col")
            for j in range(len(cols)):
                self.covarianceMatrixInverse[i,j] = float(cols[j].text)


#-------------------------------------
# if executed by itself, run all the doc tests

if __name__ == "__main__":
    Logger.setDoctest(logger)
    import doctest
    doctest.testmod()


