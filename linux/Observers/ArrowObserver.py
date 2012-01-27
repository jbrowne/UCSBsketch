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
from xml.etree import ElementTree as ET

logger = Logger.getLogger('ArrowObserver', Logger.DEBUG)

#-------------------------------------

class ArrowAnnotation( Annotation ):
    def __init__(self, tip, tail, headstroke = None, tailstroke = None, direction = 'tail2head', linearity=0):
        Annotation.__init__(self)
        self.tip = tip  # Point
        self.tail = tail  # Point
        self.linearity = linearity
        self.headstroke = headstroke
        self.tailstroke = tailstroke
        self.direction = direction # 'tail2head' vs. 'head2tail' for the direction the tail stroke was drawn in
    def xml( self ):
        "Returns an element tree object for the XML serialization of this annotation"
        root = Annotation.xml(self)

        root.attrib['headstroke'] = str(self.headstroke.id)
        root.attrib['tailstroke'] = str(self.tailstroke.id)
        root.attrib['direction'] = str(self.direction)

        tail  = ET.SubElement(root, "tail")
        tail.attrib['x'] = str(self.tail.X)
        tail.attrib['y'] = str(self.tail.Y)

        tip  = ET.SubElement(root, "tip")
        tip.attrib['x'] = str(self.tip.X)
        tip.attrib['y'] = str(self.tip.Y)


        return root

#-------------------------------------

# FIXME: first go -- only single stroke arrows

class ArrowMarker( BoardObserver ):

    def __init__(self):
        BoardSingleton().AddBoardObserver( self , [ArrowAnnotation])
        BoardSingleton().RegisterForStroke( self )
        
        #For multistroke arrows, keep track of arrowheads and line endpoints
        # and match them up into arrows
        self._arrowHeads = [] #tuples of (arrowhead_tip, arrowhead_stroke)
        self._endpoints = []  #tuples of (endpoint, tail_stroke), one for each endpoint of a tail
        
        self.arrowHeadMatcher = Template.TemplateDict(filename = "Utils/arrowheads.templ")
        
        

    def onAnnotationSuggested(self, anno_type, strokelist):
        """Called when the a list of strokes are suggested to yield an annotation of type anno_type."""

        #First pass, assume we were just too strict with the distance/size thresholds
        knownHeads = []
        knownTails = []
        for tip, stk in self._arrowHeads:
            if stk in strokelist:
                knownHeads.append( (tip, stk) )
        for ep, tail_stk in self._endpoints:
            if tail_stk in strokelist:
                for tip, head_stk in knownHeads:
                    if head_stk == tail_stk:
                        continue
                    headEnds = ( head_stk.Points[0], head_stk.Points[-1] )
                    if GeomUtils.pointInAngleCone(ep, headEnds[0], tip, headEnds[1]):
                        anno = ArrowAnnotation( tip, ep, headstroke= head_stk, tailstroke = tail_stk )
                        BoardSingleton().AnnotateStrokes([head_stk, tail_stk],anno)
                        logger.debug("Suggestion Response: Matched arrow with looser constraints")
                        return

        #Second pass, we missed the arrowhead to begin with

        logger.warn("Not able to generate Arrow!")
        return

                        
                        
                


 
    def onStrokeAdded( self, stroke ):
        "Watches for Strokes that look like an arrow to Annotate"
        smoothedStroke = GeomUtils.strokeSmooth(stroke)
        ep1 = stroke.Points[0]
        ep2 = stroke.Points[-1]
        #ep1 = smoothedStroke.Points[0]
        #ep2 = smoothedStroke.Points[-1]
        isArrowHead = False
        #GeomUtils.ellipseAxisRatio(stroke)


        #Match single-stroke arrows
        #DISABLED
        logger.debug("**Warning: Single-stroke arrows disabled**")
        tip, tail = None, None
        tip, tail = _isSingleStrokeArrow(smoothedStroke)
        #if tip is None or tail is None:
            #revpts = list(smoothedStroke.Points)
            #revpts.reverse()
            #tip, tail = _isSingleStrokeArrow(Stroke(revpts))
        
        if  tip is not None and tail is not None:
            isArrowHead = False
            anno = ArrowAnnotation( tip, tail, headstroke= stroke, tailstroke = stroke )
            BoardSingleton().AnnotateStrokes( [stroke],  anno)
        #/DISABLED
        else:
            if _isArrowHead(smoothedStroke, self.arrowHeadMatcher):
                logger.debug("Arrowhead Found")
                #head = smoothedStroke
                head = stroke
                isArrowHead = True

                #                * (tip-point)
                #              o   o
                #             o      o
                #            o         o
                #          o            o
                
                #Get the endpoints/tip point as max curvature
                strokeNorm = GeomUtils.strokeNormalizeSpacing(smoothedStroke, numpoints = 7)
                curvatures = GeomUtils.strokeGetPointsCurvature(strokeNorm)
                ptIdx = curvatures.index(max(curvatures))
                tip = strokeNorm.Points[ptIdx] #Middle is the point of max curvature

                #Match it to any tails we have 
                matchedTails = self._matchHeadtoTail(head = stroke, point = tip)
                for headpoint, tail in matchedTails:
                    #Orient the tail correctly
                    if tail.Points[0] == headpoint:
                        endpoint = tail.Points[-1]
                        direction = 'head2tail'
                    elif tail.Points[-1] == headpoint:
                        endpoint = tail.Points[0]
                        direction = 'tail2head'

                    logger.debug("Stroke is head of arrow, drawn %s" % (direction))
                    anno = ArrowAnnotation(tip, endpoint, headstroke = stroke, tailstroke = tail, direction = direction)
                    BoardSingleton().AnnotateStrokes([head, tail],anno)
        
        #Match it like a tail even if we think it's an arrowhead. Oh ambiguity!
        matchedHeads = self._matchHeadtoTail(tail = stroke, point = ep1)
        tail = stroke
        for tip, head in matchedHeads:
            logger.debug("Stroke is tail of arrow, drawn head2tail")
            anno = ArrowAnnotation(tip, ep2, headstroke = head, tailstroke = tail, direction='head2tail') #Arrow is from the back endpoint to the tip of the arrowhead
            BoardSingleton().AnnotateStrokes([head, tail],anno)
            
        matchedHeads = self._matchHeadtoTail(tail = stroke, point = ep2)
        for tip, head in matchedHeads:
            logger.debug("Stroke is tail of arrow, drawn tail2head")
            anno = ArrowAnnotation(tip, ep1, headstroke = head, tailstroke =tail, direction='tail2head')
            BoardSingleton().AnnotateStrokes([head, tail],anno)
        
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
            ep1, ep2 = head.Points[0], head.Points[-1]
            headBreadth = GeomUtils.pointDistance(ep1.X, ep1.Y, ep2.X, ep2.Y)
            for endpoint, tailStroke in self._endpoints:
                pointingLength = len(tailStroke.Points) / 5
                if endpoint == tailStroke.Points[0]: #Treat as drawn head2tail
                    tailpoints = tailStroke.Points
                    linept1, linept2 = tailStroke.Points[pointingLength], endpoint
                elif endpoint== tailStroke.Points[-1]: #Treat as drawn tail2head
                    tailpoints = list(reversed(tailStroke.Points))
                    linept1, linept2 = tailStroke.Points[-pointingLength], endpoint

                headLen = GeomUtils.strokeLength(head) 
                tailLen = GeomUtils.strokeLength(tailStroke)
                pointWithHead = _isPointWithHead(tailpoints, head, tip)
                if headLen < tailLen * 2 \
                and pointWithHead:
                    logger.debug("Head stroke has a tail close and within cone")
                    #headToTail
                    pointsTo = GeomUtils.linePointsTowards(linept1, linept2, tip, headBreadth)
                    if pointsTo:
                        retlist.append( (endpoint, tailStroke) )
                else:
                    if headLen < tailLen * 2:
                        logger.debug("  Head stroke scale is okay for this arrowhead")
                    else:
                        logger.debug("  Head stroke scale is BAD for this arrowhead")
                        logger.debug("  Head Len: %s, tail Len: %s" % (headLen, tailLen))
                    if pointWithHead:
                        logger.debug("  Head stroke is NOT close or within cone of an arrowhead\n")
                    else:
                        logger.debug("  Head stroke is close and within cone of an arrowhead\n")

        elif tail is not None and head is None: #Find the head
            endpoint = point
            pointingLength = len(tail.Points) / 5

            if endpoint == tail.Points[0]: #Treat as drawn head2tail
                tailpoints = tail.Points
                linept1, linept2 = tail.Points[pointingLength], endpoint
            elif endpoint== tail.Points[-1]: #Treat as drawn tail2head
                tailpoints = list(reversed(tail.Points))
                linept1, linept2 = tail.Points[-pointingLength], endpoint

            for tip, headStroke in self._arrowHeads:
                ep1, ep2 = headStroke.Points[0], headStroke.Points[-1]
                headBreadth = GeomUtils.pointDistance(ep1.X, ep1.Y, ep2.X, ep2.Y)
                headLen = GeomUtils.strokeLength(headStroke) 
                tailLen = GeomUtils.strokeLength(tail)
                pointWithHead = _isPointWithHead(tailpoints, headStroke, tip)
                if headLen < tailLen * 2\
                and pointWithHead:
                    logger.debug("Tail stroke is close and within cone of an arrowhead")
                    pointsTo = GeomUtils.linePointsTowards(linept1, linept2, tip, headBreadth)
                    if pointsTo:
                        retlist.append( (tip, headStroke) )
                else:
                    if headLen < tailLen * 2:
                        logger.debug("  Tail stroke scale is okay for this arrowhead")
                    else:
                        logger.debug("  Tail stroke scale is BAD for this arrowhead")
                        logger.debug("  Head Len: %s, tail Len: %s" % (headLen, tailLen))

                    if not pointWithHead:
                        logger.debug("  Tail stroke is NOT close or within cone of an arrowhead\n")
                    else:
                        logger.debug("  Tail stroke is close and within cone of an arrowhead\n")
                        
        return retlist
                

    def onStrokeRemoved(self, stroke):
        "When a stroke is removed, remove arrow annotation if found and clean up local state"
        for ep_tuple in list(self._endpoints):
            if ep_tuple[1] is stroke:
                self._endpoints.remove(ep_tuple)
        for head_tuple in list( self._arrowHeads ):
            if head_tuple[1] is stroke:
                logger.debug("Removed arrowhead")
                self._arrowHeads.remove(head_tuple)
                
    	for anno in stroke.findAnnotations(ArrowAnnotation, True):
            logger.debug("Removing annotation")
            BoardSingleton().RemoveAnnotation(anno)


def _isPointWithHead(tailpoints, head, tip):
    "Returns true if point is close enough and within the cone of the head stroke"

    distanceThresh = 1 
    distanceThresh *= distanceThresh #Keep up with squared distances

    point = tailpoints[0]
    ep1 = head.Points[0]
    ep2 = head.Points[-1]
    #              *  tip
    #           o     o
    #          o        o
    #        o            o
    #      o      (x)      o
    #          midpoint
    #
    #             * endpoint
    #            o
    #            o
    #           o
    #         (etc)
    midpoint = Point((ep1.X + ep2.X)/2, (ep1.Y + ep2.Y)/2) #Mid-way between the two endpoints of the arrowhead
    tip_to_endpoint = GeomUtils.pointDistanceSquared(point.X, point.Y, tip.X, tip.Y)
    tip_to_backofarrowhead =  GeomUtils.pointDistanceSquared(tip.X, tip.Y, midpoint.X, midpoint.Y)
    endpoint_to_backofarrowhead = GeomUtils.pointDistanceSquared(point.X, point.Y, midpoint.X, midpoint.Y)

    #fuzz = math.sqrt(tip_to_backofarrowhead) #Number of pixels to fuzz the "in-angle-cone" test
    
    #logger.debug("tip_to_endpoint: %s\n, tip_to_backofarrowhead: %s,\n endpoint_to_backofarrowhead: %s" % (tip_to_endpoint, tip_to_backofarrowhead, endpoint_to_backofarrowhead))
    #Tail's endpoint is close to the end of the arrowhead, or even closer to the tip of the arrowhead
    if tip_to_backofarrowhead >= endpoint_to_backofarrowhead or tip_to_backofarrowhead >= tip_to_endpoint:
        logger.debug("Distance from head-tip to tail-endpoint is good!")
        #Check the in-angle cone progressively down the tail
        epList = tailpoints[: len(tailpoints) / 3]

        for pt in epList:
            if GeomUtils.pointInAngleCone(pt, ep1, tip, ep2):
                logger.debug("Endpoint inside angle cone")
                return True
    return False
    
#-------------------------------------

class ArrowVisualizer( BoardObserver ):
    "Watches for Arrow annotations, draws them"
    def __init__(self):
        BoardSingleton().AddBoardObserver( self ,[])
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

def _isArrowHead(stroke, matcher):
    
    numPts = 11
    sNorm = GeomUtils.strokeNormalizeSpacing(stroke, numpoints = numPts)
    curvatures = GeomUtils.strokeGetPointsCurvature(sNorm)
    maxCurv = max(curvatures)
    maxCurvIdx = curvatures.index(maxCurv)
    #Make sure the max curvature is roughly in the middle of the stroke before even bothering
    #   with more complicated checks
    if maxCurvIdx > (numPts / 5.0) and maxCurvIdx < ( 4 * numPts / 5.0): 
        strkLen = GeomUtils.strokeLength(stroke)
        arrowHeadStroke = GeomUtils.strokeNormalizeSpacing(Stroke([sNorm.Points[0], sNorm.Points[maxCurvIdx], sNorm.Points[-1]]), numpoints = strkLen) #What would the approximated arrowhead look like?
        origStroke = GeomUtils.strokeNormalizeSpacing(stroke, numpoints = strkLen)
        approxAcc = GeomUtils.strokeDTWDist(sNorm, arrowHeadStroke)
        logger.debug("Stroke approximates arrowhead with %s accuracy" % (approxAcc))

        return approxAcc < 500000
        #_isArrowHead_Template(stroke, matcher) or _isArrowHead_Template(Stroke(list(reversed(stroke.Points))), matcher)
    
    return False

        
def _isArrowHead_Template(stroke, matcher):
    score_dict = matcher.Score([stroke])
    logger.debug("Arrowhead template score: %s" % (score_dict['score']))
    if score_dict['score'] < 0.2:
        return True
    return False

def _isSingleStrokeArrow(stroke):
    "Input: Single stroke for evaluation. Returns a tuple of points (tip, tail) if the stroke is an arrow, (None, None) otherwise"
    logger.debug("stroke len %d", stroke.length() )
    if len(stroke.Points) < 10:
        logger.debug("Not a single-stroke arrow: stroke too short")
        return (None, None)# too small to be arrow

    """
    #Starting code for line curvature classification
    #points = GeomUtils.strokeNormalizeSpacing( stroke, numpoints=50).Points
    for gran in range(1, 10):
        norm_len = max(len(stroke.Points) / gran, 5)
        points = GeomUtils.strokeNormalizeSpacing( stroke, numpoints=norm_len).Points

        points.reverse() # start from end
        # find the first 90 degree turn in the stroke
        curvatures = GeomUtils.strokeGetPointsCurvature( Stroke(points) )
        gran = 0.1
        for idx, ori in enumerate(curvatures):
            print "%s:\t|" % (idx),
            quantity = ori 
            while quantity > 0:
                quantity -= gran
                print "X",
            print "\t\t%s" % (ori)
        print "_______________________________"
        print "Max:%s, Avg%s" % (max(curvatures), sum(curvatures)/float(len(curvatures)))
        print "_______________________________"
    #/EndCurvature classification
    """

    norm_len = max(len(stroke.Points) / 10, 15)
    points = GeomUtils.strokeNormalizeSpacing( stroke, numpoints=norm_len).Points
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
    if first_corner > norm_len/5:
        logger.debug("Not a ss arrow: First right angle too far from endpoint")
        return (None, None) # scale is wrong for an arrowhead        

    tail = stroke.Points[0] # first of the original points
    tip = points[i] # reverse point

    # create a list of the monoticity of all substrokes from the first corner to some dist after
    m_list = [ GeomUtils.strokeMonotonicity(Stroke(points[first_corner:x])) for x in range(first_corner+2,first_corner*3) ]
    if len(m_list) == 0:
        logger.debug("Not a ss arrow: Stroke monotonicity list zero length")
        return (None, None)
    m_min = min(m_list) 
    #logger.debug("stroke mon (%f)", m_min )
    if m_min>0.65:
        logger.debug("Not a ss arrow: Stroke too monotonic")
        return (None, None)# too monotonic after the first corner, need to double back
    
    logger.debug("Single Stroke Arrow found!")
    return (tip, tail)
if __name__ == "__main__":
    Logger.setDoctest(logger) 
    import doctest
    doctest.testmod()
