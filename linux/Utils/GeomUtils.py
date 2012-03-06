"""
filename: GeomUtils.py

description:
   This module implements a class GeomUtils that provides different geometry functions.

[are these still on the todo list?]
TODO: Centroid (and thus convex hull) is used too often: refactor to use a Stroke.Center instead of
    finding the true centroid every time.
    Also, why is GeomUtils a class at all?

TODO: Normalize the names behind the type of objects that they work on, perhaps points, angles, strokes, etc..
TODO: Need to make sure that we are consistant about these having input that is "stroke" versus "list of points"
TODO: Finish out doctest for the rest of functions in this module

--- angles ---

>>> angles = range(-180,500,90)
>>> angles
[-180, -90, 0, 90, 180, 270, 360, 450]

- Angles can be normalized to be between 0 and 350 with angleNormalize
>>> normangles = [angleNormalize(x) for x in angles]
>>> normangles
[180, 270, 0, 90, 180, 270, 0, 90]

- Angles can be compared with one another with angleDiff
>>> [angleDiff(a,b) for (a,b) in zip(angles,normangles)]
[0, 0, 0, 0, 0, 0, 0, 0]
>>> [angleDiff(a,b) for (a,b) in zip(angles,[n-190 for n in normangles])]
[170, 170, 170, 170, 170, 170, 170, 170]

- Unlike angleDiff, the order matters for angleSub (and results can be -180 to 180)
>>> [angleSub(a,b) for (a,b) in zip(angles,[n-190 for n in normangles])]
[-170, -170, -170, -170, -170, -170, -170, -170]

--- strokes ---

>>> instroke = Stroke([Point(x**3,x**3) for x in range(1,8)])
>>> [ str(p) for p in instroke.Points]
['(1.0,1.0)', '(8.0,8.0)', '(27.0,27.0)', '(64.0,64.0)', '(125.0,125.0)', '(216.0,216.0)', '(343.0,343.0)']

>>> straightStroke = Stroke([Point(x,x) for x in range(1,8)])
>>> ellipseAxisRatio(straightStroke)
1.0
- Given a path as a list of points (e.g. from a stroke), you can make new list of
- points over that path with a constant length between each one.  In this example, they
- are are now about 34 units apart in both x and y
>>> [ str(p) for p in strokeNormalizeSpacing(instroke,10).Points]
['(1.0,1.0)', '(35.2,35.2)', '(69.4,69.4)', '(103.6,103.6)', '(137.8,137.8)', '(172.0,172.0)', '(206.2,206.2)', '(240.4,240.4)', '(274.6,274.6)', '(308.8,308.8)', '(343.0,343.0)']

- strokeCircularity will give a number from 0.0 to 1.0, with 1.0 being a perfect circle.  
- Below we test it first with a line, and then with a perfectly generated circle stroke
>>> strokeCircularity(instroke)
0.0
>>> circlepoints = [(int(math.sin(math.radians(x))*100+200),int(math.cos(math.radians(x))*100)+200) for x in range(0,360,20)]
>>> 0.98 < strokeCircularity(Stroke(circlepoints)) < 1
True

- strokeOrientation measure the angle of a stroke
- in this case, the line looks like (x,x) so it should be 45 degrees
>>> strokeOrientation(instroke)
45.0

- strokeConcavity measures what fraction of points fall inside the convex hull of the stroke
- for a circle, it should be zero because none of the points are on the interior of the hull.
>>> strokeConcavity(Stroke(circlepoints))
0.0

- strokeChopEnds cuts the ends off of a stroke
>>> chopstroke = strokeChopEnds(instroke,0.35,4)
>>> [ str(p) for p in chopstroke.Points]
['(8.0,8.0)', '(27.0,27.0)', '(64.0,64.0)', '(125.0,125.0)', '(216.0,216.0)']

- strokeLineSegOrientations returns a list of all the orientations of the line segments
- in the stroke.  If we feed it a cicle, the start (normalized) should be 0.0, and about
- halfway though we should be about at 180 degrees
>>> lso = strokeLineSegOrientations( Stroke(circlepoints) )
>>> lso[0]==0.0
True

- strokeDTWDist is a function that can be used to compare two strokes to one another,
- if you compare two things that are the same perfectly, they should match with 0.0.
- the more different they are, the bigger the output, but there is no upper bound
>>> strokeDTWDist( instroke, instroke )
0.0


--- lists of strokes ---
- computes the bounding box of a list of strokes, and returns a tuple of
- point as (topleft,bottomright)
>>> (tl,br) = strokelistBoundingBox( [instroke, instroke] )
>>> str(tl),str(br)
('(1.0,343.0)', '(343.0,1.0)')

"""

import math
import sys
import pdb

from Utils import Logger
from SketchFramework.Point import Point
from SketchFramework.Stroke import Stroke

logger = Logger.getLogger('GeomUtils', Logger.DEBUG )


#--------------------------------------------------------------
# Functions on Points

# FIXME: maybe these should be functions on "cordinates" rather than points


def pointDistanceSquared(X1, Y1, X2, Y2):
    "Input: two points. Returns the squared distance between the points"
    distance = (X2 - X1) ** 2 + (Y2 - Y1) ** 2
    return distance

def pointDistance(X1, Y1, X2, Y2):
    "Input: two points. Returns the euclidian distance between the points"
    return math.sqrt(float(pointDistanceSquared(X1,Y1,X2,Y2)));

def pointOrientation(X1, Y1, X2, Y2):
    "Compute the angle of orentation (in degrees) of a segment of the form (X1,Y1),(X2,Y2)."
    return angleNormalize( math.degrees( math.atan2(Y1-Y2,X1-X2) ) )

def pointDist(p1, p2):
    "Input: two points. Returns the euclidian distance between the points"
    return pointDistance( p1.X, p1.Y, p2.X, p2.Y )
    
def rotatePoint(p, angle):
    "Input: point p, rotates p angle radians around the origin (0,0)"
    px = p.X
    py = p.Y
    
    x = px * math.cos(angle) - py * math.sin(angle)
    y = px * math.sin(angle) + py * math.cos(angle) 
    
    return Point(x,y,drawTime = p.T)
    
def pointInAngleCone(point, endpoint1, cusp, endpoint2):
    "Tests if point is within the cone of angle defined by endpoints and cusp"
    if endpoint1.X - cusp.X != 0:
        m = (endpoint1.Y-cusp.Y) / float(endpoint1.X-cusp.X)
        b = (endpoint1.Y - endpoint1.X * m)
    else: 
        m = b = "inf"
    eq1 = {"m":m, "b":b}

    if endpoint2.X - cusp.X != 0:
        m = (endpoint2.Y-cusp.Y) / float(endpoint2.X-cusp.X)
        b = (endpoint2.Y - endpoint2.X * m)
    else: 
        m = b = "inf"
    eq2 = {"m":m, "b":b}

    #See what side our known points are on for each line
    if eq1["m"] != "inf":
        lt_1 = endpoint2.Y < eq1["m"]*endpoint2.X + eq1["b"]
        p_lt_1 = point.Y < eq1["m"]*point.X + eq1["b"]
    else:
        lt_1 = endpoint2.X < cusp.X
        p_lt_1 = point.X < cusp.X

    if eq2["m"] != "inf":
        lt_2 = endpoint1.Y < eq2["m"]*endpoint1.X + eq2["b"]
        p_lt_2 = point.Y < eq2["m"]*point.X + eq2["b"]
    else:
        lt_2 = endpoint1.Y < cusp.X
        p_lt_2 = point.X < cusp.X

    if p_lt_1 == lt_1 and p_lt_2 == lt_2:
        return True
    else:
        return False

def pointInBox(point, boxTL, boxBR):
    "Input: point, and top-left/bottom-right points of bounding box. Returns False if point is outside box, True otherwise"
    inside_vertical = point.Y <= boxTL.Y and point.Y >= boxBR.Y
    inside_horiz = point.X >= boxTL.X and point.X <= boxBR.X
    
    return inside_horiz and inside_vertical


#--------------------------------------------------------------
# Functions on Vectors

def vectorLengthSquared(XCom, YCom):
    "Input: int X,Y representing a vector.  Returns the Length of the Vector, Squared for speed optimizations"
    return XCom ** 2 + YCom ** 2

def vectorLength(XCom, YCom):
    "Input: int X,Y representing a vector.  Returns the Length of the Vector"
    return math.sqrt(vectorLengthSquared(XCom, YCom))

def vectorDot(Xvect, Yvect):
    "Input: list Xvect, list Yvect representing 2 equal-length vectors.  Returns the dot product of the vectors"
    if len(Xvect) != len(Yvect):
       raise ValueError

    retval = 0
    for i in range(len(Xvect)):
       retval += Xvect[i] * Yvect[i]
    return retval

def vectorMagnitude(vector):
    "Input: list vector of size n. Returns the magnitude of the vector in n-dimensions."
    retval = 0
    for component in vector:
       retval += component ** 2
    retval = math.sqrt(retval)
    return retval
def vectorDistance(Xvect, Yvect):
    "Input: list Xvect, list Yvect of equal size n. Returns the angular distance between the vectors in n-dimensions."
    #Compute: Angle = acos( (X dot Y) / |X| |Y| )
    if len(Xvect) != len(Yvect):
       raise ValueError
    dotval = vectorDot(Xvect, Yvect)
    xMag = vectorMagnitude(Xvect)
    yMag = vectorMagnitude(Yvect)

    if xMag == 0 or yMag == 0:
       #One of the vectors is all 0's, i.e. junk?
       return math.pi
    retval = dotval / (xMag * yMag)
    retval = round(retval, 5) #Kludge to avoid some nasty precision errors. Besides, who need accurate similarity metrics?
    retval = math.acos(retval)
    return retval

    




#--------------------------------------------------------------
# Functions on Angles

# FIXME switch this and everyone that calls it over to degrees
# FIXME change name to be angleComputeInterior
def interiorAngle(P1, P2, P3):
    "Input: three points. Returns the interior angle (radians) of the three points with P2 at the center"
    X1 = P1.X
    Y1 = P1.Y
    X2 = P2.X
    Y2 = P2.Y
    X3 = P3.X
    Y3 = P3.Y
    a_len = pointDistanceSquared(X1, Y1, X2, Y2)
    b_len = pointDistanceSquared(X2, Y2, X3, Y3)
    c_len = pointDistanceSquared(X1, Y1, X3, Y3)
    a = sqrt(a_len)
    b = sqrt(b_len)
    c = sqrt(c_len)
    #make more explicit
    try:
        angle = a_len + b_len - c_len
        angle = angle / (2 * a * b)
        angle = math.acos(angle)
    except (ZeroDivisionError, ValueError):
        #print "A, B, C:", angle, "=", a_len, b_len, c_len, a, b
        angle = math.pi
    return angle



def angleNormalize( a ):
    "Input: angle. Covert and angle (in degrees) to a number between 0 and 360."
    a = a % 360
    if ( a < 0 ) : a = a + 360
    return a

def angleDiff( a, b ):
    "Input: angles a and b. Normalize and find the difference in degrees between two angles (result between 0 and 180)."
    #compute distance taking into account wrap around 
    a, b = angleNormalize(a), angleNormalize(b)
    basediff = max(a,b)-min(a,b)
    diff = min( basediff, abs(basediff-360) )       
    assert( diff<=180 and diff>=0 )
    return diff

def angleParallel( a, b ):
    "Input: angles a and b. return a number in [0,1], where 1 equals parallel and 0 is perpendicular."
    #compute distance taking into account wrap around 
    angle_diff = angleDiff( a, b )
    if angle_diff > 90:
        angle_diff = 180-angle_diff
    return 1 - (angle_diff/90.0)

def angleSub( a, b ):
    "Input: angles a and b. Substract one angle from the other (result between -180 and 180)."
    a, b = angleNormalize(a), angleNormalize(b)
    diff = a-b
    if diff>180: diff = diff-360
    if diff<=-180: diff = diff+360
    assert( diff<=180 and diff>-180 )
    return diff

#--------------------------------------------------------------
# Functions on Strokes

def strokeContainsStroke(outerStk, innerStk, granularity = None):
    "Returns whther outerStk contains innerStk"
    #pdb.set_trace()
    #if granularity == None:
        #granularity = max (len(outerStk.Points), len(innerStk.Points))

    #close outerStk
    ep1 = outerStk.Points[0]
    ep2 = outerStk.Points[-1]
    if pointDistanceSquared(ep1.X, ep1.Y, ep2.X, ep2.Y) > 10:
        logger.warn("Checking containment within a stroke that's probably not closed")

    #Test first point inside stroke 1
    if not pointInPolygon(outerStk.Points, innerStk.Points[0]):
        logger.debug("Stroke %s doesn't start in polygon" % innerStk.id)
        return False
    #Test if innerStk ever leaves outerStk's containment
    elif len(getStrokesIntersection(outerStk, innerStk)) > 0:
        logger.debug("Stroke %s leaves polygon" % innerStk.id)
        return False

    logger.debug("Stroke %s CONTAINED" % innerStk.id)
    return True
        

    

def getStrokesIntersection(stroke1, stroke2):
   "Returns the intersection(s) of two strokes"
   intersections = []

   prev1 = None
   for p1 in stroke1.Points:
      if prev1 is not None:
         prev2 = None
         for p2 in stroke2.Points:
            if prev2 is not None:
               cross = getLinesIntersection( (prev1, p1), (prev2, p2) )
               if cross is not None:
                  intersections.append(cross)
            prev2 = p2
      prev1 = p1
   return intersections
                

def translateStroke(inStroke, xDist, yDist):
    "Input: Stroke, and the distance in points to translate in X- and Y-directions. Returns a new translated stroke"
    return inStroke.translate(xDist, yDist)
    
def rotateStroke(inStroke, angle):
    pointlist = []
    for point in inStroke.Points:
        pointlist.append(rotatePoint(point, angle))
    return Stroke(points=pointlist)

def strokeSegments( inStroke ):
    "Input: Stroke. Return a list of the segments in that stroke"
    point_list = [ (p.X,p.Y) for p in inStroke.Points ]  # if this looks like: [(0,0),(1,1),(2,2)] 
    if len(point_list)<2:
        return []
    segments = zip( point_list[:-1], point_list[1:] ); # this looks like: [((0, 0), (1, 1)), ((1, 1), (2, 2))]
    return segments
def strokeGetPointsCurvature( inStroke ):
    "Input: stroke. Returns a list of curvatures at each point. *CAUTION* Endpoints have -1 curvature! "
    endPointCurvature = -1
    prev_vect = None
    prev_pt = None
    curvature_list = []
    if len(inStroke.Points) > 0: #Handle the nonsense curvature at the first point
       curvature_list.append(endPointCurvature)

    for point in inStroke.Points:
	if prev_pt != point:
	    if prev_vect == None:
		if prev_pt is not None:
		    prev_vect = (point.X - prev_pt.X, point.Y - prev_pt.Y)
		prev_pt = point
		continue
	    vector = [point.X - prev_pt.X, point.Y - prev_pt.Y]
	    if vector == (0.0, 0.0) or prev_vect == (0.0, 0.0):
		curvature = 0.0
	    else:
		curvature = vectorDistance(vector, prev_vect)
	    curvature_list.append(curvature)
	    prev_vect = vector
        prev_pt = point

    if len(inStroke.Points) > 1: #Nonsense curvature for the last point
       curvature_list.append(endPointCurvature)

    return curvature_list


def strokeNormalizeSpacing( inStroke, numpoints=50):
    """Input: Stroke.  Return a stroke with points evenly distributed in distance across the original path described by inStroke. 
    Single point strokes just return the point numpoints times"""
    # TODO: right now, this does not retain any stroke properties other than the path of the points in X,Y (i.e. not time data)

    # this is the final list of points to be returned
    normalized_points = []
    inPoints = inStroke.Points

    #Single point strokes case
    if len(inPoints) == 1 or numpoints <= 1: 
        return Stroke(int(numpoints) * [inPoints[0]])
        
    # calculate the total euclidean distance traveled
    total_dist = float(strokeLength(inStroke))
    # set the new distance between points
    gap = total_dist/( numpoints - 1)
    # turn the list of point into a list of line segements
    segments = strokeSegments( inStroke )

    # start at first point
    i = 0; current_dist = 0; 
    # the first point in the new list of points should be the same as the old
    normalized_points.append( inPoints[0] ) 

    # for each new segment (which should be end at length target_dist)
    stop_dist = total_dist * (1 - (1/(2*float(numpoints))) )
    # target_dist will be the running total distance done so far
    target_dist = gap
    while target_dist < stop_dist :

        # walk until we hit the segment containing the target dist
        while current_dist<target_dist:
            (ax,ay),(bx,by) = segments[i]
            current_dist += pointDistance(ax,ay,bx,by)
            i += 1
            # now we should know that segment i-1 contains the best stopping point
            target_seg = segments[i-1]
            (p1x,p1y),(p2x,p2y) = target_seg

        # find the new best point in the middle of that segment
        # figure out how much we overshot the target
        overshot_dist = current_dist - target_dist;
        seg_dist = pointDistance( p1x,p1y, p2x,p2y );

        # the new point should lie on that last segment
        newx = ( (p1x*overshot_dist) + (p2x*(seg_dist-overshot_dist)) ) / float(seg_dist)
        newy = ( (p1y*overshot_dist) + (p2y*(seg_dist-overshot_dist)) ) / float(seg_dist)

	# add this new point to the list        
        normalized_points.append( Point(newx,newy) )

        # move on to the next point
        target_dist += gap


    # make sure not to drop that last point
    normalized_points.append( inPoints[-1] ) # should be final point 
    return Stroke(normalized_points)
    
def strokeLength(inStroke):
    "Input: Stroke.  Returns the total length of the stroke by summing up all of the segments."
    
    totalLength = 0.0
    inPoints = inStroke.Points
    
    for i in range(0, len(inPoints) - 1):
        cur = inPoints[i]
        nxt = inPoints[i + 1]
        
        totalLength += vectorLength(cur.X - nxt.X, cur.Y - nxt.Y)
        
    return totalLength
    #TODO: This func. looks like the perim function, except without closing it off, cause Perim just assumes it's been hulled...

def strokeLinearity(inStroke):
    "Input: Stroke.  Returns the Linearity from [0,1] of a set of points as defined by the Ellipse Axis Ratio by the Monotonicity."
     # The General linearity of the points by the amount that they all point in the same direction
    axisRatio = ellipseAxisRatio(inStroke)
    if axisRatio is not None:
        return axisRatio * strokeMonotonicity(inStroke)
    return 0.0

def strokeChopEnds(inStroke,chopfrac=0.10,minchop=10):
    "Input: Stroke.  Returns a new stroke with the ends chopped off, or the original stroke."
    # Chops chopfrac/2 of the stroke of the front and back of any stroke with more than minchop points
    inPoints = inStroke.Points
    l = len(inPoints)
    if l<minchop:
        return inStroke
    numchop = int(math.floor( l * (chopfrac/2.0) ))
    if numchop==0:
        return inStroke
    newPoints = inPoints[numchop:-numchop]
    return Stroke(newPoints)

def strokeCircularity(inStroke):
    "Input: List inPoints.  Returns the Circularity from [0,1]"
    # of a set of points as defined by the Area Perimeter Ratio 
    # a Circle returns 1, an infinite Line returns 0.  Square returns Pi/4"

    inPoints = strokeNormalizeSpacing(inStroke,30).Points
    if len(inPoints) < 3:
        logger.warn("trying to get the circularity of less than three points")
        return 0

    circularity = 0.0
    pArea = area(inPoints)

    perim = perimeter(inPoints)
    if perim == 0:
        return 0

    circularity = ((4 * math.pi) * pArea) / (perim ** 2)
    return circularity

def strokeConcavity(inStroke):
    "Input: Stroke.  Returns the concavity [0,1] of a set of points as defined by the fraction of points in the stroke on the convex hull."
    inPoints = inStroke.Points 
    if len(inPoints) < 3:
        return 0
    chull = convexHull(inPoints) # find the hull
    # the concavity should be the ratio of the size of the hull to the 
    # number of points in the original stroke
    return 1.0 - (len(chull) / float(len(inPoints)))

def strokeLineSegOrientations( inStroke, normalize=True ):
    "Input: Stroke. Returns a list of the orientations (in degrees) of all the segments in the stroke"
    # if there are are N points, there will be N-1 orientations
    # if normalize is True, then the first segment will be angle 0
    inPoints = inStroke.Points 
    if len(inPoints) < 3:
        return []
    segments = strokeSegments( inStroke )
    orientations = [ pointOrientation(x1,y1,x2,y2) for ((x1,y1),(x2,y2)) in segments ]

    # normalize w.r.t to the first segement
    if normalize:
         offset = orientations[0]
    else:
         offset = 0
    norm_orientations = [ angleNormalize(x-offset) for x in orientations ]
    return norm_orientations

def strokeSmooth(inStroke, width = 1, preserveEnds = False):
    "Input: Stroke.  Returns a simmilar stroke with the points smoothed out"
    inPoints = inStroke.Points;
    outPoints = _smooth(inPoints, width = width, preserveEnds = preserveEnds)
    return Stroke(outPoints)

def strokeDTWDist( testStroke, refStroke):
    "Input: 2 strokes, a cost function Return the Dynamic-Time-Warping distance between this and the reference stroke."

    INFINITY = 1e300

    ref_angles =  strokeLineSegOrientations( refStroke, normalize=True )
    test_angles = strokeLineSegOrientations( testStroke, normalize=True )

    # the dtw matrix stores the first computed element at 1,1 (not 0,0)
    n = len(ref_angles)
    m = len(test_angles)
    dtw = [[0 for col in range(m+1)] for row in range(n+1)]
    for i in range(1,m+1):
        dtw[0][i] = INFINITY
    for i in range(1,n+1):
        dtw[i][0] = INFINITY
    dtw[0][0] = 0

    for i in range(1,n+1):
        for j in range(1,m+1):
            cost = _DTWCostFunc(ref_angles[i-1],test_angles[j-1],i-1,j-1,n,m)
            insertion = dtw[i-1][j] + cost/2
            deletion = dtw[i][j-1] + cost/2
            match = dtw[i-1][j-1] + cost
            dtw[i][j] = min( insertion, deletion, match )
    return dtw[n][m]

def _DTWCostFunc( a, b, i, j, n, m ):
        diff = angleDiff( a,b )
        c = diff * diff  
        if ( abs( (i/float(n)) - (j/float(m)) ) > 0.1 ): return 1e30  
        return c 

def strokeMonotonicity(inStroke):
    "Input: List inPoints.  Returns the amount from  [0,1]  that the line goes it a single direction along it's angle of orientation."
    inPoints = inStroke.Points
    if len(inPoints) < 3:
        return 1    #If less than 3 points, what to do?  return 0, 1, .5 of calculate it for each of these?

    ang = _angleOfOrientation(inStroke)

    #Normalize the orientation
    orientX, orientY = math.cos(ang), math.sin(ang)
    orientMag = vectorLength(orientX, orientY)
    orientX = orientX / orientMag
    orientY = orientY / orientMag

    sum = 0.0
    absSum = 0.0

    for i in range(0, len(inPoints) - 2, 4):
        cur = inPoints[i]
        nxt = inPoints[i + 2]

        vX = nxt.X - cur.X
        vY = nxt.Y - cur.Y

        vLength = vectorLength(vX, vY)

        dot = vX * orientX + vY * orientY

        sum += sign(dot) * vLength
        absSum += vLength

    if (absSum == 0): #Sanity
        return 1

    return abs(sum / absSum)

def strokeOrientation(inStroke):
    "Input: List inPoints.  Returns the Angle of Orientation of a set of points (in degrees) where 0 is horizontal"

    cen = inStroke.Center
    inPoints = inStroke.Points
    pArea = area(inPoints)

    if (len(inPoints) <= 1):
        print "Warning: trying to get the Angle of Orientation of one or fewer points."
        return 0.0

    if pArea == 0:  #Perfect line        
        orientX = inPoints[-1].X - inPoints[0].X
        orientY = inPoints[-1].Y - inPoints[0].Y
        orientMag = vectorLength(orientX, orientY)
        if orientMag == 0:
            return 0.0
        orientX = orientX / orientMag
        orientY = orientY / orientMag
        return math.degrees( math.acos(orientX) )

    moment11 = momentOfOrder(cen, inPoints, 1, 1)
    if moment11 == 0:
        return 0    #There is no Moment of order 1,1.  We'd get a divide by zero.  Orientation is undefined; just return zero.

    angle = (.5 * math.atan((momentOfOrder(cen, inPoints, 0, 2) - momentOfOrder(cen, inPoints, 2, 0)) / (2 * moment11))) \
            + sign(moment11) * math.pi / 4

    return math.degrees(angle)
    
 
def strokeFeaturePoints(inStroke):
   """Returns a list of "interesting" feature points (corners, endpoints) of a stroke"""
   pass


#--------------------------------------------------------------
# Functions on Lists of Strokes

def strokelistBoundingBox( strokelist ):
    "Input: a list of strokes. Returns the bounding box as a tuple of Points, (topleft,bottomright)"
    if len(strokelist) < 1:
        return
    topleft = strokelist[0].BoundTopLeft.copy()
    bottomright = strokelist[0].BoundBottomRight.copy()
    for s in strokelist:
        topleft.X = min( topleft.X, s.BoundTopLeft.X )
        topleft.Y = max( topleft.Y, s.BoundTopLeft.Y)
        bottomright.X = max( bottomright.X, s.BoundBottomRight.X )
        bottomright.Y = min( bottomright.Y, s.BoundBottomRight.Y )    
    return (topleft,bottomright)

#--------------------------------------------------------------
# Functions on Bounding Boxes

def boundingboxOverlap( bb1, bb2 ):
    "Input: two bounding boxes, each a tuple of points (topleft,bottomright).  Returns true only if the boxes overlap"
    bb1_tl,bb1_br = bb1
    bb2_tl,bb2_br = bb2

    box1_x = bb1_tl.X
    box1_y = bb1_br.Y
    box1_w = bb1_br.X - bb1_tl.X
    box1_h = bb1_tl.Y - bb1_br.Y
    box2_x = bb2_tl.X
    box2_y = bb2_br.Y
    box2_w = bb2_br.X - bb2_tl.X
    box2_h = bb2_tl.Y - bb2_br.Y

    if box1_x > (box2_x+box2_w):
        return False # box1 is too far right, no collision
    elif (box1_x+box1_w) < box2_x: 
        return False # box1 is too far left, no collision
    elif box1_y > (box2_y+box2_h): 
        return False # box1 is too far down, no collision
    elif (box1_y+box1_h) < box2_y: 
        return False # box1 is too far up, no collision
    return True # there is a collision

#--------------------------------------------------------------
# Functions on Lists of Points 


def pointListOrientationHistogram(points, direction=False):
    """Return a dict with the histogram of the segment orientations for this pointlist.
    If direction is true, count the direction as unique (i.e. right->left != left->right)"""

    def to_tuple(indict):
        temp = []
        for orient in ['lr', 'tb', 'tlbr', 'trbl']:
            if orient in indict:
                temp.append(indict[orient])
        return tuple(temp)

    if direction:
        print "Sorry, don't support direction yet"
        raise NotImplemented
    else:
        retDict = { 'lr' : 0,
                    'tb' : 0,
                    'tlbr' : 0,
                    'trbl' : 0,
                  }
    if len(points) < 2:
        return to_tuple(retDict)
    else:
        prev = None
        for p in points:
            if prev != None:
                if p.X == prev.X: #same X
                    if p.Y < prev.Y or p.Y > prev.Y:
                        retDict['tb'] += 1
                else:
                    angle = math.atan( (p.Y - prev.Y)/(p.X - prev.X) ) * 57.296 # convert to deg
                    if angle >= 67.5 or angle < -67.5:
                        retDict['tb'] += 1
                    elif angle >= 22.5:
                        retDict['trbl'] += 1
                    elif angle >= -22.5:
                        retDict['lr'] += 1
                    elif angle >= -67.5:
                        retDict['tlbr'] += 1
            #endif prev != None
            prev = p
        #Normalize the histogram to sum() = 1
        totalSegs = sum(retDict.values())
        if totalSegs > 0:
            for orient, count in retDict.items():
                retDict[orient] = count / float(totalSegs)
        return to_tuple(retDict)
        
def momentOfOrder(center, inPoints, p, q):
    "Input: Point center, List inPoints, int p, q.  Returns the Mathematical moment of a set of points or orders p, q"
    retval = []
    for pt in inPoints:
        xpow = (pt.X - center.X) ** p
        ypow = (pt.Y - center.Y) ** q
        point_val = xpow * ypow
        retval.append( point_val )

    retval = sum(retval)
    return retval

def averageDistance(center, inPoints):
    "Input: Point center, List inPoints.  Returns the average abs distance of a set of points from a specified point"

    distSum = 0.0

    for pt in inPoints:
        distSum += vectorLength(pt.X - center.X, pt.Y - center.Y)

    return distSum / len(inPoints)

def sliceByLength(inPoints, lengthBegin, lengthEnd):
    "Input: List inPoints; double lengthBegin, lengthEnd - values between 0.0 and 1.0.  Returns the (closest) slice of the set of points based on the starting percentages given by length Begin & End.  Doesn't create points"
    
    if len(inPoints) < 2:
        print "Warning: Trying to get a slice of a stroke with less than two points."
        return inPoints
    
    lengthDiff = lengthEnd - lengthBegin
    
    
    
        
    if lengthBegin < 0.0:
        lengthBegin = 0.0
    
    if lengthEnd > 1.0:
        lengthEnd = 1.0
        
    if( lengthEnd < lengthBegin ):
        temp = lengthEnd;
        lengthEnd = lengthBegin
        lengthBegin = temp
        
    newPoints = []
    
#    if lengthBegin == 0:
#        newPoints.append( inPoints[0] )
        
    currentLength = 0.0
    totalLength = 0.0
    
    for i in range(0, len(inPoints) - 1):
        cur = inPoints[i]
        nxt = inPoints[i + 1]
        
        totalLength += vectorLength(nxt.X - cur.X, nxt.Y - cur.Y)
        
    beginThreshold = totalLength * lengthBegin
    endThreshold = totalLength * lengthEnd
    
    for i in range(0, len(inPoints) - 1):
        cur = inPoints[i]
        nxt = inPoints[i + 1]
        
        segmentLength = vectorLength(nxt.X - cur.X, nxt.Y - cur.Y)
        curAndSegmentLength = currentLength + segmentLength
        
        if( (currentLength < beginThreshold) and (curAndSegmentLength >= beginThreshold) ):
            newPoints.append(cur)   #Adds the point just before the Threshold
        elif( currentLength > beginThreshold and currentLength < endThreshold ):
            newPoints.append(cur)   #Adds points inside the bounds
            
        if( (currentLength < endThreshold) and (curAndSegmentLength >= endThreshold) ):
            newPoints.append(nxt)   #Adds the point just outside the threshold
            break   #Passed end threshold, no need to keep going
            
        currentLength = curAndSegmentLength
        
    return newPoints
    
  

def _smooth(inPoints, width = 1, preserveEnds = False):
    "Input: List inPoints.  returns a smoothed set of the same size using Laplacian smoothing...IN 2D!."

    if len(inPoints) < 3:
        logger.debug("trying to smooth less than three points")
        return inPoints
    newPoints = []

    #Double the amount of points, and then smooth that.
    for i in range(0, len(inPoints) - 1):
        cur = inPoints[i]
        nxt = inPoints[i + 1]
        newPoints.append(cur)

        avgpt = Point((cur.X + nxt.X) / 2.0, (cur.Y + nxt.Y) / 2.0, (cur.T + nxt.T) / 2.0)
        newPoints.append(avgpt)

    newPoints.append(inPoints[len(inPoints) - 1]) #add the last point into the list, but do NOT add in a point between the first & last.
    #TODO: Maybe instead of disregarding it, check to see if stroke is a closedAnno, and if so, smooth between beginning and end?

    #Decision time: Smooth and modify both new and old points, or old points only?  Currently does both
    finalPoints = []
    #finalPoints.append(newPoints[0]) # First Point remains unchanged... See above TODO to possibly contradict this statement

    #new and old point smoothing
    for i in range(len(newPoints)):
        pointRange = range( max(0, i - width), min (len(newPoints), i + 1 + width) )  #Average over a range
        pointListX = [newPoints[j].X for j in pointRange]
        pointListY = [newPoints[j].Y for j in pointRange]
        pointListT = [newPoints[j].T for j in pointRange]
        if preserveEnds:
            while len(pointListX) < (2 * width + 1):
                pointListX.append(newPoints[i].X)
                pointListY.append(newPoints[i].Y)
                pointListT.append(newPoints[i].T)

        x = sum(pointListX) / float(len(pointListX))
        y = sum(pointListY) / float(len(pointListY))
        t = sum(pointListT) / float(len(pointListT))
        finalPoints.append( Point(x,y,t) )

    #finalPoints.append(newPoints[len(newPoints) - 1]) #As with first point remaining unchanged...
    return finalPoints


def perimeter(inPoints):
    "Input: List inPoints.  returns the perimeter of the input set of points."

    if len(inPoints) < 3:
        print("Warning: trying to get the perimeter of less than three points")
        return 0

    perim = 0.0
    for i in range(0, len(inPoints) - 1):
        cur = inPoints[i]
        nxt = inPoints[i + 1]

        perim += vectorLength(cur.X - nxt.X, cur.Y - nxt.Y)

    #We should NOT add in the last point with the first point, we don't need to connect them Because we're not taking the convex hull; we may not be drawing a polygon
    #Ignore the Above, because when calculating the area, we assume it IS a polygon.. SO.. we should take the convex hull
    perim += vectorLength(inPoints[len(inPoints) - 1].X - inPoints[0].X, inPoints[len(inPoints) - 1].Y - inPoints[0].Y)

    return perim


def ellipseAxisRatio(inStroke):
    "Input: List inPoints.  Returns the Ellipse Axis Ratio from  [0,1] of a set of points.  Calculates the ratio between the two axis of an approximating ellipse to calculate the lineness of a set of points."
    #How do we handle a single-point stroke?
    inPoints = inStroke.Points

    if (inStroke.length() == 0):
        logger.warn("Ellipse axis ratio of a 0-length stroke")
        return None
    if (len(inPoints) == 2 and inPoints[0].X != inPoints[1].X and inPoints[0].Y != inPoints[1].Y):  # It's a line if there's only two points
        return 1

    alpha = 0.0
    beta = 0.0

    cen = centroid(inStroke.Points)

    moment11 = momentOfOrder(cen, inPoints, 1, 1)
    moment20 = momentOfOrder(cen, inPoints, 2, 0)
    moment02 = momentOfOrder(cen, inPoints, 0, 2)
    moment00 = len(inPoints) #MomentOfOrder(  cen, inPoints, 0, 0 )

    #How does EllipseAxisRatio compare with Eccentricity and compactness as given by Csetverikov?

    try:    
        dsc = math.pow(moment20 - moment02, 2) + 4 * math.pow(moment11, 2)
        dsc = math.sqrt(dsc)
        alpha = (2 * (moment20 + moment02 + dsc)) / moment00
        alpha = math.sqrt(alpha)
        beta = (2 * (moment20 + moment02 - dsc)) / moment00
        beta = math.sqrt(beta)
        return 1 - beta / alpha
    except Exception as e:
        logger.error("Ellipse AxisRatio failing: \n%s" % e)
        fp = open("ERRORS.txt", "w")
        print >> fp, "#Stroke"
        for pt in inPoints:
            print >> fp, "%s %s %s" % (pt.X, pt.Y, pt.T)
        print >> fp, "#ENDStroke"
        fp.close()
        #exit(1)    
        return 1.0

def sign(number): #So argh that python doesn't have one of these built in
    "Input: int/double number.  Returns the sign of the input as either -1, 0 or 1."
    return cmp(number, 0)

def lineLength(inStroke):
    "Input: List inPoints.  Returns the length of a set of points along the line in which the set of points is determined to resemble."
    cen = inStroke.Center
    ang = _angleOfOrientation(inStroke)

    orientX = math.cos(ang)
    orientY = math.sin(ang)

    #Normalize the orientation
    orientMag = vectorLength(orientX, orientY)
    orientX = orientX / orientMag
    orientY = orientY / orientMag

    max = 0.0
    min = 0.0

    for pt in inPoints:
        vX = pt.X - cen.X
        vY = pt.Y - cen.Y

        dot = vectorDot(vX, vY, orientX, orientY)

        if dot > max:
            max = dot
        elif dot < min:
            min = dot


    return max - min


def linePointsTowards(linept1, linept2, target, radius):
    "Tests whether a line points toward a target or not"
    retValue = False
    slope = lineSlope(linept1, linept2)
    dir_mult = 1
    if (slope != None and linept2.X - linept1.X < 0) or (slope == None and linept2.Y - linept1.Y < 0):
        dir_mult = -1

    pt1 = target
    if slope == 0:
        pt2 = Point(target.X, target.Y + 10 )
    else:
        if slope == None:
            perp_slope = 0.0
        else:
            perp_slope = -1 / float(slope)
        pt2 = Point(target.X + 10, target.Y + (10 * perp_slope))
    line1 = (linept1, linept2)
    line2 = (target, pt2)
    tangentPoint = getLinesIntersection(line1, line2, infinite1 = True, infinite2 = True)


    if tangentPoint != None:
        line1dist = pointDistanceSquared(linept1.X, linept1.Y, tangentPoint.X, tangentPoint.Y)
        line2dist = pointDistanceSquared(linept2.X, linept2.Y, tangentPoint.X, tangentPoint.Y)
        distSqr =  pointDistanceSquared(target.X, target.Y, tangentPoint.X, tangentPoint.Y)
        if distSqr < radius ** 2 and line2dist < line1dist: #Points close enough and the right direction
            retValue = True

    return retValue
        


    
def pointDistanceFromLine(point, lineseg):
    """Returns the Euclidean distance of the point from an infinite line formed by extending the lineseg.
    point: Point object
    lineseg: tuple( Point, Point) making up a linesegment
    """

    assert len(lineseg) == 2, "pointDistanceFromLine called with malformed line segment"
    ep1 = lineseg[0]
    ep2 = lineseg[1]

    assert ep1.X != ep2.X or ep1.Y != ep2.Y, "pointDistanceFromLine called with 0-length line segment"
    if ep1.X == ep2.X: #Vertical line segment
        return math.abs(point.X - ep1.X)
    elif ep1.Y == ep2.Y:
        return math.abs(point.Y - ep1.Y)
    else:
        inv_slope = - (ep1.X - ep2.X) / float(ep1.Y - ep2.Y) #Perpendicular slope!
        point2 = Point( point.X + 10, point.Y + (inv_slope * 10) )
        distancePoint = getLinesIntersection(lineseg, (point, point2), infinite1 = True, infinite2 = True)

        return pointDistance(point, distancePoint)
        
        

#With respect to the horizontal.  0 deg == horizontal line
def angleOfOrientation(inStroke):
    logger.warning("angleOfOrientation is deprecated, use strokeOrientation")
    return _angleOfOrientation(inStroke)

#With respect to the horizontal.  0 deg == horizontal line
def _angleOfOrientation(inStroke):
    "Input: List inPoints.  Returns in radians the Angle of Orientation of a set of points to be interpreted as a line with respect to the horizontal axis"
    cen = inStroke.Center
    inPoints = inStroke.Points
    pArea = area(inPoints)

    if (len(inPoints) <= 1):
        print "Warning: trying to get the Angle of Orientation of one or fewer points."
        return 0.0

    #Perfect line        
    if pArea == 0:
        #Corner case of a single point. Weird behavior?
        orientX = inPoints[len(inPoints) - 1].X - inPoints[0].X
        orientY = inPoints[len(inPoints) - 1].Y - inPoints[0].Y

        orientMag = vectorLength(orientX, orientY)
        if orientMag == 0:
            return 0.0
        orientX = orientX / orientMag
        orientY = orientY / orientMag

        #dot = 1*orientX + 0*orientY

        return math.acos(orientX)


    moment11 = momentOfOrder(cen, inPoints, 1, 1)

    if moment11 == 0:
        return 0    #There is no Moment of order 1,1.  We'd get a divide by zero.  Orientation is undefined; just return zero.

    angle = (.5 * math.atan((momentOfOrder(cen, inPoints, 0, 2) - momentOfOrder(cen, inPoints, 2, 0)) / (2 * moment11))) + sign(moment11) * math.pi / 4

    return angle


def _TurnType(A, B, C):
    "Input: Points A, B, C.  Returns the type of turn from A -> B."
    z = (B.X - A.X) * (C.Y - A.Y) - (C.X - A.X) * (B.Y - A.Y)

    if z > 0:
        return "Left"
    elif z < 0:
        return "Right"
    else:
        return "Collinear"


def convexHull(inPoints):
    "Input:  Set of Points as a polygon/line.  Returns a set of ordered points defined as the Convex Hull using Grahms Scan"
    pts = list(set(inPoints)) # Remove duplicates
    if len(pts) < 3:
        print("Warning: Trying to get the hull of less than 3 points")
        return inPoints

    A = pts[0]

    #Find upperleftmost point, with leftness taking priority
    for pt in inPoints:
        if pt.X < A.X or (pt.X == A.X and pt.Y < A.Y):
            A = pt


    comparer = _PointComparer(A)
    pts.sort(comparer.Compare)
    newPoints = []
    newPoints.append(A)   #The upperleft most point
    currentPt = pts[1]  #The 2nd point
    j = 2

    while j < len(pts):
        turnType = _TurnType(newPoints[len(newPoints) - 1], currentPt, pts[j])
        if turnType == "Right":
            currentPt = newPoints.pop()
        else:
            newPoints.append(currentPt)
            currentPt = pts[j]
            j = j + 1

    if (_TurnType(newPoints[len(newPoints) - 1], currentPt, A) != "Right"):
        newPoints.append(currentPt)

    return newPoints

def centroid(inPoints):
    "Input: List inPoints.  Returns a Point of the center of Mass (assuming uniform density) of the convex hull of a polygon/line."
    inPoints = convexHull(inPoints)

    xCoord = 0.0
    yCoord = 0.0

    currentPoint = None
    nextPoint = None

    for i in range(0, len(inPoints)):
        currentPoint = inPoints[i]
        nextPoint = inPoints[(i + 1) % len(inPoints)]

        secondFactor = currentPoint.X * nextPoint.Y - nextPoint.X * currentPoint.Y
        xCoord = xCoord + (currentPoint.X + nextPoint.X) * secondFactor
        yCoord = yCoord + (currentPoint.Y + nextPoint.Y) * secondFactor

    pArea = area(inPoints)

    if pArea == 0:  #if the area is zero, it's a perfect line.  The center would be the center of the first and last points
        return Point((inPoints[0].X + inPoints[len(inPoints) - 1].X) / 2.0, (inPoints[0].Y + inPoints[len(inPoints) - 1].Y) / 2.0)

    xCoord = (xCoord / 6.0) / pArea
    yCoord = (yCoord / 6.0) / pArea

    if xCoord < 0:
        xCoord = -xCoord
        yCoord = -yCoord
    return Point(xCoord, yCoord)



def area(inPoints):
    "Input: List inPoints.  Returns a double of the area of the set of points.  If Area is zero, also indicates perfect line."
    #print "Using GeomUtils.area... Not sure it actually does what it says..."
    curArea = 0.0
    currentPoint = None
    nextPoint = None

    for i in range(0, len(inPoints)):
        currentPoint = inPoints[i]
        nextPoint = inPoints[(i + 1) % len(inPoints)]
        curArea = curArea + (nextPoint.X - currentPoint.X) * (nextPoint.Y + currentPoint.Y)

    curArea = curArea / 2
    if curArea < 0:
        curArea = curArea * -1
    return curArea

def pointInPolygon( inPoints, point ):
    "Input: List inPoints, Point point.  Returns true if the point is inside the Polygon.  Assumptions: List of points describes a CLOSED polygon.  Open polygons will be treated as if first & last point interconnect.  TODO:  Improve support for strokes with tails."
    
    rayEndPt = Point( sys.maxint, point.Y ) #A ray extending as far as possible to the right , max X coord.
    
    currentPoint = None
    nextPoint = None
    
    allCrossPts = set()
    for i in range(0, len(inPoints)):
        
        currentPoint = inPoints[i]
        nextPoint = inPoints[(i + 1) % len(inPoints)]
        
        crossPt = getLinesIntersection( (point, rayEndPt), (currentPoint, nextPoint) )
        if crossPt != None:
            allCrossPts.add( (crossPt.X, crossPt.Y) )
            
    logger.debug("pointInPolygon: %s intersections: %s" % (str(len(allCrossPts)), allCrossPts))
    
    return ( (len(allCrossPts) % 2) !=0)    #If the ray passes through an ODD number of points, then it's inside the polygon.


                

            



def getLinesIntersection(line1, line2, infinite1 = False, infinite2 = False):
    "Input: two lines specified as 2-tuples of points. Returns the intersection point of two lines or None."
    p1, p2 = line1
    q1, q2 = line2
    
    if p1.X > p2.X:
        p1, p2 = p2, p1
    if q1.X > q2.X:
        q1, q2 = q2, q1   
    
    #is p __ than q
    isHigher = p1.Y > q1.Y and p2.Y > q2.Y and p1.Y > q2.Y and p2.Y > q1.Y
    isLower = p1.Y < q1.Y and p2.Y < q2.Y and p1.Y < q2.Y and p2.Y < q1.Y
    isLeft= p2.X < q1.X
    isRight= p1.X > q2.X
    
    if (isHigher or isLower or isLeft or isRight) and not infinite1 and not infinite2:
        return None
    else:
        pA = p2.Y - p1.Y
        pB = p1.X - p2.X
        pC = pA*p1.X + pB*p1.Y
       
        qA = q2.Y - q1.Y
        qB = q1.X - q2.X
        qC = qA*q1.X + qB*q1.Y
        
        det = pA*qB - qA*pB
        if det == 0.0:
            return None #Parallel
        ret_x = (qB*pC - pB*qC) / float(det)
        ret_y = (pA*qC - qA*pC) / float(det)
        
        xpoint = Point(ret_x, ret_y)
        
        
        if not infinite1:
            line1_bb = strokelistBoundingBox([Stroke(points = list(line1))]) #Create a bounding box for this line
            if not pointInBox(xpoint, line1_bb[0], line1_bb[1]):
                return None
        if not infinite2:
            line2_bb = strokelistBoundingBox([Stroke(points = list(line2))])
            if not pointInBox(xpoint, line2_bb[0], line2_bb[1]):
                return None
        
        return xpoint
    
def linesIntersect(p1, p2, q1, q2):
    "Returns true if lines intersect, else false. getLinesIntersection returns the actual point"
    if getLinesIntersection((p1, p2) , (q1, q2)) is not None:
        return True
    return False
    

def lineSlope(p1, p2):
    "Returns the slope of a line formed from points p1 to p2. Returns None if slope is infinite or points are the same."
    if p1.X == p2.X and p1.Y == p2.Y:
        return None
    run = p2.X - p1.X
    if run == 0.0:
        return None
    return (p2.Y - p1.Y) / run
    
class _PointComparer:
    "Comparer used to compare and sort points based on their TurnType"
    def __init__(self, pointA):
        self.A = pointA

    def Compare(self, P, Q):
        if P == Q:
            return 0

        if P == self.A:
            return - 1
        elif Q == self.A:
            return 1

        turnType = _TurnType(self.A, P, Q)

        if turnType == "Right":
            return 1
        elif turnType == "Left":
            return - 1
        else:
            V1 = vectorLengthSquared(P.X - self.A.X, P.Y - self.A.Y)
            V2 = vectorLengthSquared(Q.X - self.A.X, Q.Y - self.A.Y)
            return cmp(V1, V2)

#-------------------------------------
# if executed by itself, run all the doc tests

if __name__ == "__main__":
    Logger.setDoctest(logger) 
    import doctest
    doctest.testmod()

