
from Utils import Logger
from Utils import GeomUtils

from SketchFramework import SketchGUI
from SketchFramework.Point import Point
from SketchFramework.Stroke import Stroke
from SketchFramework.Board import BoardObserver, BoardSingleton
from SketchFramework.Annotation import Annotation, AnnotatableObject

from Observers import DiGraphObserver
from Observers import TextObserver
from Observers import ObserverBase



tm_logger = Logger.getLogger('TuringCollector', Logger.DEBUG )

#-------------------------------------

class TuringMachineAnnotation(Annotation):
    def __init__(self, state_graph_anno = None, edge_labels = set([])):
        Annotation.__init__(self)
        tm_logger.debug("Creating new turing machine")

        #A DiGraphAnnotation that keeps track of all of the edges and nodes and their connections
        self.state_graph_anno = state_graph_anno
        #A dictionary mapping edges to their labels. 
        self.edge2labels_map = {}
        self.labels2edge_map = {}
        for l in edge_labels:
            self._assocLabelEdge(l, None)

        #Which state we are currently in
        self.active_state = None
        #Where on the tape we are currently residing
        self.tape_idx = ""
        #What is currently on the tape
        self.tape_string = ""

    def _assocLabelEdge(self, label, edge):
        self.edge2labels_map.setdefault(edge, set([])).add(label)
        self.labels2edge_map.setdefault(label, set([])).add(edge)
        
    def getAssociatedStrokes(self):
        "Returns a set of all the strokes that this annotation is actively tracking"
        strokeSet = set([])
        strokeSet.update(self.state_graph_anno.Strokes)
        for l in self.labels2edge_map.keys():
            strokeSet.update(l.Strokes)
        return strokeSet


#-------------------------------------
class TuringMachineCollector(BoardObserver):
    def __init__( self ):
        # this will register everything with the board, and we will get the proper notifications
        BoardSingleton().RegisterForAnnotation(TextObserver.TextAnnotation, self)
        BoardSingleton().RegisterForAnnotation(DiGraphObserver.DiGraphAnnotation, self)

    def onAnnotationAdded(self, strokes, anno):
        if anno.isType( TextObserver.TextAnnotation ):
            tm_logger.debug("Found text")
            tmAnno = TuringMachineAnnotation(edge_labels = [anno])
            BoardSingleton().AnnotateStrokes(strokes, tmAnno)

        elif anno.isType( DiGraphObserver.DiGraphAnnotation ):
            tm_logger.debug("Found a graph")
            tmAnno = TuringMachineAnnotation(state_graph_anno = anno)
            BoardSingleton().AnnotateStrokes(strokes, tmAnno)

    def onAnnotationRemoved(self, anno):
        return
        #          DISABLED

        shouldUpdate = False
        tm_annos = set([])
        for s in anno.Strokes:
            tm_annos.update(s.findAnnotations(TuringMachineAnnotation))
        if anno.isType( TextObserver.TextAnnotation ):
            for a in tm_annos:
                for edge, labelAnnoSet in anno.edge_labels.items():
                    if anno in labelAnnoSet:
                        labelAnnoSet.remove(anno)
                        shouldUpdate = True
        if anno.isType( DiGraphObserver.DiGraphAnnotation ):
            for a in tm_annos:
                if anno == a.state_graph_anno:
                    a.state_graph_anno = None
                    shouldUpdate = True
        #Update the annotation to keep things consistent
        #Return

#-------------------------------------
