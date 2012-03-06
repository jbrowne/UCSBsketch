"""
filename: Rubine.py

description:
   Using the Rubine classifier to detect strokes

Doctest Examples:

>>> t = TextMarker()

"""

#-------------------------------------

import pdb
import math
import traceback
from Utils import Logger
from Utils import GeomUtils

from SketchFramework.Point import Point
from SketchFramework.Stroke import Stroke

from xml.etree import ElementTree as ET

from numpy  import *

logger = Logger.getLogger('Rubine', Logger.DEBUG )

#------------------------------------------------------------
class FeatureSet(object):
    """An abstract class for running sets of feature methods on strokes"""
    def __init__(self):
        pass
    def generateVector(strokeList):
        """This method takes in a list of strokes and returns a tuple of floats for the scores of each feature"""
        return (0.0)
    def __len__(self):
        """Return how many feature values are in a vector"""
        return 0

#------------------------------------------------------------
class BCPFeatureSet(FeatureSet):
    """Feature set found to be best for Rubine's classifier in
    Blagojevic, et al. "The Power of Automatic Feature Selection: 
    Rubine on Steroids" 2010"""
    def __init__(self):
        FeatureSet.__init__(self)

    def __len__(self):
        return 10

    def generateVector(self, strokeList):
        """Assemble the vector of feature scores from a list of strokes, presumed to
        make up a single symbol."""
        retVector = []

        #Set up the common data
        if len(strokeList) > 1:
            logger.warn("Concatenating multiple strokes")
            stroke = Stroke( [ p for stk in strokeList for p in stk.Points ])
        elif len(strokeList) == 1:
            stroke = strokeList[0]

        convexHull = Stroke(GeomUtils.convexHull(stroke.Points))
        strokeLength = GeomUtils.strokeLength(stroke)
        boundingBox = (stroke.BoundTopLeft, stroke.BoundBottomRight)

        #Generate the vector
        retVector = (self.f1_12(stroke) , \
                     self.f2_7(strokeLength, convexHull) , \
                     self.f2_8(strokeLength, boundingBox) , \
                     self.f5_1(stroke), \
                     self.f7_2(boundingBox) , \
                     self.f7_7(convexHull, boundingBox) , \
                     self.f7_10(strokeLength) , \
                     self.f7_13(strokeLength) , \
                     self.f7_16(convexHull) , \
                     self.f7_17(convexHull) \
                    )

        assert len(self) == len(retVector)
        return retVector
    #-----------------------------------------------
    #   Features common to all symbol classes
    #-----------------------------------------------
    def f1_12(self, stroke):
        """Distance from the first point of the stroke to the 
        last point of the stroke [Rub91]"""
        return GeomUtils.pointDist(stroke.Points[0], stroke.Points[-1])

    def f1_16(self, stroke):
        """Number of fragments in a stroke, according to its corners [BSH04]"""
        raise NotImplemented
        return 1.0

    def f2_7(self, strokeLen, cvxHull):
        """Stroke length / perimeter of the stroke's convex hull [FPJ02]"""
        cvx_perimeter = GeomUtils.strokeLength(cvxHull)
        if cvx_perimeter > 0.0:
            return strokeLen / cvx_perimeter
        else:
            return 1.0

    def f2_8(self, strokeLen, bbox):
        """Length of the stroke divided by the length of the bounding box
        diagonal. Adapted from [Rub91]"""
        diagDist = GeomUtils.pointDist( bbox[0], bbox[1])
        if diagDist > 0:
            return strokeLen / float(diagDist)
        else:
            return 1.0

    def f5_1(self, stroke):
        """Number of self intersections at the endpoints of the stroke, adapted
        from [Qin05]"""
        selfIntersections = 0
        for i in range(len(stroke.Points)-1):
            seg1 = (stroke.Points[i], stroke.Points[i+1])
            for j in range(i+1, len(stroke.Points)-1):
                seg2 = (stroke.Points[j], stroke.Points[j+1])
                cross = GeomUtils.getLinesIntersection( seg1, seg2 )
                if cross is not None:
                    selfIntersections += 1
        return selfIntersections
 

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
    
    def f7_10(self, strokeLen):
        """Total length of the stroke [Rub91]"""
        return strokeLen

    def f7_13(self, strokeLen):
        """Log of the total length of the stroke. [LLR*00, MFN93]"""
        if strokeLen > 0.0:
            return math.log(strokeLen)
        else:
            return 0.0

    def f7_16(self, cvxHull):
        """Perimeter efficiency: 2 * sqrt( pi * convex hull area ) / convex hull perimeter
        [LC02]"""
        cvxArea = GeomUtils.area(cvxHull.Points)
        cvxPerim = GeomUtils.strokeLength(cvxHull)

        if cvxPerim > 0.0:
            return 2 * math.sqrt( math.pi * cvxArea) / cvxPerim 
        else:
            return 1.0

    def f7_17(self, cvxHull):
        """Ratio of perimeter to area of the stroke's convex hull [FPJ02]"""
        cvxArea = GeomUtils.area(cvxHull.Points)
        cvxPerim = GeomUtils.strokeLength(cvxHull)
        if cvxPerim > 0.0:
            return cvxArea / float(cvxPerim)
        else:
            return 1.0


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
        pointList = stroke.Points
        f9 = 0 # angle sum
        for i in range(len(pointList) -2):
            dxp = pointList[i+1].X - pointList[i].X   # delta x sub p
            dyp = pointList[i+1].Y - pointList[i].Y   # delta y sub p

            if i != 0:
                dxpOld = pointList[i].X - pointList[i-1].X   # delta x sub (p-1)
                dypOld = pointList[i].Y - pointList[i-1].Y   # delta y sub (p-1)
                if (dxp * dxpOld) + (dxp * dxpOld) != 0:
                    angle = math.atan(((dxp * dypOld) - (dxpOld * dyp)) / ((dxp * dxpOld) + (dxp * dxpOld)))
                    f9 += angle
        return f9

    def f10(self, stroke):
        # 10th and 11th are the sum of the absolute value of the angels and to sum of the angles squared
        pointList = stroke.Points
        f10 = 0 # sum of the absolute value of the angle
        for i in range(len(pointList) -2):
            dxp = pointList[i+1].X - pointList[i].X   # delta x sub p
            dyp = pointList[i+1].Y - pointList[i].Y   # delta y sub p

            if i != 0:
                dxpOld = pointList[i].X - pointList[i-1].X   # delta x sub (p-1)
                dypOld = pointList[i].Y - pointList[i-1].Y   # delta y sub (p-1)
                if (dxp * dxpOld) + (dxp * dxpOld) != 0:
                    angle = math.atan(((dxp * dypOld) - (dxpOld * dyp)) / ((dxp * dxpOld) + (dxp * dxpOld)))
                    f10 += math.fabs(angle)
        return f10

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

class RubineClassifier():
    """Classifies strokes based on the Rubine classifier"""


    def __init__(self, featureSet = BCPFeatureSet(), debug=False):
        """ Initiates the rubin classifier.
            file is the data file generated by the rubine trainer
            debug is an optional flag to print debug information.

        """
        self.debug = debug
        #self.featureSet = RubineFeatureSet()
        self.featureSet = featureSet
        self.weights = []
        self.names = []
        self.weight0 = []

        self.covarianceMatrixInverse = []
        self.averages = []

    def loadWeights(self, file):
        """ Loads the training data in the file. File is a file name """
        et = ET.parse(file)
        classes = et.findall("class")
        self.count = -1

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

        self.covarianceMatrixInverse = mat(zeros((len(self.averages[0]),len(self.averages[0]))))
        covariance = et.find("covariance")
        rows = covariance.findall("row")
        for i in range(len(rows)):
            cols = rows[i].findall("col")
            if self.debug:
                print cols
            for j in range(len(cols)):
                self.covarianceMatrixInverse[i,j] = float(cols[j].text)


    def classifyStroke(self, stroke):
        """ Attempts to classify a stroke using the given training data """
        #we need at least three points
        if len(stroke.Points) < 3:
            return None

        rubineVector =  self.featureSet.generateVector([stroke])

        max = -100000.0
        maxIndex = 0
        featureWeights = []
        for i in range(len(self.weight0)):
            val = self.weight0[i]
            for j in range(len(self.weights[i])):
                val += rubineVector[j]*self.weights[i][j]
            featureWeights.append([val, i])
            if (val > max):
                max = val
                maxIndex = i

        max = math.fabs(max)

        featureWeights.sort(key = (lambda x: x[0]) )
        #print featureWeights[len(featureWeights)-1][1]
        sum = 0
        '''
        l = len(featureWeights) - 1
        for i in range(l+1):
            print "\n"
            print featureWeights[i][0] / max
            print (featureWeights[i][0] / max ) - (featureWeights[l][0] / max )
            print  math.exp((featureWeights[i][0] / max) - (featureWeights[l][0] / max))
            sum += math.exp((featureWeights[i][0] / max) - (featureWeights[l][0] / max))

        print "probability"
        print sum
        if sum != 0:
            print 1/sum
        else:
            print 0
        '''
        
        # Mahalanobis distance
        if self.debug:
            print "Mahalanobis distance"
        delta = 0
        for j in range(len(self.weights[0])):
            for k in range(len(self.weights[0])):
                delta += self.covarianceMatrixInverse[j,k] * (rubineVector[j] - self.averages[maxIndex][j]) * (rubineVector[k] - self.averages[maxIndex][k])
        
        if self.debug:
            print str(delta) + " : " + str(len(self.weights[0]) * len(self.weights[0]) * 0.5)

        if delta > len(self.weights[0]) * len(self.weights[0]) * 0.5:
            print "REJECT"
            return None# pass # print "DON'T RECOGNISE!"
        
        if self.debug:
            print self.names[maxIndex]

        return self.names[maxIndex]

        #self.getBoard().AnnotateStrokes( [stroke],  RubineAnnotation(self.names[maxIndex], height , 0))


#------------------------------------------------------------
#------------------------------------------------------------
class SymbolClass (object):
    COUNT = 0
    def __init__(self, featureSet, name = None):
        """Initialize a new symbol class without any examples"""
        logger.debug("SymbolClass intantiated: %s" % (name))
        self.featureSet = featureSet
        #self.examples = []
        self.featureVectors = []
        self.weights = []
        if name == None:
            self.name = str(SymbolClass.COUNT)
        else:
            self.name = name
        SymbolClass.COUNT += 1
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
            for f_j in range (numFeatures):
                for sVect in self.featureVectors:
                    cmc[f_i,f_j] += (sVect[f_i] - avgFeatureVals[f_i]) * ( sVect[f_j] - avgFeatureVals[f_j])
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
                self.weights[w_idx] += invCovMatrix[f_i,w_idx] * avgFeatureVals[f_i]
            self.weight0 +=  self.weights[w_idx] * avgFeatureVals[w_idx]
        self.weight0 /= -2.0
#------------------------------------------------------------
#------------------------------------------------------------

class RubineTrainer():
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

    def reset(self):
        """ Resets the trainer """
        self.count = -1
        self.symbolClasses = {}
        self.averages = {}

        #self.features = [] #Lists of example stroke feature vectors indexed by gesture class
        #self.weights = [] #Vectors of feature weights indexed by gesture class
        #self.names = [] #Names of each gesture, indexed by gesture class
        #self.weight0 = [] #List of "zero" weights indexed by class

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
        if clsName != None and clsName in self.symbolClasses:
            if clsName in self.symbolClasses:
                symCls = self.symbolClasses[clsName]
            else:
                symCls = self.symbolClasses[clsName] =  SymbolClass(self.featureSet, name = clsName) 
        else:
            raise Exception("Cannot add stroke to Symbol 'None'")
        #we need at least three points
        if len(stroke.Points) < 3:
            raise Exception("Not enough points in this stroke: %s" % (str(stroke)))

        symCls.addStrokes([stroke])

        if self.debug:
            print "Stroke added to class: " + symCls.name

    def calculateWeights(self):
        """ Creates teh training data based on the current classes. Call this before saving the weights """
        numFeatures = len(self.featureSet)
        dividor = 0
        self.averages = {}
        for name, symCls in self.symbolClasses.items():
            print "Class %s: %s examples" % (name, len(symCls))
            dividor += len(symCls) - 1 #Number of examples - 1
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


        self.covarianceMatrixInverse = invCovMatrix = avgCovMat.I

        for symCls in self.symbolClasses.values():
            symCls.calculateWeights(invCovMatrix, self.averages[symCls.name])
        """
        self.averages = []
        cmc = [] # covariance matrix for each class
        for fVectList in self.features: # the gesture classes
            self.averages.append(self._getAverageForClass(fVectList))
            
        numClasses = len(self.features)
        dividor = - numClasses # - number of classes
        for c in range(numClasses):
            dividor += len(self.features[c]) #number of examples for class c
            cmc.append(self._getCovMatrixForClass(c, self.averages))

        cm =  mat(zeros((numFeatures, numFeatures)))
        for f_i in range(numFeatures):
            for f_j in range(numFeatures):
                for symCls in range(numClasses):
                    cm[f_i,f_j] += (cmc[c])[f_i,f_j] # / (len(self.features[0]) - 1)
                cm[f_i,f_j] /= dividor

        #print cm
        #print linalg.det(cm)
        cm = cm.I
        self.covarianceMatrixInverse = cm

        self.weight0 = zeros(numClasses)
        for c in range(numClasses):
            self.weights.append(zeros( numFeatures ))
            for w_idx in range(numFeatures):
                for f_i in range(numFeatures):
                    self.weights[c][w_idx] += cm[f_i,w_idx] * self.averages[c][f_i]
                self.weight0[c] +=  self.weights[c][w_idx] * self.averages[c][w_idx]
            self.weight0[c] /= -2.0

        # normalize the weights
        maxWeight = 0.0
        for c in self.weights:
            for weight in c:
                if math.fabs(weight) > maxWeight:
                    maxWeight = math.fabs(weight)
        
        for c in self.weights:
            for i in range(len(c)):
                c[i] /= maxWeight

        for i in range(len(self.weight0)):
            self.weight0[i] /= maxWeight
        """
        if self.debug:
            for name, symCls in self.symbolClasses.items():
                print "Class: %s" % (name)
                print symCls.weight0, symCls.weights

    def saveWeights(self, fileName):
        """ Saves the current trainning data to a file given by fileName. This file can then be loaded by the rubine classifier """
        
        self.calculateWeights()

        if self.debug:
            print "Saving training data to file: " + fileName
        
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

        ET.dump(elem)
        fd = open(fileName, "w")
        print >> fd, ET.tostring(elem)
        fd.close()

#-------------------------------------
# if executed by itself, run all the doc tests

if __name__ == "__main__":
    Logger.setDoctest(logger)
    import doctest
    doctest.testmod()

