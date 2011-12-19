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
    def __init__(self, type, scale, accuracy):
        "Create a Rubin annotation."
        Annotation.__init__(self)
        self.type = type # a string for the text
        self.accuracy = accuracy
        self.scale = scale # an approximate "size" for the object
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

#------------------------------------------------------------

def getRubineVector(stroke):
    # normalize the stroke
    
    p = GeomUtils.strokeNormalizeSpacing(GeomUtils.strokeSmooth(stroke)).Points
    ul,br = GeomUtils.strokelistBoundingBox( [stroke] )
    for point in p:
        point.X -= ul.X
        point.Y -= br.Y

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
    for i in range(len(sp) -2):
        dxp = sp[i+1].X - sp[i].X   # delta x sub p
        dyp = sp[i+1].Y - sp[i].Y   # delta y sub p

        f8 += math.sqrt(dxp**2 + dyp**2)

        if i != 0:
            dxpOld = sp[i].X - sp[i-1].X   # delta x sub (p-1)
            dypOld = sp[i].Y - sp[i-1].Y   # delta y sub (p-1)
            if (dxp * dxpOld) + (dxp * dxpOld) != 0:
                angle = math.atan(((dxp * dypOld) - (dxpOld * dyp)) / ((dxp * dxpOld) + (dxp * dxpOld)))
                f9 += angle
                f10 += math.fabs(angle)
                f11 += angle*angle

    return [f1, f2, f3, f4, f5, f6, f7, f8, f9, f10 ,f11]

#------------------------------------------------------------

class RubineMarker( BoardObserver ):
    """Classifies strokes based on the Rubine classifier"""

    weights = []
    names = []
    weight0 = []

    covarianceMatrixInverse = []
    averages = []

    def __init__(self, file):
        """ Initiates the Rubine classifier. file is the name of a file containing the training data to be used. """
        BoardObserver.__init__(self)
        BoardSingleton().AddBoardObserver( self )
        BoardSingleton().RegisterForStroke( self )
        self.loadWeights(file)

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
            print cols
            for j in range(len(cols)):
                self.covarianceMatrixInverse[i,j] = float(cols[j].text)

    def sortByFeatureWeight(self, item):
        """ Internal Use Only """
        return item[0]

    def onStrokeAdded(self, stroke):
        """ Attempts to classify a stroke using the given training data """
        #we need at least three points
        if len(stroke.Points) < 3:
            return

        rubineVector =  getRubineVector(stroke)

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

        featureWeights.sort(key = self.sortByFeatureWeight)
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
        print "Mahalanobis distance"
        delta = 0
        for j in range(len(self.weights[0])):
            for k in range(len(self.weights[0])):
                delta += self.covarianceMatrixInverse[j,k] * (rubineVector[j] - self.averages[maxIndex][j]) * (rubineVector[k] - self.averages[maxIndex][k])

        print str(delta) + " : " + str(len(self.weights[0]) * len(self.weights[0]) * 0.5)

        if delta > len(self.weights[0]) * len(self.weights[0]) * 0.5:
            return # pass # print "DON'T RECOGNISE!"
        

        print self.names[maxIndex]

        height = stroke.BoundTopLeft.Y - stroke.BoundBottomRight.Y        
        BoardSingleton().AnnotateStrokes( [stroke],  RubineAnnotation(self.names[maxIndex], height , 0))

    #------------------------------------------------------------

class RubineTrainer( BoardObserver ):
    """Takes training data to create a file representing a rubine classifier"""

    count = -1

    features = []

    weights = []
    names = []
    weight0 = []

    covarianceMatrixInverse = []
    averages = []

    def __init__(self, isObserver = True):
        """Initiates the rubine trainer. If isObserver is true then it is added as an observer to the board"""
        print "trainer\n"
        self.reset()
        if isObserver:
            BoardObserver.__init__(self)
            BoardSingleton().AddBoardObserver( self )
            BoardSingleton().RegisterForStroke( self )

    def addToBoard(self):
        """ Added the trainer to the board"""
        BoardObserver.__init__(self)
        BoardSingleton().AddBoardObserver( self )
        BoardSingleton().RegisterForStroke( self )

    def reset(self):
        """ Resets the trainer """
        count = -1
        features = []

        weights = []
        names = []
        weight0 = 0

        covarianceMatrixInverse = []
        averages = []

    def newClass(self, name = None):
        """ Creates a new class for the trainer. Name must be a string"""
        self.count += 1;
        self.features.append([])
        if name == None:
            name = str(self.count)
        self.names.append(name)
        #print "Starting class " + str(self.count)

    def onStrokeAdded(self, stroke):
        """ Adds a stroke """
        self.addStroke(stroke)

    def addStroke(self, stroke):
        """ Adds a stroke to the current class """
        #we need at least three points
        if len(stroke.Points) < 3:
            return

        feature = getRubineVector(stroke)
        self.features[self.count].append(feature)

    def getCovMatrixForClass(self, c, averages):
        """ Calculates the covariance matrix for a class. For Internal use only """
        cmc = mat(zeros((len(self.features[0][0]),len(self.features[0][0]))))
        for i in range(len(self.features[c][0])):
            for j in range(len(self.features[c][0])):
                for e in self.features[c]:
                    cmc[i,j] += (e[i] - averages[c][i]) * ( e[j] - averages[c][j])
        return cmc

    def getAverageForClass(self, examples):
        """ Calculates the averages for a class. For Internal use only """
        averages = zeros(len(examples[0]))
        for e in examples: 
            for i in range(len(e)):
                averages[i] += e[i]
        
        for i in range(len(averages)):
            averages[i] /= len(examples)

        return averages

    def calculateWeights(self):
        """ Creates teh training data based on the current classes. Call this before saving the weights """
        self.averages = []
        cm =  mat(zeros((len(self.features[0][0]),len(self.features[0][0]))))
        cmc = [] # covariance matrix for each class
        for c in self.features: # the gesture classes
            self.averages.append(self.getAverageForClass(c))
            
        dividor = -len(self.features)
        for c in range(len(self.features)):
            dividor += len(self.features[c])
            cmc.append(self.getCovMatrixForClass(c, self.averages))

        for i in range(len(self.features[0][0])):
            for j in range(len(self.features[0][0])):
                for c in range(len(self.features)):
                    cm[i,j] += (cmc[c])[i,j] # / (len(self.features[0]) - 1)
                cm[i,j] /= dividor

        #print cm
        #print linalg.det(cm)
        cm = cm.I
        self.covarianceMatrixInverse = cm

        self.weight0 = zeros(len(self.features))
        for c in range(len(self.features)):
            self.weights.append(zeros(len(self.features[c][0])))
            for j in range(len(self.features[0][0])):
                for i in range(len(self.features[0][0])):
                    self.weights[c][j] += cm[i,j] * self.averages[c][i]
                self.weight0[c] +=  self.weights[c][j] * self.averages[c][j]
            self.weight0[c] /= -2

        # normalize the weights
        maxWeight = 0.0
        '''
        for c in self.weights:
            for weight in c:
                if math.fabs(weight) > maxWeight:
                    maxWeight = math.fabs(weight)
        
        for c in self.weights:
            for i in range(len(c)):
                c[i] /= maxWeight

        for i in range(len(self.weight0)):
            self.weight0[i] /= maxWeight
        '''

        #print self.weights
        #print self.weight0

    def saveWeights(self, fileName):
        """ Saves the current trainning data to a file given by fileName. This file can then be loaded by the rubine classifier """
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

            for j in self.averages[i]:
                TB.start("average", {})
                TB.data(str(j))
                TB.end("average")
            TB.end("class") # class

        TB.start("covariance", {})
        for i in range(len(self.averages[0])):
            TB.start("row", {})
            for j in range(len(self.averages[0])):
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

class RubineVisualizer( ObserverBase.Visualizer ):

    def __init__(self):
        ObserverBase.Visualizer.__init__( self, RubineAnnotation )

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
        SketchGUI.drawBox(ul, br, color="#a0a0a0")
        SketchGUI.drawText( br.X - 15, br.Y, a.type , size=15, color="#a0a0a0" )

#-------------------------------------
# if executed by itself, run all the doc tests

if __name__ == "__main__":
    Logger.setDoctest(logger)
    import doctest
    doctest.testmod()

