import pdb
from Utils import Logger
from Utils import GeomUtils

from SketchFramework.Point import Point
from SketchFramework.Stroke import Stroke
from SketchFramework.Board import BoardObserver
from SketchFramework.Annotation import Annotation, AnnotatableObject

log = Logger.getLogger('Semantics_Class1', Logger.DEBUG)


    
class Class1Annotation( Annotation ):
    def __init__(self):
        self._keyPoints = {} #A list of points that have semantic meaning
                             # e.g. the tip of an arrowhead
        self._tags = {} #A dict of semantic tags. e.g. "text" : "ABCD"

    def setTag(self, key, value):
        """Set a textual tag."""
        self._tags[str(key)] = str(value)
    def getTag(self, key):
        return self._tags[str(key)]
    def removeTag(self, key):
        del(self._tags[str(key)])

    def getKeyPoint(self, key):
        return self._keyPoints[key]
    def addKeyPoint(self, key, point):
        self._keyPoints[key] = point
    def removeKeyPoint(self, key, point):
        del(self._keyPoints[key])
        
#-------------------------------------

class Class1Marker( BoardObserver ):
    def __init__(self, board):
        BoardObserver.__init__(self, board)
        self.getBoard().AddBoardObserver( self , [])
        self.getBoard().RegisterForStroke( self )
        
        self.strokeObservers = set() #A set of functions to classify raw strokes

    def registerStrokeClassifier(self, classifier):
        self.strokeObservers.add(classifier)
        log.debug("Registered %s" % (classifier.__name__))
        print self.strokeObservers

    def onStrokeAdded( self, stroke ):
        """Calls all classifier functions on the stroke"""
        print self.strokeObservers
        for so in self.strokeObservers:
            log.debug("New stroke: %s notified" % (so.__name__))
            anno = so(self.getBoard(), stroke)
            if anno is not None: #and is a class1 anno!
                self.getBoard().AnnotateStrokes([stroke], anno)

    def onStrokeRemoved(self, stroke):
        return

if __name__ == "__main__":

    pass
