"""
filename: ArrowObserver.py

description:
   This module implements 2 classes, ArrowAnnotation (which is applied to any 
   annotableObjects to describe as an arrow), and ArrowMarker (which watches
   for strokes that looks like arrows and adds the arrow annotation)

Doctest Examples:

>>> c = ArrowMarker()

example of something not a arrow
>>> linepoints = [Point(x,2*x) for x in range(1,20)] 
>>> c.onStrokeAdded(Stroke(linepoints))

"""

#-------------------------------------

import math
import pdb
from Utils import Logger
from Utils import GeomUtils
from Utils import Template

from SketchFramework import SketchGUI
from SketchFramework.Point import Point
from SketchFramework.Stroke import Stroke
from SketchFramework.Board import BoardObserver, BoardSingleton
from SketchFramework.Annotation import Annotation, AnnotatableObject

logger = Logger.getLogger('ArrowObserver', Logger.DEBUG)

#-------------------------------------

class ArrowAnnotation( Annotation ):
    def __init__(self, tip, tail, linearity=0):
        Annotation.__init__(self)
        self.tip = tip  # Point
        self.tail = tail  # Point
        self.linearity = linearity

#-------------------------------------

# FIXME: first go -- only single stroke arrows

class ArrowMarker( BoardObserver ):

    def __init__(self):
        BoardSingleton().AddBoardObserver( self )
        BoardSingleton().RegisterForStroke( self )
        
        #For multistroke arrows, keep track of arrowheads and line endpoints
        # and match them up into arrows
        self._arrowHeads = []
        self._endpoints = []
        
        self.arrowHeadMatcher = Template.TemplateDict(filename = "Utils/arrowheads.templ")
        
        

    def onStrokeAdded( self, stroke ):
        "Watches for Strokes that look like an arrow to Annotate"
        smoothedStroke = GeomUtils.strokeSmooth(stroke)
        ep1 = smoothedStroke.Points[0]
        ep2 = smoothedStroke.Points[-1]
        isArrowHead = False
        #GeomUtils.ellipseAxisRatio(stroke)


        #Match single-stroke arrows
        tip, tail = _isSingleStrokeArrow(smoothedStroke)
        if tip is None or tail is None:
            revpts = list(smoothedStroke.Points)
            revpts.reverse()
            tip, tail = _isSingleStrokeArrow(Stroke(revpts))
        
        if  tip is not None and tail is not None:
            isArrowHead = False
            anno = ArrowAnnotation( tip, tail )
            BoardSingleton().AnnotateStrokes( [stroke],  anno)
        else:
            if _isArrowHead(smoothedStroke, self.arrowHeadMatcher): #We've matched an arrowhead
                head = smoothedStroke
                isArrowHead = True
                strokeNorm = GeomUtils.strokeNormalizeSpacing(smoothedStroke, numpoints = 5)
                tip = strokeNorm.Points[2] #Middle normalized point is the tip
                
        
        #Match it to any tails we have
        if isArrowHead:
            matchedTails = self._matchHeadtoTail(head = smoothedStroke, point = tip)
            for headpoint, tail in matchedTails:
                #Orient the tail correctly
                if tail.Points[0] == headpoint:
                    endpoint = tail.Points[-1]
                else:
                    endpoint = tail.Points[0]
                anno = ArrowAnnotation(tip, endpoint)
                BoardSingleton().AnnotateStrokes([head, tail],anno)
        
        #Match it like a tail even if we think it's an arrowhead. Oh ambiguity!
        matchedHeads = self._matchHeadtoTail(tail = smoothedStroke, point = ep1)
        for tip, head in matchedHeads:
            anno = ArrowAnnotation(tip, ep2)
            BoardSingleton().AnnotateStrokes([head, stroke],anno)
            
        matchedHeads = self._matchHeadtoTail(tail = smoothedStroke, point = ep2)
        for tip, head in matchedHeads:
            anno = ArrowAnnotation(tip, ep1)
            BoardSingleton().AnnotateStrokes([head, stroke],anno)
        
        #Add this stroke to the pool for future evaluation
        self._endpoints.append( (ep1, stroke) )
        self._endpoints.append( (ep2, stroke) )
        if isArrowHead:
            self._arrowHeads.append( (tip, stroke) )

        
            
    def _matchHeadtoTail(self, head = None, tail = None, point = None):
        """Input head stroke or tail stroke. If head is specified, match it to a tail. If tail is specified, match it to a head.
           Parameter 'point' should be the tip if head is specified, the end-point if tail is specified.
           Returns a list of tuples: (tip, head_stroke) if tail is specified, (endpoint, tail_stroke) if head is specified."""
        retlist = []
        if point is None:
            return retlist
            
        if head is not None and tail is None: #Head is specified, find the tail
            tip = point
            for endpoint, stroke in self._endpoints:
                if _isPointWithHead(endpoint, head, tip):
                    retlist.append( (endpoint, stroke) )

        elif tail is not None and head is None: #Find the head
            endpoint = point
            for tip, stroke in self._arrowHeads:
                if _isPointWithHead(endpoint, stroke, tip):
                    retlist.append( (tip, stroke) )
        return retlist
                

    def onStrokeRemoved(self, stroke):
        "When a stroke is removed, remove arrow annotation if found and clean up local state"
        for ep_tuple in list(self._endpoints):
            if ep_tuple[1] is stroke:
                self._endpoints.remove(ep_tuple)
        for head_tuple in list( self._arrowHeads ):
            if head_tuple[1] is stroke:
                self._arrowHeads.remove(head_tuple)
                
    	for anno in stroke.findAnnotations(ArrowAnnotation, True):
            BoardSingleton().RemoveAnnotation(anno)


def _isPointWithHead(point, head, tip):
    "Returns true if point is close enough and within the cone of the head stroke"
    ep1 = head.Points[0]
    ep2 = head.Points[-1]
    midpoint = Point((ep1.X + ep2.X)/2, (ep1.Y + ep2.Y)/2)
    tip_to_endpoint = GeomUtils.pointDistanceSquared(point.X, point.Y, tip.X, tip.Y)
    tip_to_backofarrowhead =  GeomUtils.pointDistanceSquared(tip.X, tip.Y, midpoint.X, midpoint.Y)
    
    if tip_to_endpoint < tip_to_backofarrowhead:
        if GeomUtils.pointInAngleCone(point, ep1, tip, ep2):
            return True
    return False
    
#-------------------------------------

class ArrowVisualizer( BoardObserver ):
    "Watches for Arrow annotations, draws them"
    def __init__(self):
        BoardSingleton().AddBoardObserver( self )
        BoardSingleton().RegisterForAnnotation( ArrowAnnotation, self )
        self.annotation_list = []

    def onAnnotationAdded( self, strokes, annotation ):
        "Watches for annotations of Arrows and prints out the Underlying Data" 
        self.annotation_list.append(annotation)

    def onAnnotationRemoved(self, annotation):
        "Watches for annotations to be removed"
        if annotation in self.annotation_list:
            self.annotation_list.remove(annotation)

    def drawMyself( self ):
        for a in self.annotation_list:
            SketchGUI.drawCircle( a.tail.X, a.tail.Y, color="#93bfdd", width=2.0, radius=4)
            SketchGUI.drawCircle( a.tip.X, a.tip.Y, color="#cc5544" , width=2.0, radius=4)
            
#-------------------------------------

def _isArrowHead(stroke, *args, **kargs):
    """
    curvature_list = []
    
    fp = open("indata.csv", "w")
    sNorm = GeomUtils.strokeNormalizeSpacing(stroke, numpoints = 30)
    prev_vect = None
    prev_pt = None
    for point in sNorm.Points:
        if prev_vect == None:
            if prev_pt is not None:
                prev_vect = (point.X - prev_pt.X, point.Y - prev_pt.Y)
            prev_pt = point
            continue
        vector = [point.X - prev_pt.X, point.Y - prev_pt.Y]
        if vector == (0.0, 0.0) or prev_vect == (0.0, 0.0):
            curvature = 0.0
        else:
            curvature = GeomUtils.vectorDistance(vector, prev_vect)
        for i in range(30 * curvature/int((math.pi / 2)) ):
            print " ",
        print "*      ",
        print  "%s" % (curvature)
        curvature_list.append(curvature)
        prev_vect = vector
        prev_pt = point
    print >> fp, "Segment,Curvature"
    for idx, curv in enumerate(curvature_list):
        print >> fp, "%s,%s" % (idx,curv)
    fp.close()
    """
    return _isArrowHead_Template(stroke, args[0])
        
def _isArrowHead_Template(stroke, matcher):
    score_dict = matcher.Score([stroke])
    if score_dict['score'] < 0.2:
        return True
    return False

def _isSingleStrokeArrow(stroke):
    "Input: Single stroke for evaluation. Returns a tuple of points (tip, tail) if the stroke is an arrow, (None, None) otherwise"
    logger.debug("stroke len %d", stroke.length() )
    if len(stroke.Points) < 10:
        logger.debug("Not an arrow: stroke too short")
        return (None, None)# too small to be arrow

    norm_len = len(stroke.Points)
    points = GeomUtils.strokeNormalizeSpacing( stroke, numpoints=norm_len).Points

    points.reverse() # start from end
    # find the first 90 degree turn in the stroke
    orilist = GeomUtils.strokeLineSegOrientations( Stroke(points) )
    #logger.debug("stroke ori %s", str(orilist) )
    prev = None
    i = 0
    for i,ori in enumerate(orilist):
        if prev is None:
            prev = ori
            continue
        if GeomUtils.angleDiff(ori,prev)>90: break  # found the first turn at index i
    first_corner = i
    # now we know the scale of the arrow head if there is one
    # if the first corner is more than 1/4 of the way from the end of the stroke
    if first_corner > norm_len/3:
        logger.debug("Not an arrow: First right angle too far from endpoint")
        return (None, None) # scale is wrong for an arrowhead        

    tail = stroke.Points[0] # first of the original points
    tip = points[i] # reverse point

    # create a list of the monoticity of all substrokes from the first corner to some dist after
    m_list = [ GeomUtils.strokeMonotonicity(Stroke(points[first_corner:x])) for x in range(first_corner+2,first_corner*3) ]
    if len(m_list) == 0:
        logger.debug("Not an arrow: Stroke monotonicity list zero length")
        return (None, None)
    m_min = min(m_list) 
    #logger.debug("stroke mon (%f)", m_min )
    if m_min>0.65:
        logger.debug("Not an arrow: Stroke too monotonic")
        return (None, None)# too monotonic after the first corner, need to double back
    
    return (tip, tail)
if __name__ == "__main__":
    Logger.setDoctest(logger) 
    import doctest
    doctest.testmod()
