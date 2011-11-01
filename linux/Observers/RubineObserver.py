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

def getRubineVector(stroke):
    p = GeomUtils.strokeNormalizeSpacing(stroke).Points
    # The first feature is the cosine of the inital angle
    f1 = (p[2].X - p[0].X) / GeomUtils.pointDist(p[0], p[2])
    # The second feature is the sine of the inital angle
    f2 = (p[2].Y - p[0].Y) / GeomUtils.pointDist(p[0], p[2])

    ul,br = GeomUtils.strokelistBoundingBox( [stroke] )
    # the third is the length of the diagonal of the bb
    f3 = GeomUtils.pointDist(ul, br)
    # 4th is the angle of the bounding box diagonal
    f4 = math.atan((ul.Y - br.Y)/ (br.X - ul.X))

    last = len(p) - 1
    # 5th is the length between the first and last point
    f5 = GeomUtils.pointDist(p[0], p[last])
    # the 6th and 7th are the cosine and sine of the angle between the first and last point
    f6 = (p[last].X - p[0].X) / GeomUtils.pointDist(p[0], p[last])
    f7 = (p[last].Y - p[0].Y) / GeomUtils.pointDist(p[0], p[last])

    # 8th and 9th are the sum of the lengths and angles
    # 10th and 11th are the sum of the absolute value of the angels and to sum of the angles squared
    f8 = 0 # length sum
    f9 = 0 # angle sum
    f10 = 0 # sum of the absolute value of the angle
    f11 = 0 # sum of the angle squared
    for i in range(len(p) -1):
        f8 += GeomUtils.pointDist(p[i], p[i+1])
        angle = math.atan((p[i+1].X * p[i].Y - p[i].X * p[i+1].Y) / (p[i].X*p[i+1].X + p[i].Y*p[i+1].Y))
        f9 += angle
        f10 += math.fabs(angle)
        f11 += angle*angle

    return [f1, f2, f3, f4, f5, f6, f7, f8, f9, f10 ,f11]

#-------------------------------------

class RubineTrainer( BoardObserver ):
    """Class initialized by the TextCollector object"""

    _isTraining = 0
    count = 0

    features = []

    testCasesNeeded = 5

    def __init__(self):
        BoardObserver.__init__(self)
        self.marker = RubineMarker()
        print "Trainer"
    def onStrokeAdded(self, stroke):
        print "Trainer"

        if mod(self.count, self.testCasesNeeded) == 0:
            self.features.append([])
        
        cur = self.features[len(self.features)-1]


        feature = getRubineVector(stroke)
        cur.append(feature)
        self.count += 1
        print feature

    def calculateWeights(self):
        averages = []
        cm =  mat(zeros((len(self.features[0][0]),len(self.features[0][0]))))
        for c in range(len(self.features)): # the gesture classes
            averages.append(zeros(len(self.features[c][0])))
            for j in self.features[c]: # individual test caeses in a class
                for k in range(len(j)): # individual fatures in a test
                    averages[c][k] += j[k]
                #print j
            for j in range(len(averages[c])):
                averages[c][j] /= len(self.features[c])
            print averages[c]

            #compute the sample covariance matrix
            for i in range(len(self.features[c][0])):
                for j in range(len(self.features[c][0])):
                    val = 0
                    for e in self.features[c]:
                        val += (e[i] - averages[c][i]) * ( e[j] - averages[c][j])
                    cm[i,j] += val / (len(self.features[c]) - 1)
        
        for i in range(len(self.features[0][0])):
            for j in range(len(self.features[0][0])):
                cm[i,j] /= len(self.features)*len(self.features[0]) - len(self.features)

        print cm
        print linalg.det(cm)
        cm = cm.I

        weights = []
        weight0 = zeros(len(self.features))

        for c in range(len(self.features)):
            weights.append(zeros(len(self.features[c][0])))
            for j in range(len(self.features[0][0])):
                for i in range(len(self.features[0][0])):
                    weights[c][j] += cm[i,j] * averages[c][i]
                weight0[c] +=  weights[c][j] * averages[c][j]
            weight0[c] /= -2



        print weights
        print weight0


                

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
        

#-------------------------------------

l_logger = Logger.getLogger('LetterMarker', Logger.WARN)
class RubineMarker( BoardObserver ):
    """Class initialized by the TextCollector object"""
    def __init__(self):
        BoardObserver.__init__(self)
        #BoardSingleton().AddBoardObserver( self )
        #BoardSingleton().RegisterForStroke( self )
        #print "marker"
    def onStrokeAdded(self, stroke):
        print "marker"
        print getRubineVector(stroke)

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
