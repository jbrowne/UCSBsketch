import pdb
import math
from Utils import Logger
from Utils.GeomUtils import ellipseAxisRatio

from SketchFramework.Point import Point
from SketchFramework.Stroke import Stroke
from SketchFramework.Board import BoardObserver
from SketchFramework.Annotation import Annotation, AnnotatableObject

from Observers import ArrowObserver
from Observers import ObserverBase

from xml.etree import ElementTree as ET


logger = Logger.getLogger('ChartObserver', Logger.DEBUG)

#-------------------------------------
class ChartAreaAnnotation(Annotation):
    def __init__(self, horizArrow, vertArrow):
        Annotation.__init__(self)
        self.horizontalArrow = horizArrow
        self.verticalArrow = vertArrow

    def __repr__(self):
        return "CA: H {}, V {}".format(self.horizontalArrow, self.verticalArrow)

#-------------------------------------

class ChartAreaCollector( ObserverBase.Collector ):

    def __init__( self, board ):
        # this will register everything with the board, and we will get the proper notifications
        ObserverBase.Collector.__init__( self, board, \
            [ArrowObserver.ArrowAnnotation], ChartAreaAnnotation )

    def collectionFromItem( self, strokes, anno ):
        vertDiff = math.fabs(anno.tip.Y - anno.tail.Y)
        horizDiff = math.fabs(anno.tip.X - anno.tail.X)
        straightness = ellipseAxisRatio(anno.tailstroke)
        logger.debug("Straightness: {}".format(straightness))
        if straightness >= 0.93:
            if horizDiff > vertDiff:
                logger.debug("Horizontal Axis found")
                return ChartAreaAnnotation(anno, None)
            else:
                logger.debug("Vertical Axis found")
                return ChartAreaAnnotation(None, anno)
            

    def mergeCollections( self, from_anno, to_anno ):
        horizontalArrowList = [anno.horizontalArrow for anno in (from_anno, to_anno)
                                if anno.horizontalArrow is not None]
        verticalArrowList = [anno.verticalArrow for anno in (from_anno, to_anno)
                                if anno.verticalArrow is not None]
        print horizontalArrowList
        print verticalArrowList
        if len(verticalArrowList) != 1 or len(horizontalArrowList) != 1:
            logger.debug("Not merging charts")
            return False
        else:
            logger.debug("Merging charts")
            horiz = horizontalArrowList[0]
            vert = verticalArrowList[0]
            h_len = pointDist(horiz.tail, horiz.tip)
            v_len = pointDist(vert.tail, vert.tip)
            separation = pointDist(horiz.tail, vert.tail)
            if separation > max(h_len, v_len) / 2.0:
                logger.debug("Axes too far apart")
                return False
            to_anno.verticalArrow = vert
            to_anno.horizontalArrow = horiz
            logger.debug(to_anno)
            return True
            
#-------------------------------------

class ChartVisualizer( ObserverBase.Visualizer ):
    "Watches for DiGraph annotations, draws them"
    def __init__(self, board):
        ObserverBase.Visualizer.__init__( self, board, ChartAreaAnnotation )

    def drawAnno( self, a ):
        for arrow in [a.horizontalArrow, a.verticalArrow]:
            if arrow is not None:
                x1 = arrow.tail.X
                y1 = arrow.tail.Y
                x2 = arrow.tip.X
                y2 = arrow.tip.Y
                self.getGUI().drawLine(x1,y1,x2,y2, color="#A0A000")



#-------------------------------------
# if executed by itself, run all the doc tests

if __name__ == "__main__":
    Logger.setDoctest(logger) 
    import doctest
    doctest.testmod()
