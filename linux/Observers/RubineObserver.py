"""
filename: RubineObserver.py

description:
   Using the Rubine classifier to detect strokes

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

from numpy  import *

logger = Logger.getLogger('TextObserver', Logger.WARN )

#-------------------------------------

class RubineAnnotation(Annotation):
    def __init__(self, text, scale):
        "Create a Rubin annotation."
        Annotation.__init__(self, type, accuracy)
        self.type = type # a string for the text
        self.accuracy = accuracy
        self.scale = scale # an approximate "size" for the text
        self.alternates = []
    '''def xml(self):
        root = Annotation.xml(self)
        root.attrib["text"] = self.text
        root.attrib['scale'] = str(self.scale)
        for i, a in enumerate(self.alternates):
            textEl = ET.SubElement(root, "alt")
            textEl.attrib['priority'] = str(i)
            textEl.attrib['text'] = str(a)
            root.append(textEl)
        return root
    '''

#-------------------------------------

def scalePointsToSquare(points, size):
    "Input: A list of points. Outputs the list of points transformed to a square"
    ul,br = GeomUtils.pointlistBoundingBox( points )
    if (ul.Y - br.Y) == 0:
        h = 1
    else:
        h = size / (ul.Y - br.Y)
    if (br.X - ul.X) == 0:
        w = 1
    else:
        w = size / (br.X - ul.X)

    bl = br.copy()
    bl.X = ul.X
    returnPoints = []
    for p in points:
        returnPoints.append(Point( w*(p.X - bl.X), h*(p.Y - bl.Y) ))

    return returnPoints


def getRubineVector(stroke):
    # normalize the stroke
    
    p = GeomUtils.strokeNormalizeSpacing(stroke).Points

    # scale the stroke to a known length

    sp = p
    #sp = scalePointsToSquare(p, 100)

    # The first feature is the cosine of the inital angle
    # The second feature is the sine of the inital angle
    if GeomUtils.pointDist(sp[0], sp[2]) != 0:
        f1 = (sp[2].X - sp[0].X) / GeomUtils.pointDist(sp[0], sp[2])
        f2 = (sp[2].Y - sp[0].Y) / GeomUtils.pointDist(sp[0], sp[2])
    else:
        f1 = 0
        f2 = 0

    ul,br = GeomUtils.strokelistBoundingBox( [stroke] )
    # the third is the length of the diagonal of the bb
    f3 = GeomUtils.pointDist(ul, br)
    # 4th is the angle of the bounding box diagonal
    if (br.X - ul.X) != 0:
        f4 = math.atan((ul.Y - br.Y)/ (br.X - ul.X))
    else:
        f4 = 0

    last = len(p) - 1
    # 5th is the length between the first and last point
    f5 = GeomUtils.pointDist(sp[0], sp[last])
    # the 6th and 7th are the cosine and sine of the angle between the first and last point
    if GeomUtils.pointDist(sp[0], sp[last]) != 0:
        f6 = (sp[last].X - sp[0].X) / GeomUtils.pointDist(sp[0], sp[last])
        f7 = (sp[last].Y - sp[0].Y) / GeomUtils.pointDist(sp[0], sp[last])
    else:
        f6 = 0
        f7 = 0

    # 8th and 9th are the sum of the lengths and angles
    # 10th and 11th are the sum of the absolute value of the angels and to sum of the angles squared
    f8 = 0 # length sum
    f9 = 0 # angle sum
    f10 = 0 # sum of the absolute value of the angle
    f11 = 0 # sum of the angle squared
    for i in range(len(sp) -1):
        f8 += GeomUtils.pointDist(sp[i], sp[i+1])
        if (sp[i].X*sp[i+1].X + sp[i].Y*sp[i+1].Y) != 0:
            angle = math.atan((sp[i+1].X * sp[i].Y - sp[i].X * sp[i+1].Y) / (sp[i].X*sp[i+1].X + sp[i].Y*sp[i+1].Y))
            f9 += angle
            f10 += math.fabs(angle)
            f11 += angle*angle

    return [f1, f2, f3, f4, f5, f6, f7, f8, f9, f10 ,f11]

#-------------------------------------

covarianceMatrixInverse = []
averages = []

class RubineTrainer( BoardObserver ):
    """Class initialized by the TextCollector object"""

    _isTraining = 0
    count = -1

    features = []
    testCasesNeeded = 5

    weights = []
    names = []
    weight0 = []
    

    def __init__(self):
        BoardObserver.__init__(self)
        self.marker = RubineMarker(self.weights, self.weight0)
        BoardSingleton().AddBoardObserver( self.marker )
        BoardSingleton().RegisterForStroke( self.marker )
        print "Trainer"
    def onStrokeAdded(self, stroke):
        print "Trainer"

        #we need at least three points
        if len(stroke.Points) < 3:
            return

        feature = getRubineVector(stroke)
        self.features[self.count].append(feature)
        print feature

    def newClass(self):
        if not self._isTraining:
            return

        self.count += 1;
        self.features.append([])
        self.names.append(str(self.count))
        print "Starting class " + str(self.count)


    def getCovMatrixForClass(self, c, averages):
        cmc = mat(zeros((len(self.features[0][0]),len(self.features[0][0]))))
        for i in range(len(self.features[c][0])):
            for j in range(len(self.features[c][0])):
                for e in self.features[c]:
                    cmc[i,j] += (e[i] - averages[c][i]) * ( e[j] - averages[c][j])
        return cmc

    def getAverageForClass(self, examples):
        averages = zeros(len(examples[0]))
        for e in examples: 
            for i in range(len(e)):
                averages[i] += e[i]
        
        for i in range(len(averages)):
            averages[i] /= len(examples)

        return averages

    def calculateWeights(self):
        global covarianceMatrixInverse
        global averages

        averages = []
        cm =  mat(zeros((len(self.features[0][0]),len(self.features[0][0]))))
        cmc = []
        for c in self.features: # the gesture classes
            averages.append(self.getAverageForClass(c))
            
        dividor = -len(self.features)
        for c in range(len(self.features)):
            dividor += len(self.features[c])

        for i in range(len(self.features[0][0])):
            for j in range(len(self.features[0][0])):
                for c in range(len(self.features)):
                    cm[i,j] += (self.getCovMatrixForClass(c, averages))[i,j] / (len(self.features[0]) - 1)
                cm[i,j] /= dividor

        #print cm
        #print linalg.det(cm)
        cm = cm.I
        covarianceMatrixInverse = cm

        self.weight0 = zeros(len(self.features))
        for c in range(len(self.features)):
            self.weights.append(zeros(len(self.features[c][0])))
            for j in range(len(self.features[0][0])):
                for i in range(len(self.features[0][0])):
                    self.weights[c][j] += cm[i,j] * averages[c][i]
                self.weight0[c] +=  self.weights[c][j] * averages[c][j]
            self.weight0[c] /= -2

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



        print self.weights
        print self.weight0

    def finishTraining(self):
        if not self._isTraining:
            return

        print "Finish Training"
        self._isTraining = 0
        BoardSingleton().RemoveBoardObserver(self)
        BoardSingleton().UnregisterStrokeObserver(self)

        # calculate the feature weights
        self.calculateWeights()

        #self.featureCount += 1
        self.marker.setWeights(self.weights, self.weight0, self.names)
        BoardSingleton().AddBoardObserver( self.marker )
        BoardSingleton().RegisterForStroke( self.marker )

    def startTraining(self):
        if self._isTraining:
            return

        print "Start Training"
        self._isTraining = 1

        BoardSingleton().RemoveBoardObserver(self.marker)
        BoardSingleton().UnregisterStrokeObserver(self.marker)

        BoardSingleton().AddBoardObserver( self )
        BoardSingleton().RegisterForStroke( self )
        self.newClass()
       
    def saveWeights(self):
        TB = ET.TreeBuilder()
        TB.start("rubine", {})
        for i in range(self.count + 1):
            TB.start("class", {'name':self.names[i]})
            TB.start("weight0", {})
            TB.data(str(self.weight0[i]))
            TB.end("weight0") # weight0
            for j in self.weights[i]:
                TB.start("weight", {})
                TB.data(str(j))
                TB.end("weight")
            TB.end("class") # class

        TB.end("rubine") # rubine

        elem = TB.close()

        ET.dump(elem)
        fd = open("rubine.dat", "w")
        print >> fd, ET.tostring(elem)
        fd.close()

    def loadWeights(self):
        et = ET.parse("rubine.dat")
        classes = et.findall("class")
        self.count = -1

        for i in classes:
            self.names.append(i.get("name"))
            self.weight0.append(float(i.find("weight0").text))
            self.count += 1
            self.weights.append([])
            for j in i.findall("weight"):
                self.weights[self.count].append(float(j.text))
                
        print self.names
        print self.weight0
        print self.weights
        self.marker.setWeights(self.weights, self.weight0, self.names)
            

#-------------------------------------


l_logger = Logger.getLogger('LetterMarker', Logger.WARN)
class RubineMarker( BoardObserver ):
    """Class initialized by the TextCollector object"""

    weights = []
    names = []
    weight0 = 0

    def __init__(self, weights, weight0):
        BoardObserver.__init__(self)
        #BoardSingleton().AddBoardObserver( self )
        #BoardSingleton().RegisterForStroke( self )
        #print "marker"

    def sortByFeatureWeight(self, item):
        return item[0]

    def onStrokeAdded(self, stroke):

        global covarianceMatrixInverse
        global averages

        print "marker"

        #we need at least three points
        if len(stroke.Points) < 3:
            return

        rubineVector =  getRubineVector(stroke)

        max = 0.00000001
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

        featureWeights.sort(key = self.sortByFeatureWeight)
        #print featureWeights[len(featureWeights)-1][1]
        sum = 0
        
        l = len(featureWeights) - 1
        for i in range(l+1):
            print (featureWeights[i][0] ) - (featureWeights[l][0] )
            print  math.exp((featureWeights[i][0] / max) - (featureWeights[l][0] / max))
            sum += math.exp((featureWeights[i][0] / max) - (featureWeights[l][0] / max))

        print sum
        if sum != 0:
            print 1/sum
        else:
            print 0
        
        '''
        # Mahalanobis distance
        delta = 0
        for j in range(len(self.weights[0])):
            for k in range(len(self.weights[0])):
                delta += covarianceMatrixInverse[j,k] * (rubineVector[j] - averages[maxIndex][j]) * (rubineVector[k] - averages[maxIndex][k])

        print str(delta) + " : " + str(len(self.weights[0]) * len(self.weights[0]) * 0.5)

        if delta > len(self.weights[0]) * len(self.weights[0]) * 0.5:
            print "DON'T RECOGNISE!"
        '''

        print self.names[maxIndex]

    def setWeights(self, weights, weight0, names):
        self.weights = weights
        self.weight0 = weight0
        self.names = names
        
#-------------------------------------

    

#-------------------------------------

class RubineVisualizer( ObserverBase.Visualizer ):

    def __init__(self):
        ObserverBase.Visualizer.__init__( self, RubineAnnotation )

    def drawAnno( self, a ):
        ul,br = GeomUtils.strokelistBoundingBox( a.Strokes )
        logger.debug(a.Strokes)
        height = ul.Y - br.Y
        midpointY = (ul.Y + br.Y) / 2
        midpointX = (ul.X + br.X) / 2
        left_x = midpointX - a.scale / 2.0
        right_x = midpointX + a.scale / 2.0
        SketchGUI.drawBox(ul, br, color="#a0a0a0")

#-------------------------------------
# if executed by itself, run all the doc tests

if __name__ == "__main__":
    Logger.setDoctest(logger)
    import doctest
    doctest.testmod()
