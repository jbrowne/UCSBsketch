from Observers import ArrowObserver
from Observers import ObserverBase
from Observers.EquationObserver import EquationAnnotation
from Observers.EquationObserver import EquationVisualizer
from SketchFramework.Annotation import Annotation
from SketchFramework.Board import BoardObserver
from SketchFramework.Point import Point
from SketchFramework.Stroke import Stroke
from Utils import Logger
from Utils.GeomUtils import ellipseAxisRatio, pointDist
from Utils.LaTexCalculation import solveLaTex
from xml.etree import ElementTree as ET
import math
import pdb
from Utils.GeomUtils import strokelistBoundingBox





logger = Logger.getLogger('ChartObserver', Logger.DEBUG)

#-------------------------------------
class ChartAreaAnnotation(Annotation):
    def __init__(self, horizArrow, vertArrow):
        Annotation.__init__(self)
        self.horizontalArrow = horizArrow
        self.verticalArrow = vertArrow
        self.equations = []


    def __repr__(self):
        return "CA: H {}, V {}".format(self.horizontalArrow, self.verticalArrow)

#-------------------------------------

class ChartAreaCollector(ObserverBase.Collector):

    def __init__(self, board):
        """This will register everything with the board, and we will
        get the proper notifications"""
        ObserverBase.Collector.__init__(self, board, \
            [ArrowObserver.ArrowAnnotation], ChartAreaAnnotation)

    def collectionFromItem(self, strokes, anno):
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
    def mergeCollections(self, from_anno, to_anno):
        horizontalArrowList = [anno.horizontalArrow for anno in
                                            (from_anno, to_anno)
                                if anno.horizontalArrow is not None]
        verticalArrowList = [anno.verticalArrow for anno in
                                            (from_anno, to_anno)
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


class DummyEqnVisualizer(EquationVisualizer):
    """A class that can be called to draw annotations,
    but doesn't track anything itself"""
    def __init__(self, board):
        ObserverBase.Visualizer.__init__(self, board, None)
        self._cachedPixbuf = {}  # 'latexString' : pixbuf


class ChartVisualizer(ObserverBase.Visualizer):
    "Watches for DiGraph annotations, draws them"
    COLORS = ["#a000a0", "#00a0a0", "#a00000", "#00a000",
              "#0000a0"]
    def __init__(self, board):
        ObserverBase.Visualizer.__init__(self, board, ChartAreaAnnotation)
        self.equationVisualizer = DummyEqnVisualizer(board)
        self.getBoard().RegisterForAnnotation(EquationAnnotation, self)
        self.equations = set([])

    def onAnnotationAdded(self, strokes, annotation):
        if type(annotation) == EquationAnnotation:
            self.equations.add(annotation)
        else:
            ObserverBase.Visualizer.onAnnotationAdded(self, strokes, annotation)

    def onAnnotationRemoved(self, annotation):
        if type(annotation) == EquationAnnotation \
            and annotation in self.equations:
            self.equations.remove(annotation)
        else:
            ObserverBase.Visualizer.onAnnotationRemoved(self, annotation)

    def drawAnno(self, a):
        if a.horizontalArrow is None or a.verticalArrow is None:
            return
        x0, y0 = None, None  # offset coordinates
        slopeFn = lambda x: 0
        height = int(a.verticalArrow.tip.Y - a.verticalArrow.tail.Y)
        width = int(a.horizontalArrow.tip.X - a.horizontalArrow.tail.X)
        for arrow in [a.horizontalArrow, a.verticalArrow]:
            x1 = arrow.tail.X
            y1 = arrow.tail.Y
            x2 = arrow.tip.X
            y2 = arrow.tip.Y
            if x0 is None or x0 < x1:
                x0 = x1
            if y0 is None or y0 < y1:
                y0 = y1

        scales = []
        allGraphs = []
        for i, eqn in enumerate(self.equations):
            try:
                scale = 1
                eqnAnnos = self.getBoard().FindAnnotations(
                                               strokelist=eqn.Strokes,
                                               anno_type=ChartAreaAnnotation)
                isEquationAChart = len(eqnAnnos) > 0
                if isEquationAChart:
                    continue
                func = solveLaTex(eqn.latex)
                points = []
                for x in range(width):
                    try:
                        y = func(x)
                        scale = float(max(y, scale))
                    except:
                        y = None
                    points.append((x, y,))
                allGraphs.append((i, points,))
                self.equationVisualizer.drawAnno(eqn)
                bbox = strokelistBoundingBox(eqn.Strokes)
                color = ChartVisualizer.COLORS[i % len(ChartVisualizer.COLORS)]
                self.getGUI().drawLine(bbox[0].X, bbox[1].Y - 3,
                                       bbox[1].X, bbox[1].Y - 3,
                                       color=color)
                scales.append(scale)
            except Exception as e:
                logger.debug("Cannot draw equation '{}': {}".format(eqn.latex, e))
                continue

        drawScale = sum(scales) / float(max(1, len(scales)))
        for i, points in allGraphs:
            color = ChartVisualizer.COLORS[i % len(ChartVisualizer.COLORS)]
            px = py = None
            for x, y in points:
                if y is not None:
                    cx = x0 + x
                    cy = y0 + (y / drawScale * height)
                    if px is not None and py is not None:
                        if cy < y0 + height and py < y0 + height \
                            and cx < x0 + width and px < x0 + width:
                            self.getGUI().drawLine(px, py, cx, cy, color=color)
                    px = cx
                    py = cy
                else:
                    px = py = None

#-------------------------------------
# if executed by itself, run all the doc tests

if __name__ == "__main__":
    Logger.setDoctest(logger)
    import doctest
    doctest.testmod()
