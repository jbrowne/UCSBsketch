from SketchFramework.Stroke import Stroke
from SketchFramework.Point import Point
from Utils import Logger

logger = Logger.getLogger("CubicCurve", Logger.WARN)

class CubicCurve(object):
    def __init__(self, p0,p1, p2, p3):
        if p0 == None or p1 == None or p2 == None or p3 == None:
            logger.warn("Creating invalid CubicCurve, %s" % ( [p0, p1, p2, p3] ) )
        self.p0 = p0
        self.p1 = p1
        self.p2 = p2
        self.p3 = p3
        logger.debug("Created curve: %s" % (self))
    def getControlPoints(self):
        return (self.p0, self.p1, self.p2, self.p3)

    def toStroke(self, numpts = 30):
        p0 = self.p0
        p1 = self.p1
        p2 = self.p2
        p3 = self.p3

        points = [None] * numpts

        numpts = max (1, numpts)
        inc = 1 / float(numpts)
        t = 0.0
        for i in range(numpts):
        #while t < 1.0:
            t = i * inc
            x = (1-t) **3 * p0.X \
                + 3 * (1-t) ** 2 * t * p1.X \
                + 3 * (1-t) * t **2 * p2.X \
                + t ** 3 * p3.X

            y = (1-t) **3 * p0.Y \
                + 3 * (1-t) ** 2 * t * p1.Y \
                + 3 * (1-t) * t **2 * p2.Y \
                + t ** 3 * p3.Y
            points[i] = Point(x,y)
        return Stroke(points)
    def __repr__(self):
        return "C(%s,%s,%s,%s)" % (self.p0, self.p1, self.p2, self.p3)


        

