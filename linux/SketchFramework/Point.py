import sys
from SketchFramework.Annotation import Annotation, AnnotatableObject

class Point(AnnotatableObject):   
    "Point defined by X, Y, T.  X,Y Cartesian Coords, T as Time"
    def __init__(self, xLoc, yLoc, drawTime=0):
        AnnotatableObject.__init__(self)
        #self.X = int(xLoc)
        #self.Y = int(yLoc)
        #self.T = int(drawTime)
        self.X = float(xLoc)
        self.Y = float(yLoc)
        self.T = float(drawTime)

    def distance(self, point2):
         "Returns the distance from this point to the point in argument 1"
         from Utils import GeomUtils
         return GeomUtils.pointDist(self, point2)

    def copy(self):
        return Point(self.X, self.Y, self.T)

    def __str__(self):
        return "(" + ("%.1f" % self.X) + "," + ("%.1f" % self.Y) + ")"
        #return "(" + str(self.X) + "," + str(self.Y) + ")"
        #return "(" + str(self.X) + "," + str(self.Y) + "," + str(self.T) + ")"
