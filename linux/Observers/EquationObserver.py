from Observers import ObserverBase
from Queue import Empty
from Queue import Queue
from SketchFramework.Annotation import Annotation
from SketchFramework.Board import BoardObserver
from SketchFramework.Point import Point
from Utils import GeomUtils
from Utils import Logger
from Utils.GeomUtils import strokelistBoundingBox
from Utils.MyScriptUtils import flipStrokes
from Utils.MyScriptUtils.Equations import recognizeEquation
from threading import Lock
import gtk
import os
import pdb
import shutil
import subprocess
import tempfile
import threading
import time


logger = Logger.getLogger('EquationObserver', Logger.DEBUG)

#-------------------------------------
class EquationAnnotation(Annotation):
    @staticmethod
    def fromMyScriptResponse(mscResponse):
        """Generate an equation annotation from a myscript response"""
        if len(mscResponse.result.results) > 0 and mscResponse.result.results[0].type == 'LATEX':
            latex = mscResponse.result.results[0].value
        else:
            latex = ""
        return EquationAnnotation(latex)

    def __init__(self, latex):
        Annotation.__init__(self)
#        logger.debug("Annotating as %s" % (latex))
        self.latex = latex

    def setEqual(self, rhsanno):
        self.latex = rhsanno.latex

    def __repr__(self):
        return u'Eqn: "{}"'.format(self.latex)

#-------------------------------------
class DeferredEquationRecognizer(threading.Thread):
    """A thread that pools equation recognition requests.
    Interface is through DER.annoQueue, which accepts
    EquationAnnotation objects (already added to the board)."""
    def __init__(self, annoQueue, board):
        threading.Thread.__init__(self)
        self.daemon = True
        self.annoQueue = annoQueue
        self.board = board

    def run(self):
        """Wait indefinitely for the first anno added to the queue.
        Then wait at least _delay_, then process the rest of the 
        queued annotations."""
        delay = 0.5  # seconds
        while True:
            updateSet = set([])
            annotation = self.annoQueue.get(True)
            self.annoQueue.task_done()
            updateSet.add(annotation)
            time.sleep(delay)
            try:
                while True:
                    annotation = self.annoQueue.get_nowait()
                    self.annoQueue.task_done()
                    updateSet.add(annotation)
            except Empty:
                pass
            for annotation in updateSet:
                if len(annotation.Strokes) > 0:
                    mscResponse = recognizeEquation(flipStrokes(annotation.Strokes))
                    eqnAnno = EquationAnnotation.fromMyScriptResponse(mscResponse)
                    annotation.setEqual(eqnAnno)
                    with self.board.Lock:
                        self.board.UpdateAnnotation(annotation, annotation.Strokes)


class EquationMarker(BoardObserver):
    """Used to tag a individual strokes as equations"""
    def __init__(self, board, deferredAnnoQueue):
        BoardObserver.__init__(self, board)
        self.getBoard().AddBoardObserver(self, [EquationAnnotation])
        self.getBoard().RegisterForStroke(self)
        self.deferredAnnoQueue = deferredAnnoQueue

    def onStrokeAdded(self, stroke):
        if stroke.length() < 6:
            return
        # Annotate a null equation annotation for deferred recognition
        eqnAnno = EquationAnnotation("")
        with self.getBoard().Lock:
            self.getBoard().AnnotateStrokes([stroke], eqnAnno)
        self.deferredAnnoQueue.put(eqnAnno)  # Mark it for deferred recognition


    def onStrokeRemoved(self, stroke):
        "When a stroke is removed, remove equation annotation if found"
        for anno in stroke.findAnnotations(EquationAnnotation, True):
            logger.debug("Removing stroke from %s" % (anno.latex))
            annoStrokes = list(anno.Strokes)
            annoStrokes.remove(stroke)
            self.getBoard().UpdateAnnotation(anno, annoStrokes)
            self.deferredAnnoQueue.put(anno)


#-------------------------------------

class EquationCollector (ObserverBase.Collector):
    def __init__(self, board):
        # this will register everything with the board, and we will get the proper notifications
        ObserverBase.Collector.__init__(self, board, \
            [], EquationAnnotation)
        # Initialize the equation marker
        observers = board.GetBoardObservers()

        self.annoQueue = Queue()
        self.deferredRecognizer = DeferredEquationRecognizer(self.annoQueue, board)
        self.deferredRecognizer.start()

        if EquationMarker not in [type(obs) for obs in observers]:
            logger.debug("Registering Equation Marker")
            EquationMarker(self.getBoard(), self.annoQueue)


    def onAnnotationUpdated(self, annotation):
        if isinstance(annotation, EquationAnnotation):
            self.getGUI().boardChanged()

    def mergeCollections(self, from_anno, to_anno):
        "merge from_anno into to_anno if they are naer enough to each other"
        minScale = 30
        vertOverlapRatio = 0
        horizOverlapRatio = 0
        groupingDistScale = 0.4  # multiplier for the median scale of how far to check around
                                # The strokes
        def annoScale(anno):
            """Helper function to get the scale of this annotation"""
            heights = [s.BoundTopLeft.Y - s.BoundBottomRight.Y for s in anno.Strokes]
#            scale = max(minScale, heights[len(heights)/2]) # median
            scale = sum(heights) / float(max(1, len(heights)))
            return max(scale, minScale)

        #  bb[0]-------+
        #   |          |
        #   |          |
        #   |          |
        #   +--------bb[1]
        # (0,0)

        from_scale = annoScale(from_anno)
        bb_from = GeomUtils.strokelistBoundingBox(from_anno.Strokes)
        tl = Point (bb_from[0].X - from_scale, bb_from[0].Y + from_scale * groupingDistScale)
        br = Point (bb_from[1].X + from_scale, bb_from[1].Y - from_scale * groupingDistScale)
        bb_from = (tl, br)

        to_scale = annoScale(to_anno)
        bb_to = GeomUtils.strokelistBoundingBox(to_anno.Strokes)
        tl = Point (bb_to[0].X - to_scale, bb_to[0].Y + to_scale * groupingDistScale)
        br = Point (bb_to[1].X + to_scale, bb_to[1].Y - to_scale * groupingDistScale)
        bb_to = (tl, br)
        # check x's overlap
        if   bb_from[1].X - bb_to[0].X < horizOverlapRatio \
          or bb_to[1].X - bb_from[0].X < horizOverlapRatio :
            logger.debug("Not merging %s and %s: horizontal overlap too small" % (from_anno, to_anno))
            return False

        # check y's overlap
        if   bb_from[0].Y - bb_to[1].Y < vertOverlapRatio \
          or bb_to[0].Y - bb_from[1].Y < vertOverlapRatio :
            logger.debug("Not merging %s and %s: vertical overlap too small" % (from_anno, to_anno))
            return False

        self.annoQueue.put(to_anno)
        return True

def pixbufFromLatex(latex):
    """Generate a png image from LaTex markup. The image
    is returned as a gtk.gdk.pixbuf, as well as stored in
    pngFileName"""
    logger.debug("Generating Latex {}".format(latex))
    tempDir = tempfile.mkdtemp(prefix="Sketch_")
    pngFileName = os.path.join(tempDir, "equationOutput.png")
    tex2imPath = os.path.abspath("./Utils/tex2im.sh")
    args = ['-f', 'png', '-b', 'black', '-t', 'Dandelion', '-o', pngFileName]
    cmd = [tex2imPath] + args + [latex]
    subprocess.call(cmd)
    pixbuf = gtk.gdk.pixbuf_new_from_file(pngFileName)  # pixbuf
    shutil.rmtree(tempDir)
    return pixbuf



#-------------------------------------

visLogger = Logger.getLogger("EquationVisualizer", Logger.DEBUG)
class EquationVisualizer(ObserverBase.Visualizer):
    "Watches for DiGraph annotations, draws them"
    def __init__(self, board):
        ObserverBase.Visualizer.__init__(self, board, EquationAnnotation)
        self._cachedPixbuf = {}  # 'latexString' : pixbuf

    def drawAnno(self, a):
        bbox = GeomUtils.strokelistBoundingBox(a.Strokes)
        gui = self.getBoard().getGUI()
        drawBox = False
        if drawBox:  # Draw the logical box
            minScale = 20
            heights = [s.BoundTopLeft.Y - s.BoundBottomRight.Y for s in a.Strokes]
            bb_from = GeomUtils.strokelistBoundingBox(a.Strokes)
            from_scale = max(minScale, heights[len(heights) / 2])
#            from_scale = max(minScale, sum(heights)/float(len(heights)))
            tl = Point (bb_from[0].X - from_scale, bb_from[0].Y + from_scale / 2)
            br = Point (bb_from[1].X + from_scale, bb_from[1].Y - from_scale / 2)
            bb_from = (tl, br)
            gui.drawBox(tl, br, color="#FFFFFF")

        visLogger.debug("Drawing Anno: {}".format(a.latex))
        if a.latex and len(a.latex) > 0:
            try:
                if hasattr(gui, 'drawBitmap'):
                    if a.latex not in self._cachedPixbuf:
                        self._cachedPixbuf[a.latex] = pixbufFromLatex(a.latex)

                    pixbuf = self._cachedPixbuf[a.latex]
                    gui.drawBitmap(bbox[1].X, bbox[1].Y, pixbuf=pixbuf)
                else:
                    gui.drawText(bbox[1].X, bbox[1].Y, a.latex)
            except Exception as e:
                visLogger.warn("Cannot draw equation {}: {}".format(a.latex, e))
