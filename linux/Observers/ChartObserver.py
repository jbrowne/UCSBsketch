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

from SketchFramework.Point import Point
from SketchFramework.Stroke import Stroke
from SketchFramework.Board import BoardObserver
from SketchFramework.Annotation import Annotation, AnnotatableObject



logger = Logger.getLogger('ChartObserver', Logger.WARN)

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
class ChartEquationSplitter(BoardObserver):
    def __init__(self, board):
        BoardObserver.__init__(self, board)
        self.getBoard().AddBoardObserver(self, [ChartAreaAnnotation, EquationAnnotation])
        self.getBoard().RegisterForAnnotation(ChartAreaAnnotation, self)
        self.getBoard().RegisterForAnnotation(EquationAnnotation, self)

    def onAnnotationUpdated(self, anno):

        chartAnnotations = []
        equationAnnotations = []
        if type(anno) == ChartAreaAnnotation:
            chartAnnotations = [anno]
            for stk in anno.Strokes:
                equationAnnotations.extend(stk.findAnnotations(EquationAnnotation))
        elif type(anno) == EquationAnnotation:
            equationAnnotations = [anno]
            for stk in anno.Strokes:
                chartAnnotations.extend(stk.findAnnotations(ChartAreaAnnotation))
        for chartAnno in chartAnnotations:
            if None in (chartAnno.horizontalArrow, chartAnno.verticalArrow):
                continue
            for eqAnno in equationAnnotations:
                newStks = eqAnno.Strokes
                for stk in chartAnno.Strokes:
                    if stk in newStks:
                        newStks.remove(stk)
                logger.debug("Splitting chart annotation from '{}'".format(eqAnno.latex))
                self.getBoard().UpdateAnnotation(eqAnno, new_strokes = newStks)

class ChartAreaCollector(ObserverBase.Collector):

    def __init__(self, board):
        """This will register everything with the board, and we will
        get the proper notifications"""
        ObserverBase.Collector.__init__(self, board, \
            [ArrowObserver.ArrowAnnotation], ChartAreaAnnotation)
        ChartEquationSplitter(board)

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
        if len(verticalArrowList) != 1 or len(horizontalArrowList) != 1:
            logger.debug("Not merging charts")
            return False
        else:
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
            logger.debug("Merging charts")
            return True

#-------------------------------------


class DummyEqnVisualizer(EquationVisualizer):
    """A class that can be called to draw annotations,
    but doesn't track anything itself"""
    def __init__(self, board):
        ObserverBase.Visualizer.__init__(self, board, None)
        self._cachedPixbuf = {}  # 'latexString' : pixbuf


def mapChartsToEquations(chartsMap, equations):
    """Take in a chartMap and list of equations, and fill in the
    chartMap such that each chart maps to a list of its closest equations"""
    if len(chartsMap) == 0:
        return
    chartsBB = {}
    for chart_anno in chartsMap.keys():
        ch_bb = strokelistBoundingBox(chart_anno.Strokes)
        ch_point = Point( (ch_bb[0].X + ch_bb[1].X)/2.0, 
                          (ch_bb[0].Y + ch_bb[1].Y)/2.0)
        chartsBB[chart_anno] = ch_point
        chartsMap[chart_anno] = []

    for eq_anno in equations:
        eq_bb = strokelistBoundingBox(eq_anno.Strokes)
        eq_point = Point( (eq_bb[0].X + eq_bb[1].X)/2.0, 
                          (eq_bb[0].Y + eq_bb[1].Y)/2.0)
        chosenChart = None
        chosenDist = 1000
        for chart_anno, chart_point in chartsBB.items():
            if chart_anno.horizontalArrow is None or chart_anno.verticalArrow is None:
                continue
            thisDist = pointDist(chart_point, eq_point)
            if chosenChart is None or thisDist < chosenDist:
                chosenChart = chart_anno
                chosenDist = thisDist
        if chosenChart is not None:
            chartsMap[chosenChart].append(eq_anno)

class ChartVisualizer(ObserverBase.Visualizer):
    "Watches for DiGraph annotations, draws them"
    COLORS = ["#ff0000", "#00a000", "#0000FF","#ff00a0", "#a0a000", "#a000FF"] 
    def __init__(self, board):
        ObserverBase.Visualizer.__init__(self, board, ChartAreaAnnotation)
        self.equationVisualizer = DummyEqnVisualizer(board)
        self.getBoard().RegisterForAnnotation(EquationAnnotation, self)
        self.equations = set([])
        self.charts = {}

    def onAnnotationAdded(self, strokes, annotation):
        if type(annotation) == EquationAnnotation:
            self.equations.add(annotation)
        else:
            if type(annotation) == ChartAreaAnnotation:
                self.charts[annotation] = []
            ObserverBase.Visualizer.onAnnotationAdded(self, strokes, annotation)
        mapChartsToEquations(self.charts, self.equations)

    def onAnnotationRemoved(self, annotation):
        if type(annotation) == EquationAnnotation \
            and annotation in self.equations:
            self.equations.remove(annotation)
        else:
            if type(annotation) == ChartAreaAnnotation and annotation in self.charts:
                del(self.charts[annotation])
            ObserverBase.Visualizer.onAnnotationRemoved(self, annotation)
        mapChartsToEquations(self.charts, self.equations)

    def drawAnno(self, a):
        if a.horizontalArrow is None or a.verticalArrow is None:
            return
        xValRange = (0,10)
        x0, y0 = None, None  # offset coordinates
        rise = a.horizontalArrow.tip.Y - a.horizontalArrow.tail.Y 
        height = int(a.verticalArrow.tip.Y - a.verticalArrow.tail.Y)
        width = int(a.horizontalArrow.tip.X - a.horizontalArrow.tail.X)
        slopeFn = (lambda x: rise * (x / float(width)))
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
        for i, eqn in enumerate(self.charts[a]):
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
                    xVal = (x * (xValRange[1] - xValRange[0]) / float(width)) - xValRange[0]
                    try:
                        y = func(xVal)
                        scale = float(max([y, scale, -y]))
                    except:
                        y = None
                    points.append((x, y,))
                allGraphs.append((i, points,))
                self.equationVisualizer.drawAnno(eqn)
                bbox = strokelistBoundingBox(eqn.Strokes)
                color = ChartVisualizer.COLORS[i % len(ChartVisualizer.COLORS)]
                self.getGUI().drawLine(bbox[0].X, bbox[1].Y - 5,
                                       bbox[1].X, bbox[1].Y - 5,
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
                    y = (y / drawScale * height) + slopeFn(x)
                    cy = max(min(y0+height, y0 + y), y0-height)
                    if px is not None and py is not None:
                        if cy < y0 + height and py < y0 + height \
                            and cy > y0 - height and py > y0 - height \
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
