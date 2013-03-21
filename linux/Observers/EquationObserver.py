from Observers import ObserverBase
from SketchFramework.Annotation import Annotation
from SketchFramework.Board import BoardObserver
from SketchFramework.Point import Point
from Utils import GeomUtils
from Utils import Logger
from Utils.GeomUtils import strokelistBoundingBox
from Utils.MyScriptUtils import flipStrokes
from Utils.MyScriptUtils.Equations import recognizeEquation
from threading import Lock
import os
import pdb
import shutil
import subprocess
import tempfile
import threading


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
        #Reminder, CircleAnno has fields:
        #   center
        Annotation.__init__(self)
        logger.debug("Annotating as %s" % (latex))
        self.latex = latex
        
    def setEqual(self, rhsanno):
        self.latex = rhsanno.latex
        
    def __repr__(self):
        return u'Eqn: "{}"'.format(self.latex)

#-------------------------------------

class EquationMarker( BoardObserver ):
    def __init__(self, board):
        BoardObserver.__init__(self, board)
        self.getBoard().AddBoardObserver(self, [EquationAnnotation])
        self.getBoard().RegisterForStroke( self )

    def onStrokeAdded( self, stroke ):
        if stroke.length()<6:
            return
        
        def getAndAddEquation():
            """Helper function to query MyScript and tag the annotation"""
            mscResponse = recognizeEquation(flipStrokes([stroke]))
            eqnAnno = EquationAnnotation.fromMyScriptResponse(mscResponse)
            if eqnAnno is not None:
                with self.getBoard().Lock:
                    self.getBoard().AnnotateStrokes([stroke], eqnAnno)
                    self.getGUI().boardChanged()
        t = threading.Thread(target=getAndAddEquation)
        t.daemon = True
        t.start()
#        getAndAddEquation()
        


    def onStrokeRemoved(self, stroke):
        "When a stroke is removed, remove equation annotation if found"
        for anno in stroke.findAnnotations(EquationAnnotation, True):
            logger.debug("Removing stroke from %s" % (anno.latex))
            annoStrokes = list(anno.Strokes)
            annoStrokes.remove(stroke)
            def updateAnno():
                if len(annoStrokes) == 0:
                    with self.getBoard().Lock:
                        self.getBoard().RemoveAnnotation(anno)
                else:
                    mscResponse = recognizeEquation(flipStrokes(annoStrokes))
                    eqnAnno = EquationAnnotation.fromMyScriptResponse(mscResponse)
                    if eqnAnno is not None:
                        logger.debug("Updating Equation" % (eqnAnno))
                        with self.getBoard().Lock:
                            anno.setEqual(eqnAnno)
                            self.getBoard().UpdateAnnotation(anno, annoStrokes)
                self.getGUI().boardChanged()

            t = threading.Thread(target=updateAnno)
            t.daemon = True
            t.start()
#-------------------------------------

class EquationCollector ( ObserverBase.Collector ):
    def __init__( self, board ):
        # this will register everything with the board, and we will get the proper notifications
        ObserverBase.Collector.__init__( self, board, \
            [], EquationAnnotation )
        #Initialize the equation marker
        observers = board.GetBoardObservers()
        if EquationMarker not in [type(obs) for obs in observers]:
            logger.debug("Registering Equation Marker")
            EquationMarker(self.getBoard())
        
    def mergeCollections( self, from_anno, to_anno ):
        "merge from_anno into to_anno if they point to each other"
        vertOverlapRatio = 0
        horizOverlapRatio = 0
        minScale = 20
        #  bb[0]-------+
        #   |          |
        #   |          |
        #   | (0,0)    |
        #   +--------bb[1]
        bb_from = GeomUtils.strokelistBoundingBox( from_anno.Strokes )
        center_from = Point( (bb_from[0].X + bb_from[1].X) / 2.0, (bb_from[0].Y + bb_from[1].Y) / 2.0)
        from_scale = max(minScale, bb_from[0].Y - bb_from[1].Y)
        tl = Point (bb_from[0].X - from_scale, center_from.Y + from_scale / 1.3  )
        br = Point (bb_from[1].X + from_scale, center_from.Y - from_scale / 1.3  )
        bb_from = (tl, br)

        bb_to = GeomUtils.strokelistBoundingBox( to_anno.Strokes )
        center_to = Point( (bb_to[0].X + bb_to[1].X) / 2.0, (bb_to[0].Y + bb_to[1].Y) / 2.0)
        to_scale = max(minScale, bb_to[0].Y - bb_to[1].Y) 
        tl = Point (bb_to[0].X - to_scale, center_to.Y + to_scale / 1.3  )
        br = Point (bb_to[1].X + to_scale, center_to.Y - to_scale / 1.3  )
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
        
        allStrokes = list(set(from_anno.Strokes + to_anno.Strokes))
        flippedStks = flipStrokes(allStrokes)
        mscResponse = recognizeEquation(flippedStks)
        eqAnno = EquationAnnotation.fromMyScriptResponse(mscResponse)
        to_anno.setEqual(eqAnno)
        return True

def pngFromLatex(latex, pngFileName):
    tex2imPath = os.path.abspath("./Utils/tex2im.sh")
    args = ['-f', 'png', '-b', 'black', '-t', 'red', '-o', pngFileName]
    cmd = [tex2imPath] + args + [latex]
    subprocess.call(cmd)
    
##-------------------------------------

visLogger = Logger.getLogger("EquationVisualizer", Logger.DEBUG)
class EquationVisualizer( ObserverBase.Visualizer ):
    "Watches for DiGraph annotations, draws them"
    def __init__(self, board):
        ObserverBase.Visualizer.__init__( self, board, EquationAnnotation)
        self.lock = Lock()
        
    def drawAnno( self, a ):
        bbox = GeomUtils.strokelistBoundingBox(a.Strokes)
        gui = self.getBoard().getGUI()
        visLogger.debug("Drawing Anno: {}".format(a.latex))
        if hasattr(gui, 'drawBitmap'):
            with self.lock:
                tempDir = tempfile.mkdtemp(prefix="Sketch_")
            pngFileName = os.path.join(tempDir, "equationOutput.png")
            pngFromLatex(a.latex, pngFileName)
            gui.drawBitmap(bbox[1].X, bbox[1].Y, pngFileName)
            shutil.rmtree(tempDir)
        else:
            gui.drawText(bbox[1].X, bbox[1].Y, a.latex)
            

#        minScale = 20
#        bb_from = GeomUtils.strokelistBoundingBox( a.Strokes )
#        center_from = Point( (bb_from[0].X + bb_from[1].X) / 2.0, (bb_from[0].Y + bb_from[1].Y) / 2.0)
#        from_scale = max(minScale, bb_from[0].Y - bb_from[1].Y)
#        tl = Point (bb_from[0].X - from_scale, center_from.Y + (from_scale / 1.3) )
#        br = Point (bb_from[1].X + from_scale, center_from.Y - (from_scale / 1.3) )
#        bb_from = (tl, br)
#        gui.drawBox(tl, br, color="#FFFFFF")
