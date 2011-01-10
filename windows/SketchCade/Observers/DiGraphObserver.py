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



logger = Logger.getLogger('DiGraphObserver', Logger.WARN )

#-------------------------------------

class DiGraphAnnotation(Annotation):
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
            for (tail_node,tip_node) in all_pair( tail_list, tip_list ):
                if tail_node not in self.connectMap:
                    self.connectMap[tail_node] = []
                self.connectMap[tail_node].append( (e,tip_node) )
        logger.debug("connectMap = %s", str(self.connectMap) )

    def tipToNode( self, arrow_anno, circle_anno ):
        "return true if the tip of the arrow points to the circle"
        return GeomUtils.pointDist( arrow_anno.tip,  circle_anno.center ) < circle_anno.radius*1.5

    def tailToNode( self, arrow_anno, circle_anno ):
        "return true if the tail of the arrow comes from the circle"
        return GeomUtils.pointDist( arrow_anno.tail, circle_anno.center ) < circle_anno.radius*1.5

    def shouldConnect( self, arrow_anno, circle_anno ):
        "given an arrow and a circle anno, return true if arrow points from/to circle"
        return self.tipToNode(arrow_anno, circle_anno) or self.tailToNode(arrow_anno, circle_anno)


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
            for from_node in a.connectMap.keys():
                for connect_tuple in a.connectMap[from_node]:
                    edge,to_node = connect_tuple
                    SketchGUI.drawCircle( edge.tail.X, edge.tail.Y, radius=7, width=2, color="#ccffcc")
                    SketchGUI.drawCircle( edge.tip.X, edge.tip.Y, radius=7, width=2, color="#ccffcc")

                    #x1,y1 = from_node.center.X, from_node.center.Y
                    #x2,y2 = edge.tail.X, edge.tail.Y
                    #SketchGUI.drawLine( x1,y1,x2,y2, width=2,color="#ccffcc")
                    #x1,y1 = to_node.center.X, to_node.center.Y
                    #x2,y2 = edge.tip.X, edge.tip.Y
                    #SketchGUI.drawLine( x1,y1,x2,y2, width=2,color="#ccffcc")

#-------------------------------------
# if executed by itself, run all the doc tests

if __name__ == "__main__":
    Logger.setDoctest(logger) 
    import doctest
    doctest.testmod()
