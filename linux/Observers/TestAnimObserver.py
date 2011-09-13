
import time
import math
import sys
import pdb
from SketchFramework import SketchGUI

from Utils import Logger
from Utils import GeomUtils
from SketchFramework.Point import Point
from SketchFramework.Stroke import Stroke
from SketchFramework.Board import BoardObserver, BoardSingleton
from SketchFramework.Annotation import Annotation, AnimateAnnotation
from Observers import ObserverBase


logger = Logger.getLogger('TestObserver', Logger.DEBUG)

#-------------------------------------

class TestAnnotation(AnimateAnnotation):
    def __init__(self):
        Annotation.__init__(self)
        self.dt = 0
        self.pattern = [1,1,1,1,1,0,0,0,0,0,2,0,0,0,0,0]
        self.idx = 0

    def step(self,dt):
        "Test animator, tracks the time since this was last called"
        self.idx = (self.idx + 1) % len(self.pattern)
        self.dt += dt

#-------------------------------------

class TestMarker( BoardObserver ):
    def __init__(self):
        BoardSingleton().RegisterForStroke( self )
    def onStrokeAdded(self, stroke):
        BoardSingleton().AnnotateStrokes([stroke], TestAnnotation())
    def onStrokeRemoved(self, stroke):
        for anno in stroke.findAnnotations(TestAnnotation):
            BoardSingleton().RemoveAnnotation(anno)

class TestAnimator( ObserverBase.Animator):
    def __init__(self, fps = 1):
        ObserverBase.Animator.__init__(self, anno_type = TestAnnotation, fps=fps)
        self.colors = ["#FFFF00", "#00FFFF", "#FF00FF"]
        self.lastDraw = time.time()
        self.trackedAnno = None

    def drawAnno(self, anno):
        #pdb.set_trace()
        if self.trackedAnno == None:
            self.trackedAnno = anno
        for stk in anno.Strokes:
            prevPt = None
            for i, point in enumerate(GeomUtils.strokeNormalizeSpacing(stk, numpoints = len(stk.Points)).Points):
                if prevPt != None:
                    color = self.colors[anno.pattern[ (i + anno.idx) % len(anno.pattern) ] ]
                    SketchGUI.drawLine(prevPt.X, prevPt.Y, point.X, point.Y, color=color, width = 3)
                prevPt = point
        if anno == self.trackedAnno:
            dt = time.time() - self.lastDraw
            self.lastDraw = time.time()
            logger.debug("Effective FPS = %s" % (1 / float(dt)))
                

