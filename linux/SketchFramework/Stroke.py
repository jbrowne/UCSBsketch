import sys
from Utils import Logger
from SketchFramework.Point import Point
from SketchFramework.Annotation import Annotation, AnnotatableObject
from xml.etree import ElementTree as ET

logger = Logger.getLogger('DiGraphObserver', Logger.WARN )


#FIXME: this module is in dire need of some documentation

class Stroke(AnnotatableObject):
    "Stroke defined as a List of Points: Points"

    # counter shared with all strokes, incremented on each new stroke
    Number = 0
    DefaultStrokeColor = "#000000"

    def __repr__(self):
        return "<Stroke %s>" % (str(self.id))
    
    def __init__(self, points=None, board=None):#, smoothing=False): DEPRECATED
        # call parent constructor
        AnnotatableObject.__init__(self) 
        # give each stroke a unique id
        self.id = Stroke.Number
        Stroke.Number += 1

        self.Points = []
        self.BoundTopLeft = Point( 0, 0 )
        self.BoundBottomRight = Point( 0, 0 )
        #Centerpoint of this stroke
        self.X = None
        self.Y = None
        self.Center = None
        self.Color = Stroke.DefaultStrokeColor

        self._length = -1
        self._resample = {}
        self.setBoard(board)# self._board = board

        if points and len(points)>0:
            # if passed a sequence of tuples, covert them all to points
            if all(type(i)==tuple for i in points):
                points = [ Point(x,y) for (x,y) in points ]
            # turning smoothing off is very handy for testing
            self.Points = points
            xlist = [p.X for p in points]
            ylist = [p.Y for p in points]
            ( left , right ) = min(xlist), max(xlist)
            ( bottom, top ) = min(ylist), max(ylist)
            self.BoundTopLeft = Point(left, top)
            self.BoundBottomRight = Point(right, bottom)

            self.X = (left + right) / 2
            self.Y = (top + bottom) / 2
            self.Center = Point(self.X, self.Y)

    def xml(self):
        root = ET.Element("Stroke")

        root.attrib['id'] = str(self.id)
        root.attrib['length'] = str(self.length())

        pts_el = ET.SubElement(root, "Points")
        for i, pt in enumerate(self.Points):
            pts_el.append(pt.xml())

        topleft = self.BoundTopLeft.xml()
        topleft.tag = "topleft"
        root.append(topleft)

        bottomright = self.BoundBottomRight.xml()
        bottomright.tag = "bottomright"
        root.append(bottomright)

        center = self.Center.xml()
        center.tag = "center"
        root.append(center)
        return root
 
    
    def drawMyself(self, color=None):

        if color: drawColor = color
        else: drawColor = self.Color 

        board = self.getBoard()
        if board is not None and board.getGUI() is not None and len(self.Points) > 0:
            board.getGUI().drawStroke(self, color=drawColor, erasable = True)
                            
    def length (self, force = False):
        if self._length == -1 or force:
            if len(self.Points) > 0:
                self._length = 0
                prev = self.Points[0]
                for next in self.Points:
                    #Sum up the pairwise distance between points
                    self._length += prev.distance(next)
                    prev = next
            else:
                self._length = 0

        return self._length

    def get_id(self):
	return self.id

    def setBoard(self, board):
        self._board = board
    def getBoard(self):
        return self._board

    def addPoint(self, x, y, t):
        self.addPoint( Point( x, y, t ) )
        
    def addPoint(self, point):
        self.Points.append( point )
        if self.X == None or self.Y == None:
           self.BoundTopLeft.X = self.BoundBottomRight.X = point.X
           self.BoundTopLeft.Y = self.BoundBottomRight.Y = point.Y

        if (point.X < self.BoundTopLeft.X):
            self.BoundTopLeft.X = point.X
        elif (point.X > self.BoundBottomRight.X):
            self.BoundBottomRight.X = point.X
            
        if (point.Y > self.BoundTopLeft.Y):
            self.BoundTopLeft.Y = point.Y
        elif (point.Y < self.BoundBottomRight.Y):
            self.BoundBottomRight.Y = point.Y

        self.X = (self.BoundTopLeft.X + self.BoundBottomRight.X) / 2
        self.Y = (self.BoundTopLeft.Y + self.BoundBottomRight.Y) / 2
        self.Center = Point(self.X, self.Y)

    def translate(self, xDist, yDist, overWrite = False):
        "Input: Stroke, and the distance in points to translate in X- and Y-directions. Returns a new translated stroke"
        if overWrite:
            for p in self.Points:
                p.X += xDist
                p.Y += yDist
            
            self.BoundTopLeft.X += xDist
            self.BoundTopLeft.Y += yDist
            self.BoundBottomRight.X += xDist
            self.BoundBottomRight.Y += yDist
            
            self.X = (self.BoundTopLeft.X + self.BoundBottomRight.X) / 2
            self.Y = (self.BoundTopLeft.Y + self.BoundBottomRight.Y) / 2
            self.Center = Point(self.X, self.Y)
            return self
        else:
            retStroke = Stroke()
            for p in self.Points:
                newPoint = Point(p.X + xDist, p.Y + yDist)
                retStroke.addPoint(newPoint)
            return retStroke
