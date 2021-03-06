from SketchFramework.Annotation import Annotation, AnnotatableObject
from xml.etree import ElementTree as ET
import math
import sys

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

    def xml(self):
        root = ET.Element("p")
        root.attrib['x'] = str(self.X)
        root.attrib['y'] = str(self.Y)
        root.attrib['t'] = str(self.T)

        return root
 

    def distance(self, point2):
         "Returns the distance from this point to the point in argument 1"
         from Utils import GeomUtils
         return GeomUtils.pointDist(self, point2)

    def copy(self):
        return Point(self.X, self.Y, self.T)

    def __repr__(self):
        return "P(%s,%s)" % (self.X, self.Y)

    def __eq__(self, other):
        if other is not None \
            and math.fabs(self.X - other.X) < 0.0001 \
            and math.fabs(self.Y - other.Y) < 0.0001:
                return  True
        return False
    def __ne__(self, other):
        if not (self == other):
            return True
        return False

    def __str__(self):
        return "(" + ("%.1f" % self.X) + "," + ("%.1f" % self.Y) + ")"
        #return "(" + str(self.X) + "," + str(self.Y) + ")"
        #return "(" + str(self.X) + "," + str(self.Y) + "," + str(self.T) + ")"

    #getitem and setitem so implement index interface
    # e.g.: Point(2,4)[0] == 2
    def __getitem__(self, key):
        if key == 0:
            return self.X
        elif key == 1:
            return self.Y
        else:
            raise IndexError
    def __setitem__(self, key, value):
        if key == 0:
            self.X = value
        elif key == 1:
            self.Y = value
        else:
            raise IndexError
