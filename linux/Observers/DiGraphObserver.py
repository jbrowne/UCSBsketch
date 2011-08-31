"""
filename: DiGraphObserver.py

description:

Doctest Examples:

>>> d = DiGraphMarker()

-- one circle
>>> circle1points = [(int(math.sin(math.radians(x))*100+200),int(math.cos(math.radians(x))*100)+200) for x in range(0,360,20)]
>>> circle1_stroke = Stroke(circle1points)
>>> circle1_anno = CircleObserver.CircleAnnotation(100,Point(100,100),100)
>>> d.onAnnotationAdded( [circle1_stroke], circle1_anno )

-- two circles
>>> circle2points = [(int(math.sin(math.radians(x))*100+600),int(math.cos(math.radians(x))*100)+600) for x in range(0,360,20)]
>>> circle2_stroke = Stroke(circle2points)
>>> circle2_anno = CircleObserver.CircleAnnotation(100,Point(600,600),100)
>>> d.onAnnotationAdded( [circle2_stroke], circle2_anno )

-- now connect them with an arrow
>>> arrow_anno = ArrowObserver.ArrowAnnotation( Point(150,150), Point(600,600) )
>>> d.onAnnotationAdded( [circle1_stroke], arrow_anno )

"""

#-------------------------------------

import pdb
import math
from Utils import Logger
from Utils import GeomUtils

from SketchFramework import SketchGUI
from SketchFramework.Point import Point
from SketchFramework.Stroke import Stroke
from SketchFramework.Board import BoardObserver, BoardSingleton
from SketchFramework.Annotation import Annotation, AnnotatableObject

from Observers import CircleObserver
from Observers import ArrowObserver
from Observers import ObserverBase



logger = Logger.getLogger('DiGraphObserver', Logger.DEBUG )

#-------------------------------------

class DiGraphAnnotation(Annotation):
    MATCHING_DISTANCE = 2.0 # Multiplier for how far outside the circle radius to check
    def __init__(self, node_set=None, edge_set=None):
        Annotation.__init__(self)
        # DiGraph annotations maintain 3 things:
        # 1) a list of the nodes (which points to the circle_annos)
        # 2) a list of the edges (which points to the arrow_annos)
        # 3) a connectivity map (which is of the form { node_anno: [ (edge_anno, node_anno), (edge_anno, node_anno) ]}

        # set of circle annotations for nodes
        if node_set is None:
            self.node_set = set([])
        else:
            self.node_set = node_set

        # set of arrow annotations for edges
        if edge_set is None:
            self.edge_set = set([])
        else:
            self.edge_set = edge_set

        # set the map of connections
        self.connectMap = {}

    def updateConnectMap(self):
        "walk the set of edges and nodes, build a map of which nodes point to which edges and nodes"
        self.connectMap = {}
        def all_pair(x,y):
            for a in x:
                for b in y:
                    yield a,b
        for e in self.edge_set:
            tail_list = [ n for n in self.node_set if self.tailToNode(e,n) ]
            tip_list = [ n for n in self.node_set if self.tipToNode(e,n) ]
            # insert all tip_list -> tail_list for e
            if len(tail_list) == 0:
               tail_list.append(None)
            if len(tip_list) == 0:
               tip_list.append(None)
            for (tail_node,tip_node) in all_pair( tail_list, tip_list ):
                if tail_node not in self.connectMap:
                    self.connectMap[tail_node] = []
                self.connectMap[tail_node].append( (e,tip_node) )
        logger.debug("connectMap = %s", str(self.connectMap) )

    def tipToNode( self, arrow_anno, circle_anno ):
        "return true if the tip of the arrow points to the circle"
        lineDist = max(len(arrow_anno.tailstroke.Points) / 20, 1) #Check the last 10th of the stroke points the right way
        if arrow_anno.direction == "tail2head":
            lineSeg = ( arrow_anno.tailstroke.Points[-lineDist], arrow_anno.tip )
        else: #direction == 'head2tail'
            lineSeg = ( arrow_anno.tailstroke.Points[lineDist], arrow_anno.tip )
            
        if GeomUtils.pointDist( arrow_anno.tip,  circle_anno.center ) < circle_anno.radius* DiGraphAnnotation.MATCHING_DISTANCE:
            print "Arrow tip near circle"
            if GeomUtils.linePointsTowards( lineSeg[0], lineSeg[1], circle_anno.center, circle_anno.radius):
                print "Arrow points to circle"
                return True
        return False

    def tailToNode( self, arrow_anno, circle_anno ):
        "return true if the tail of the arrow comes from the circle"
        lineDist = max(len(arrow_anno.tailstroke.Points) / 10, 1) #Check the last 10th of the stroke points the right way
        if arrow_anno.direction == "tail2head":
            lineSeg = ( arrow_anno.tailstroke.Points[lineDist], arrow_anno.tailstroke.Points[0] )
        else: #direction == 'head2tail'
            lineSeg = ( arrow_anno.tailstroke.Points[-lineDist], arrow_anno.tailstroke.Points[-1] )
            
        if GeomUtils.pointDist( arrow_anno.tail,  circle_anno.center ) < circle_anno.radius* DiGraphAnnotation.MATCHING_DISTANCE:
            print "Arrow end near circle"
            if GeomUtils.linePointsTowards( lineSeg[0], lineSeg[1], circle_anno.center, circle_anno.radius):
                print "Arrow points from circle"
                return True
        return False

    def shouldConnect( self, arrow_anno, circle_anno ):
        "given an arrow and a circle anno, return true if arrow points from/to circle"
        for circle_stroke in circle_anno.Strokes:
            if circle_stroke in arrow_anno.Strokes:
                return False
        return self.tipToNode(arrow_anno, circle_anno) or self.tailToNode(arrow_anno, circle_anno)

    def __str__(self):
        listedSet = set(self.node_set)
        node_list = list(self.node_set)

        retstr = "{ "
        for node, connection_list in self.connectMap.items():
            if node == None:
                continue
            if node in listedSet:
                listedSet.remove(node)
            nodeName = str(node_list.index(node))
            for connection in connection_list:
                (edge, nbor) = connection
                if nbor in self.node_set:
                    nborName = str(node_list.index(nbor))
                else:
                    nborName = "None"
                if nbor in listedSet:
                    listedSet.remove(nbor)
                retstr += "%s->%s " % (nodeName, nborName)

        for node in listedSet:
            retstr += "-%s- " % (node_list.index(node))
        retstr += "}"

        return retstr

            
            
            
            


#-------------------------------------

class DiGraphMarker( ObserverBase.Collector ):

    def __init__( self ):
        # this will register everything with the board, and we will get the proper notifications
        ObserverBase.Collector.__init__( self, \
            [CircleObserver.CircleAnnotation, ArrowObserver.ArrowAnnotation], DiGraphAnnotation )

    def collectionFromItem( self, strokes, anno ):
        "turn the circle/arrow annotation given into a digraph"          
        if anno.isType( CircleObserver.CircleAnnotation ):
            digraph_anno = DiGraphAnnotation( node_set=set([anno]) )
        if anno.isType( ArrowObserver.ArrowAnnotation ):
            digraph_anno = DiGraphAnnotation( edge_set=set([anno]) )
        return digraph_anno

    def mergeCollections( self, from_anno, to_anno ):
        "merge from_anno into to_anno if they point to each other"
        # check all edges in one againt all nodes in the other
        merge = False
        for e in from_anno.edge_set:
            for n in to_anno.node_set:
                if to_anno.shouldConnect( e, n ):
                    merge = True
        #And reverse
        for e in to_anno.edge_set:
            for n in from_anno.node_set:
                if to_anno.shouldConnect( e, n ):
                    merge = True
        if merge:
            # add the nodes of "from" to "to"
            to_anno.node_set.update( from_anno.node_set )
            to_anno.edge_set.update( from_anno.edge_set )
            to_anno.updateConnectMap()
        return merge


#-------------------------------------

class DiGraphVisualizer( ObserverBase.Visualizer ):
    "Watches for DiGraph annotations, draws them"
    def __init__(self):
        ObserverBase.Visualizer.__init__( self, DiGraphAnnotation )

    def drawAnno( self, a ):
        if len(a.connectMap) > 0:
            node_map = {}
            for from_node in a.connectMap.keys():
                if from_node not in node_map:
                   node_map[from_node] = len(node_map)
                for connect_tuple in a.connectMap[from_node]:
                    edge,to_node = connect_tuple
                    if to_node not in node_map:
                       node_map[to_node] = len(node_map)

                    if from_node is not None:
                       SketchGUI.drawLine( edge.tail.X, edge.tail.Y, from_node.center.X, from_node.center.Y, width=2, color="#FA8072")
                    if to_node is not None:
                       SketchGUI.drawLine( edge.tip.X, edge.tip.Y, to_node.center.X, to_node.center.Y, width=2, color="#FA8072")

                    SketchGUI.drawCircle( edge.tail.X, edge.tail.Y, radius=2, width=2, color="#ccffcc")
                    SketchGUI.drawCircle( edge.tip.X, edge.tip.Y, radius=2, width=2, color="#ccffcc")

                    #x1,y1 = from_node.center.X, from_node.center.Y
                    #x2,y2 = edge.tail.X, edge.tail.Y
                    #SketchGUI.drawLine( x1,y1,x2,y2, width=2,color="#ccffcc")
                    #x1,y1 = to_node.center.X, to_node.center.Y
                    #x2,y2 = edge.tip.X, edge.tip.Y
                    #SketchGUI.drawLine( x1,y1,x2,y2, width=2,color="#ccffcc")

            for nodeAnno, nodeNum in node_map.items():
                if nodeAnno is not None:
                    x1,y1 = nodeAnno.center.X, nodeAnno.center.Y
                    SketchGUI.drawText(x1, y1, str(nodeNum))

#-------------------------------------

class DiGraphExporter ( ObserverBase.Visualizer ):
    "Watches for DiGraph annotations, draws them"
    def __init__(self, filename = "graph.dot"):
        ObserverBase.Visualizer.__init__( self, DiGraphAnnotation )
        self._fname = filename

    def drawAnno( self, a ):
        "Overridden to export a graph to a dot file"
        if len(a.connectMap) > 0:
            fd = open(self._fname, "a") 
            node_map = {}
            print >> fd, "digraph G {"
            for from_node in a.connectMap.keys():
                if from_node not in node_map:
                   node_map[from_node] = len(node_map)
                for connect_tuple in a.connectMap[from_node]:
                    edge,to_node = connect_tuple
                    if to_node not in node_map:
                       node_map[to_node] = len(node_map)
                    print >> fd, "  %s -> %s" % (node_map[from_node], node_map[to_node])
            for nodeAnno, nodeNum in node_map.items():
               if nodeAnno is None:
                  print >> fd, "  %s [shape=none,label=\"\"]" % (nodeNum)
               else:
                  print >> fd, "  %s []" % (nodeNum)
            print >> fd, "}"
            fd.close()


#-------------------------------------
# if executed by itself, run all the doc tests

if __name__ == "__main__":
    Logger.setDoctest(logger) 
    import doctest
    doctest.testmod()
