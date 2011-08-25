
import pdb

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
            self.assocLabel2Edge(l, None)

        #Which state we are currently in
        self.active_state = None
        #Where on the tape we are currently residing
        self.tape_idx = ""
        #What is currently on the tape
        self.tape_string = ""

    def setDiGraphAnno(self, dgAnno):
        self.state_graph_anno = dgAnno

    def assocLabel2Edge(self, label, edge):
        tm_logger.debug("Associating label %s with edge of %s" % (label.text, self.state_graph_anno))
        assert edge == None or edge in self.state_graph_anno.edge_set
        self.edge2labels_map.setdefault(edge, set([])).add(label)
        self.labels2edge_map.setdefault(label, set([])).add(edge)
        
    def getAssociatedStrokes(self):
        "Returns a set of all the strokes that this annotation is actively tracking"
        strokeSet = set([])
        strokeSet.update(self.state_graph_anno.Strokes)
        for l in self.labels2edge_map.keys():
            strokeSet.update(l.Strokes)
        return strokeSet
    def dotify(self):
        "Returns a string of the turing machine in DOT format"
        nodelist = list(self.state_graph_anno.node_set)
        retstr = "digraph G {\n"
        def name(node, nodelist):
            if (node == None):
                return  "None" 
            else: 
                return str(nodelist.index(node))

        for node in self.state_graph_anno.node_set:
            retstr+= "%s\n" % (name(node, nodelist))

        for src, connlist in self.state_graph_anno.connectMap.items():
            srcname = name(src, nodelist)
            for edgeAnno , dest in connlist:
                destname = name(dest, nodelist)
                edgeLabelAnnoList = list(self.edge2labels_map.get(edgeAnno, []))
                edgeText = " "
                if len(edgeLabelAnnoList) > 0:
                    edgeText = edgeLabelAnnoList[0].text
                retstr += "%s -> %s [label=\"%s\"]\n" % (srcname, destname, edgeText)
        retstr+= "}"

        return retstr

        



#-------------------------------------
class TuringMachineCollector(BoardObserver):
    def __init__( self ):
        # this will register everything with the board, and we will get the proper notifications
        BoardSingleton().RegisterForAnnotation(TextObserver.TextAnnotation, self)
        BoardSingleton().RegisterForAnnotation(DiGraphObserver.DiGraphAnnotation, self)

        self.labelMap = {} #Maps textAnno to set of TMAnno
        self.graphMap = {} #Maps DGAnno to TMAnno
        self.tmMap = {} #Maps TMAnno to set of component DGAnno and TextAnno

    def onAnnotationUpdated(self, anno):
        if anno.isType( TextObserver.TextAnnotation ):
            labelAnno = anno
            if len(labelAnno.text) == 3: # 3-tuple text
                tm_logger.debug("Found text to track %s" % (labelAnno.text))
                tmGroups = self.labelMap.setdefault(labelAnno, set()) #All of the turing machines this label is a part of
                self.refreshTuringMachines()
            elif anno in self.labelMap: # Too many/few characters in label
                del(self.labelMap[anno])
                self.refreshTuringMachines()

        elif anno.isType( DiGraphObserver.DiGraphAnnotation ):
            graphAnno = anno
            if len(graphAnno.connectMap) >= 1:
                tm_logger.debug("Found a graph to track %s" % (graphAnno))
                self.graphMap.setdefault(graphAnno, None)
                self.refreshTuringMachines()
            elif graphAnno in self.graphMap:
                del(self.graphMap[graphAnno])
                self.refreshTuringMachines()
        
    def onAnnotationAdded(self, strokes, anno):
        self.onAnnotationUpdated(anno)

    def refreshTuringMachines(self):
        labelEdgeMatchingThresh = 2000 # how many times greater than the median we'll match edges

        labelEdgeMatches = {} # { label : {edge, distance} }

        for tmAnno in set(self.tmMap.keys()):
            BoardSingleton().RemoveAnnotation(tmAnno)
            del(self.tmMap[tmAnno])

        for graphAnno in self.graphMap:
            #Match edges to labels
            for edgeAnno in graphAnno.edge_set:
                edgeLabelPoint = edgeAnno.tailstroke.Points[len(edgeAnno.tailstroke.Points)/ 2] #Midpoint in the arrow-stroke

                for textAnno in self.labelMap:
                    labelTL, labelBR = GeomUtils.strokelistBoundingBox(textAnno.Strokes)
                    #Midpoint of the labe's bounding box
                    labelCenterPt = Point ( (labelTL.X + labelBR.X) / 2.0, (labelTL.Y + labelBR.Y) / 2.0) 

                    dist = GeomUtils.pointDistanceSquared(edgeLabelPoint.X, edgeLabelPoint.Y, labelCenterPt.X, labelCenterPt.Y)
                    labelMatchDict = labelEdgeMatches.setdefault(textAnno, {'bestmatch': (edgeAnno, dist), 'allmatches': []}) 
                    labelMatchDict['allmatches'].append({'anno': edgeAnno, 'dist': dist})
                    if dist < labelMatchDict['bestmatch'][1]:
                        labelMatchDict['bestmatch'] = (edgeAnno, dist)

        #labelEdgeMatches contains each label paired with its best edge
        
        #Have each edge claim a label
        edge2LabelMatching = {}
        procSet = set(labelEdgeMatches.keys())
        while len(procSet) > 0:
            labelAnno = procSet.pop()
            bestMatchEdge, bestMatchDist = labelEdgeMatches[labelAnno]['bestmatch']
            if bestMatchDist < labelEdgeMatchingThresh:
                edge2LabelMatching[bestMatchEdge] = (labelAnno, bestMatchDist)
            else:
                tm_logger.debug("Edge too far (%s) from best label %s" % (bestMatchDist, labelAnno.text))
                edge2LabelMatching[bestMatchEdge] = None

        #Make the associations and add the turing machine annotation
        for graphAnno, tmAnno in self.graphMap.items():
            assocSet = set([graphAnno])
            shouldAddAnno = False
            if tmAnno == None:
                shouldAddAnno = True
                tmAnno = TuringMachineAnnotation(state_graph_anno = graphAnno)

            for edgeAnno in graphAnno.edge_set:
                if edge2LabelMatching.get(edgeAnno, None) is not None:
                    label, dist = edge2LabelMatching[edgeAnno]
                    assocSet.add(label)
                    tmAnno.assocLabel2Edge(label, edgeAnno)
            if shouldAddAnno:
                BoardSingleton().AnnotateStrokes(tmAnno.getAssociatedStrokes(), tmAnno)
                self.tmMap[tmAnno] = assocSet
            else:
                BoardSingleton().UpdateAnnotation(tmAnno, new_strokes = tmAnno.getAssociatedStrokes())
                self.tmMap[tmAnno] = assocSet

    def onAnnotationRemoved(self, anno):
        newStrokes = set([])
        if anno in self.labelMap:
            del(self.labelMap[anno])
            self.refreshTuringMachines()
        if anno in self.graphMap:
            del(self.graphMap[anno])
            self.refreshTuringMachines()
        return

#-------------------------------------

class TuringMachineExporter ( ObserverBase.Visualizer ):
    "Watches for DiGraph annotations, draws them"
    def __init__(self, filename = "turing_machine.dot"):
        ObserverBase.Visualizer.__init__( self, TuringMachineAnnotation)
        self._fname = filename

    def drawAnno( self, a ):
        "Overridden to export a graph to a dot file"
        fd = open(self._fname, "a") 
        print >> fd, a.dotify()
        fd.close()

