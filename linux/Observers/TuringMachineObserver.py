
import pdb

from Utils import Logger
from Utils import GeomUtils
from Utils import Debugging as D

from SketchFramework import SketchGUI
from SketchFramework.Point import Point
from SketchFramework.Stroke import Stroke
from SketchFramework.Board import BoardObserver, BoardSingleton
from SketchFramework.Annotation import Annotation, AnnotatableObject

from Observers import DiGraphObserver
from Observers import TextObserver
from Observers import ObserverBase

from xml.etree import ElementTree as ET



tm_logger = Logger.getLogger('TuringCollector', Logger.DEBUG )

#-------------------------------------

class TuringMachineAnnotation(Annotation):
    def __init__(self, state_graph_anno = None, edge_labels = set([])):
        Annotation.__init__(self)
        tm_logger.debug("Creating new turing machine")


        #Which state we are currently in
        self.active_state = None
        #Where on the tape we are currently residing
        self.tape_idx = -1
        #What is currently on the tape
        self.tape_string = []
        #What edge brought us here
        self.leading_edge = {'edge': None, 'label' : None} #edge ArrowAnno, label TextAnno

        self.tape_text_anno = None
        self.tape_box = None

        #A dictionary mapping edges to their labels. 
        self.edge2labels_map = {}
        self.labels2edge_map = {}
        for l in edge_labels:
            self.assocLabel2Edge(l, None)

        #A DiGraphAnnotation that keeps track of all of the edges and nodes and their connections
        self.state_graph_anno = None
        self.setDiGraphAnno(state_graph_anno)

    def xml(self):
        root = Annotation.xml(self)

        mapEl = ET.SubElement(root, "edge_label_map")
            
        for e, labelset in self.edge2labels_map.items():
            #edgeEl = e.xml()
            #edgeEl.tag = "edge"
            #root.append(edgeEl)
            edgeEl = ET.SubElement(root, "edge")
            edgeEl.attrib['id'] = str(e.id)

            for  l in labelset:
                e_label = ET.SubElement(mapEl, "m")
                e_label.attrib['e'] = str(e.id)
                e_label.attrib['l'] = str(l.id)

        for l, edgeset in self.labels2edge_map.items():
            #labelEl = l.xml()
            #labelEl.tag = "label"
            #root.append(labelEl)
            labelEl = ET.SubElement(root, "label")
            labelEl.attrib['id'] = str(l.id)

        leadEdge = self.leading_edge['edge']
        if leadEdge is not None:
            eid = leadEdge.id
        else:
            eid = -1
        root.attrib['leading_edge'] = str(eid)

        #graphEl = self.state_graph_anno.xml()
        #graphEl.tag = "state_graph"
        #root.append(graphEl)
        graphEl = ET.SubElement(root, "state_graph")
        graphEl.attrib['id'] = str(self.state_graph_anno.id)

        return root

        
    def setTapeString(self, string):
        if type(string) == str:
            self.tape_string = list(string)
        else:
            self.tape_string = ""
        self.tape_idx = 0
        

    def setTapeTextAnno(self, anno):
        self.tape_text_anno = anno
        if self.tape_text_anno.isType(TextAnnotation):
            self.setTapeString(self.tape_text_anno.text)

    def setDiGraphAnno(self, dgAnno):
        self.state_graph_anno = dgAnno
        self.restartSimulation()

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

    def restartSimulation(self):
        self.active_state = None
        self.tape_idx = 0

        #Find the initial state
        initialEdges = self.state_graph_anno.connectMap.get(None, [])
        if len(initialEdges) == 0:
            tm_logger.warn("No initial state for the turing machine.")
            return
        elif len(initialEdges) > 1:
            tm_logger.warn("Multiple initial states for the turing machine, choosing random.")

        initEdge, initState = initialEdges[0]

        self.leading_edge = {'edge': initEdge,'label': None}
        self.active_state = initState
            
            
        

    def step(self, dt):
        self.simulateStep()

    def simulateStep(self):
        "Edge label: <read condition> <write character> <move direction 0L, 1R>"

        if self.tape_idx >= 0 and self.tape_idx < len(self.tape_string):
            cur_tape_val = self.tape_string[self.tape_idx]
        else:
            cur_tape_val = '-'

        out_edges = self.state_graph_anno.connectMap.get(self.active_state, [])
        next_state = None
        ops = []
        for edge, to_node in out_edges:
            for edge_label_anno in self.edge2labels_map.get(edge, []):
                edge_label = edge_label_anno.text
                if edge_label is not None and len(edge_label) == 3:
                    read_cond, write_back, move_dir = edge_label
                    bin_list = ['1', '0']
                    if read_cond == cur_tape_val \
                    and move_dir in bin_list \
                    and to_node != None:
                        ops.append( (read_cond, write_back, move_dir, to_node, edge, edge_label_anno) )

        if len(ops) > 1:
            tm_logger.warn("Multiple edges leading out of TM node can be taken: using %s" % (str(ops[0])))
        if len(ops) == 0:
            tm_logger.debug("No edges leading from node, moving to fail-state")
            self.active_state = None
            self.leading_edge = {'edge': None,'label': None}
            return
        else:
            read_cond, write_back, move_dir, next_state, along_edge, edge_label = ops[0]
            tm_logger.debug("Doing operation: read '%s', write '%s', move %s" % (read_cond, write_back, move_dir))

            if self.tape_idx < 0:
                self.tape_string.insert(0, write_back)
                self.tape_idx = 0
            elif self.tape_idx == len(self.tape_string):
                self.tape_string.insert(self.tape_idx, write_back)
            else:
                self.tape_string[self.tape_idx] = write_back
                    
            if move_dir == '0':
                self.tape_idx -= 1
            elif move_dir == '1':
                self.tape_idx += 1
            else:
                tm_logger.warn("Trying to move in non-left/right direction '%s'. Staying put." % (move_dir))
            self.leading_edge = {'edge': along_edge, 'label': edge_label}
            self.active_state = next_state

        
class BoxAnnotation (Annotation):
    def __init__(self, corners):
        Annotation.__init__(self)
        assert len(corners) == 4, "BoxAnnotation: Wrong number of corners in box annotation."
        self.corners = list(corners)

class BoxVisualizer (ObserverBase.Visualizer):
    def __init__(self):
        ObserverBase.Visualizer.__init__( self, BoxAnnotation)
    def drawAnno(self, a):
        prev = None
        for cPt in a.corners + [a.corners[0]]:
            if prev != None:
                SketchGUI.drawLine( prev.X, prev.Y, cPt.X, cPt.Y, width=4,color="#ccffcc")
            prev = cPt
        
class BoxMarker(BoardObserver):
    def __init__(self):
        BoardSingleton().RegisterForStroke(self)

    def onStrokeAdded(self, stroke):
        self.tagBox(stroke)

    def onStrokeRemoved(self, stroke):
        for ba in stroke.findAnnotations(BoxAnnotation):
            BoardSingleton().RemoveAnnotation(ba)

    def tagBox(self, stroke):

        endPointDistPct = 0.10 #How close (as % of length) the points have to be to each other
        boxApproxThresh = 50000 #The DTW distance between the stroke and how it best fits a box
        stkLen = GeomUtils.strokeLength(stroke)
        ep1, ep2 = stroke.Points[0], stroke.Points[-1]
        epDistSqr = GeomUtils.pointDistanceSquared(ep1.X, ep1.Y, ep2.X, ep2.Y)
        if  epDistSqr > (endPointDistPct * stkLen) ** 2:
            print "Endpoints aren't close enough to be a box"
            return
        overshoot = max(1, len(stroke.Points)/10)
        norm_stroke = GeomUtils.strokeSmooth(GeomUtils.strokeNormalizeSpacing(Stroke(stroke.Points + stroke.Points[0:overshoot]), numpoints = 70))
        #D.strokeCurvatureHistogram(norm_stroke)
        curvatures = GeomUtils.strokeGetPointsCurvature(norm_stroke)
        corners = set([])
        curvatures_cpy = list(curvatures)
        while len(corners) < 4:
            crnr_idx = curvatures_cpy.index(max(curvatures_cpy))
            crnr = curvatures_cpy[crnr_idx] * 57.295
            for nBor in range(crnr_idx -2, crnr_idx + 3):
                if nBor < len(curvatures_cpy) and nBor > 0:
                    curvatures_cpy[nBor] = 0
            if crnr > 0: #30 and crnr < 150:
                #Have a curvature, and we haven't already classified its immed neighbors as a corner
                corners.add(crnr_idx)
            else:
                break
        if len(corners) != 4:
            return
        else:
            c_list = [norm_stroke.Points[c_idx] for c_idx in sorted(list(corners))]
            cornerStroke = Stroke(c_list + c_list[:2])
            boxStroke = GeomUtils.strokeNormalizeSpacing(Stroke(c_list + [c_list[0]]))
            origStroke = GeomUtils.strokeNormalizeSpacing(Stroke(stroke.Points + [stroke.Points[0]]))
            approxAcc = GeomUtils.strokeDTWDist(boxStroke, origStroke)
            print "Box approximates original with %s accuracy" % (approxAcc)
            if approxAcc < boxApproxThresh:
                BoardSingleton().AnnotateStrokes([stroke], BoxAnnotation(c_list))

        

#-------------------------------------
class TuringMachineCollector(BoardObserver):
    LABELMATCH_DISTANCE = (0.5, 2.0)
    def __init__( self ):
        # this will register everything with the board, and we will get the proper notifications
        BoardSingleton().AddBoardObserver(self, [TuringMachineAnnotation])
        BoardSingleton().RegisterForAnnotation(TextObserver.TextAnnotation, self)
        BoardSingleton().RegisterForAnnotation(DiGraphObserver.DiGraphAnnotation, self)

        #BoxVisualizer()

        #BoxMarker()

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

        for textAnno in self.labelMap.keys():
            labelTL, labelBR = GeomUtils.strokelistBoundingBox(textAnno.Strokes)
            #Midpoint of the labe's bounding box
            labelCenterPt = Point ( (labelTL.X + labelBR.X) / 2.0, (labelTL.Y + labelBR.Y) / 2.0) 

            labelMatchDict = labelEdgeMatches.setdefault(textAnno, {}) 

            for graphAnno in self.graphMap:
                #Match edges to labels
                for edgeAnno in graphAnno.edge_set:
                    edgeLabelPoints = GeomUtils.strokeNormalizeSpacing(edgeAnno.tailstroke, 19).Points #Midpoint in the arrow-stroke
                    for elp in edgeLabelPoints:
                        dist = GeomUtils.pointDistanceSquared(elp.X, elp.Y, labelCenterPt.X, labelCenterPt.Y)
                        #labelMatchDict['allmatches'].append({'anno': edgeAnno, 'dist': dist})
                        if 'bestmatch' not in labelMatchDict or dist < labelMatchDict['bestmatch'][1]:
                            labelMatchDict['bestmatch'] = (edgeAnno, dist)

        #labelEdgeMatches contains each label paired with its best edge
        
        #Get the median size
        sizes = sorted([anno.scale for anno in self.labelMap.keys()])

        if len(sizes) > 0:
            medianSize = sizes[len(sizes) / 2]
        else:
            medianSize = 0

        #Have each edge claim a label
        edge2LabelMatching = {}
        for textAnno, matchDict in labelEdgeMatches.items():
            if 'bestmatch' in matchDict \
                and textAnno.scale < medianSize * TuringMachineCollector.LABELMATCH_DISTANCE[1] \
                and textAnno.scale > medianSize * TuringMachineCollector.LABELMATCH_DISTANCE[0]: # and matchDict['bestmatch'][1] < labelEdgeMatchingThresh:
                edgeLabelList = edge2LabelMatching.setdefault(matchDict['bestmatch'][0], [])
                edgeLabelList.append(textAnno)
            else:
                tm_logger.debug("TextAnno %s not matched to an edge" % (textAnno.text))

        #Make the associations and add the turing machine annotation
        for graphAnno, tmAnno in self.graphMap.items():
            assocSet = set([graphAnno])
            shouldAddAnno = False
            if tmAnno == None:
                shouldAddAnno = True
                tmAnno = TuringMachineAnnotation(state_graph_anno = graphAnno)

            for edgeAnno in graphAnno.edge_set:
                if edge2LabelMatching.get(edgeAnno, None) is not None:
                    assocLabelsList = edge2LabelMatching[edgeAnno]
                    for label in assocLabelsList:
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

class TuringMachineVisualizer ( ObserverBase.Visualizer ):
    "Watches for DiGraph annotations, draws them"
    def __init__(self, filename = "turing_machine.dot"):
        ObserverBase.Visualizer.__init__( self, TuringMachineAnnotation)

    def drawAnno( self, a ):
        tm_logger.debug(ET.tostring(a.xml()))

        edge_label_size = 15
        tape_label_size = 20
        active_color = "#BF5252"
        active_width = 7.0
        state_graph = a.state_graph_anno
        for from_node, connection_list in state_graph.connectMap.items():
            if from_node is not None:
                nodeColor = "#000000"
                if from_node == a.active_state:
                    nodeColor = active_color
                x, y = ( from_node.center.X, from_node.center.Y )
                SketchGUI.drawCircle (x, y, radius=from_node.radius, color=nodeColor, width=3.0)

            #GeomUtils.strokeSmooth(edge.tailstroke, width = len(edge.tailstroke.Points) / 3).drawMyself()
            for edge, to_node in connection_list:
                if edge == a.leading_edge['edge']:
                    edgeColor = active_color
                else:
                    edgeColor = "#000000"
                if to_node is not None:
                    nodeColor = "#000000"
                    nodeWidth = 3.0
                    if to_node == a.active_state:
                        nodeColor = active_color
                        nodeWidth = active_width
                    x, y = ( to_node.center.X, to_node.center.Y )
                    SketchGUI.drawCircle (x, y, radius=to_node.radius, color=nodeColor, fill="", width=nodeWidth)
                #Draw the smoothed tail
                if from_node is not None:
                    if edge.direction == "tail2head": #Connect the tail more closely to the edge
                        smooth_tail = Stroke([from_node.center] + edge.tailstroke.Points + [edge.tip])
                    else:
                        smooth_tail = Stroke([edge.tip] + edge.tailstroke.Points + [from_node.center])
                else:
                    smooth_tail = edge.tailstroke
                smooth_tail = GeomUtils.strokeSmooth(smooth_tail, width = len(edge.tailstroke.Points) / 3, preserveEnds = True)
                smooth_tail.drawMyself(color=edgeColor)

                #Draw the smoothed head
                ep1, ep2 = ( edge.headstroke.Points[0], edge.headstroke.Points[-1] )
                smooth_head = Stroke([ep1, edge.tip, ep2])
                smooth_head.drawMyself(color = edgeColor)

                if edge in a.edge2labels_map:
                    #Determine label offset
                     
                    for label in a.edge2labels_map[edge]:
                        textColor = "#000000"
                        if label == a.leading_edge['label']:
                            tm_logger.debug("Drawing leading label: %s" % (label.text))
                            textColor = active_color
                        tl, br = GeomUtils.strokelistBoundingBox(label.Strokes)

                        label_point = Point ((tl.X + br.X) / 2.0, (tl.Y + br.Y) / 2.0)
                        label_point.X -= edge_label_size
                        label_point.Y += edge_label_size
                        #label_point = smooth_tail.Points[len(smooth_tail.Points)/2]
                        SketchGUI.drawText (label_point.X, label_point.Y, InText=label.text, size=edge_label_size, color=textColor)
                    #endfor
                #endif
            #end for edge
        #end for from_node

        #Draw the tape string
        tl, br = GeomUtils.strokelistBoundingBox(a.Strokes)
        tape_label_pt = Point( \
            ((tl.X + br.X) / 2.0) - (len(a.tape_string) + 2) * tape_label_size / 2.0 , \
            br.Y - tape_label_size)

        for curIdx, tapeChar in enumerate(['-'] + a.tape_string + ['-']):
            curPt = Point(tape_label_pt.X + curIdx * tape_label_size, tape_label_pt.Y)
            charColor = "#000000"
            if curIdx - 1== a.tape_idx:
                charColor = active_color
            SketchGUI.drawText (curPt.X, curPt.Y, InText=tapeChar, size=tape_label_size, color=charColor)
            




            
"""
            
class TuringMachineAnimator(ObserverBase.Animator, TuringMachineVisualizer):
    def __init__(self, fps=1):
        ObserverBase.Animator.__init__(self,anno_type = TuringMachineAnnotation, fps = fps)
    def drawAnno(self, *args, **kargs):
        TuringMachineVisualizer.drawAnno(self, *args, **kargs)
        
"""
    


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

