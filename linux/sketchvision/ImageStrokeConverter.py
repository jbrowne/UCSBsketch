#!/usr/bin/env python
if __name__ == "__main__":
    import sys
    sys.path.append("../")
"""
filename: ImageStrokeConverter.py

Description:
This module handles the extraction of strokes (ordered path of points) from a photo of a whiteboard.
First, the photo is processed to separate the background from the strokes.
Then the strokes are thresholded, and thinned to reduce each stroke to a single pixel-wide blob of points.
Then the points are grouped and ordered into strokes. Currently, strokes are separated at intersections.

Todo:
* Better thinning (maybe guided by stroke thickness)
* Faster Thinning
* Handle blackboards as well as whiteboards
* Isolate the board area from a wide photo.
* Make it more object oriented

"""
from SketchFramework.Stroke import Stroke
from Utils import Logger
from Utils.GeomUtils import getLinesIntersection
from Utils.ImageUtils import saveimg
import Image
import StringIO
import cv
import datetime
import math
import os
import pdb
import pickle
import random
import time


    

log = Logger.getLogger("ISC", Logger.DEBUG)

#Random, but consistent
random.seed("sketchvision")


DEBUG = False

ISBLACKBOARD = True

BLACK = 0
WHITE = 255
GRAY = 200

FILLEDVAL = GRAY
CENTERVAL = BLACK
BGVAL = WHITE
OOBVAL = -1

COLORFACTOR = 10

DENOISE_K = 5
SMOOTH_K = 23
INV_FACTOR = 0.5
INK_THRESH = 122

PRUNING_ERROR = 0.2
SQUARE_ERROR = 0.2
PRUNING_ERROR = PRUNING_ERROR * SQUARE_ERROR

CACHE = None

NORMWIDTH = 1280
#NORMWIDTH = 2592
#NORMWIDTH = 600
DEBUGSCALE = 1
DEBUGIMG = None
#***************************************************
# Intended module interface functions 
#***************************************************

def cvimgToStrokes(in_img, targetWidth = None):
    "External interface to take in an OpenCV image object and return a list of the strokes."
    global DEBUG, CACHE
    CACHE = {}
    DEBUG = True
    if DEBUG:
        saveimg(in_img, name="Raw_ink_image")
    saveimg(in_img, outdir="./photos/", 
            filename=datetime.datetime.now().strftime("%F-%T"+".jpg"))
    small_img = resizeImage(in_img, targetWidth=targetWidth)
    #small_img = in_img
    saveimg(small_img, name="Resized")
    temp_img, _ = removeBackground(small_img)
    #temp_img = cv.CreateMat(small_img.rows, small_img.cols, cv.CV_8UC1)
    #cv.CvtColor(small_img, temp_img, cv.CV_RGB2GRAY)
    #cv.AdaptiveThreshold(temp_img, temp_img, 255, blockSize=39)
    strokelist = blobsToStrokes(temp_img)
    DEBUG = False
    if DEBUG:
        prettyPrintStrokes(temp_img, strokelist)
    #saveimg(in_img, outdir="./photos/", name=datetime.datetime.now().strftime("%F-%T"+".jpg"))
    return {"strokes": strokelist, "dims" : (small_img.cols, small_img.rows)}

def loadImageBuf(data):
    """Convert a PIL image buffer to the image expected by cvimgtoStrokes"""
    pil_img = Image.open(StringIO.StringIO(data))
    cv_img = cv.CreateImageHeader(pil_img.size, cv.IPL_DEPTH_8U, 3)
    cv.SetData(cv_img, pil_img.tostring())
    cv_mat = cv.GetMat(cv_img)
    #cv.CvtColor(cv_img, cv_img, cv.CV_BGR2RGB)
    return cv_mat
    
def imageBufferToStrokes(data):
    "External interface to take in a PIL image buffer object and return a list of the strokes."
    log.debug( "imageBufferToStrokes(..)" )
    log.debug( "DEPRECATED! Use cvimgToStrokes(loadImageBuf(data))" )
    return cvimgToStrokes(loadImageBuf(data))
    
def loadFile(filename):
    """Load an image from a filename and return the image object"""
    return cv.LoadImageM(filename)

def imageToStrokes(filename):
    "External interface to take in a filename for an image and return a list of the strokes."
    log.debug( "imageToStrokes(..)" )
    log.debug( "DEPRECATED! Use cvimgToStrokes(loadFile(filename))" )
    #in_img = cv.LoadImageM(filename)
    return cvimgToStrokes(loadFile(filename))

#***************************************************
# Random Utility Functions
#***************************************************

def interiorAngle(P1, P2, P3):
    "Input: three points. Returns the interior angle (radians) of the three points with P2 at the center"
    X1 = P1[0]
    Y1 = P1[1]
    X2 = P2[0]
    Y2 = P2[1]
    X3 = P3[0]
    Y3 = P3[1]
    a_len = pointDist(P1, P2)
    b_len = pointDist(P2, P3)
    c_len = pointDist(P1, P3)
    a = math.sqrt(a_len)
    b = math.sqrt(b_len)
    c = math.sqrt(c_len)
    #make more explicit
    try:
        angle = a_len + b_len - c_len
        angle = angle / (2 * a * b)
        angle = math.acos(angle)
    except (ZeroDivisionError, ValueError):
        #log.debug( "A, B, C:", angle, "=", a_len, b_len, c_len, a, b )
        angle = math.pi
    return angle * 180 / math.pi

def GETNORMWIDTH():
    "Return the module's NORMWIDTH attribute"
    global NORMWIDTH
    return int(NORMWIDTH)

class Timer (object):
    "A handler that allows for timing of functionality."
    def __init__(self, desc = "Timer"):
        self.start = time.time()
        self.desc = desc
        self.laps = 0
        self.laptime = self.start
        def lap(self, desc = ""):
            now = time.time()
            log.debug( "%s - %s: %s ms, %s ms" % (self.desc, desc, 1000 * (now - self.laptime), 1000 * (now - self.start)) )
            self.laptime = now


def printPoint(pt, img):
    "Prints the 8-neighborhood around a point in a pretty fashion"
    global CENTERVAL
    px, py = pt
    
    nw = getImgVal(px-1, py+1, img) == CENTERVAL
    n = getImgVal(px, py+1, img) == CENTERVAL
    ne = getImgVal(px+1, py+1, img) == CENTERVAL
    
    w = getImgVal(px-1, py, img) == CENTERVAL
    pixval = getImgVal(px, py, img) == CENTERVAL
    e = getImgVal(px+1, py, img) == CENTERVAL
    
    sw = getImgVal(px-1, py-1, img) == CENTERVAL
    s = getImgVal(px, py-1, img) == CENTERVAL
    se = getImgVal(px+1, py-1, img) == CENTERVAL
    
    chars = (' ', '#')
    print "--------------------------"
    for row in [ [nw, n, ne], [w, pixval, e], [sw, s, se] ]:
        print "\t|",
        for val in row:
            print "%s" % (chars[int(val)]),
        print "|"
    print "--------------------------"

def thicknessAtPoint(point, img):
    """Determine the thickness at a point in img. Uses an expanding circle
    from that pixel until it encounters non-ink.
    Returns the minimum thickness as twice that radius + 1"""
    global BGVAL, FILLEDVAL, CENTERVAL, OOBVAL, CACHE
    #Load the cached value
    cacheTag = "Thickness%s%s" % (str(point), str(img))
    thickness = CACHE.get(cacheTag, None)
    if thickness is None:
        px, py = point
        pixval = getImgVal(px, py, img)
        errorThresh = 0.50 #Allow at most X percent white pixels while expanding
        
        startRad = None
        endRad = None
        if pixval == BGVAL or pixval == OOBVAL:
            thickness = 0
        else:
            rad = 1
            #Phase 1: Double radius until too much error
            while rad < img.rows:
                cPixels = circlePixels(point, rad)
                numBGpix = 0
                allowableError = errorThresh * len(cPixels)
                for p in cPixels:
                    pixval = getImgVal(p[0], p[1], img)
                    if pixval == BGVAL or pixval == OOBVAL:
                        numBGpix += 1

                if startRad == None and numBGpix > 0:
                    endRad = startRad = rad - 1
                if numBGpix > allowableError:
                    endRad = rad - 1
                    break
                rad *= 2
            thickness =(startRad + endRad) 
        CACHE[cacheTag] = thickness
    
    return thickness

def circlePixels(center, rad):
    """Generates a list of pixels that lie on a circle, centered at center,
    with radius rad. Unordered."""
    x, y = center
    rad = int(rad)
    rad_sqr = rad * rad
    points = set()
    if rad == 0:
        return [center]
    dy = 0
    prevDx = rad + 1
    while dy <= rad:
        curDx = int(math.sqrt(rad_sqr - dy **2 ) + 0.5)
        dx = curDx
        while dx <= prevDx:
        #points.update( [ (x+dx, y+dy), (x-dx, y+dy), (x+dx, y-dy), (x-dx, y-dy)])
            points.add( (x+dx, y+dy) )
            points.add( (x-dx, y+dy) )
            points.add( (x+dx, y-dy) )
            points.add( (x-dx, y-dy) )
            dx += 1
        prevDx = curDx
        dy += 1
    return points


      


def linePixels(pt1, pt2):
    """Generates a list of pixels on a line drawn between pt1 and pt2"""
    left, right = sorted([pt1, pt2], key = lambda pt: pt[0])
    
    deltax = right[0] - left[0]
    deltay = right[1] - left[1]
    
    if deltax != 0:
        slope = deltay / float(deltax)
        y = left[1]
        error = 0.0
        for x in xrange(int(left[0]), int(right[0]) + 1):
            if error > -0.5 and error < 0.5:
                yield (x,y)
            while error >= 0.5:
                y += 1
                error -= 1.0
                yield (x,y)
            while error <= -0.5:
                y -= 1
                error += 1.0
                yield (x,y)
            error += slope
    else:
        bottom, top = sorted([pt1, pt2], key = lambda pt: pt[1])
        for y in xrange(int(bottom[1]), int(top[1]) + 1):
            yield (left[0], y)


def drawLine(pt1, pt2, color, img):
    """Draw a line from pt1 to pt2 in image img"""
    h = img.rows
    w = img.cols
    for x,y in linePixels(pt1, pt2):
        if y >= 0 and y < h and x >= 0 and x < w:
            setImgVal(x,y,color,img)


def pointsOverlap(pt1, pt2, img, pt1Thickness = None, pt2Thickness = None, checkSeparation=True):
    """Checks to see if two points cover each other with their thickness and are not separatred by white"""
    global CENTERVAL
    assert (pt1Thickness != None and pt2Thickness != None) or img != None, "Error, cannot determine overlap without thickness!"
    okSeparation = 0 #How many pixels can be invalid in the separation check
    distSqr = pointsDistSquared(pt1, pt2) 
    
    if pt1Thickness != None and pt2Thickness != None:
        pt1ThicknessSqr = ((pt1Thickness - 1)/2.0) ** 2
        pt2ThicknessSqr = ((pt2Thickness - 1) /2.0) ** 2
    else:
        pt1ThicknessSqr = ((thicknessAtPoint(pt1, img) -1) / 2.0) ** 2
        pt2ThicknessSqr = ((thicknessAtPoint(pt2, img) -1) / 2.0) ** 2
       
    if distSqr > pt2ThicknessSqr and distSqr > pt1ThicknessSqr: #If neither thickness covers the other point
        return False
    
    if checkSeparation:
        separation = 0
        for x,y in linePixels(pt1, pt2):
            if getImgVal(x,y,img) != CENTERVAL:
                if separation < okSeparation - 1:
                    separation += 1
                else:
                    return False
              
    return True


def getEightNeighbors(pt, shuffle = False):
    """Given a point, return a list of its eight neighboring pixels, possibly shuffled. No bounds checking!"""
    x,y = pt
    n = (x , y + 1)
    s = (x , y - 1)
    e = (x + 1 , y)
    w = (x - 1 , y)
    ne = (x + 1 , y + 1)
    se = (x + 1 , y - 1)
    nw = (x - 1 , y + 1)
    sw = (x - 1 , y - 1)
    retList = [ne, n, nw, w, sw, s, se, e]
    if shuffle:
        random.shuffle(retList)
    return retList

def pointsDistSquared (pt1, pt2):
    x1, y1 = pt1
    x2, y2 = pt2

    return (x1 - x2) ** 2 + (y1 - y2) ** 2

#***************************************************
# Bitmap thinning functions
#***************************************************

def _squareIntersections(graphDict, rawImg):
    """Take in a graph of {<point> : {'kids' : set(kidpts), 'thickness' : float} } 
    and the original, binary image of strokes and 
    fix errors on intersections introduced by thinnning, 
    producing more 'square' intersections.
    
    Uses trajectory of strokes upon entering 'intersection region' 
    to determine a better crossing point for those strokes."""
    keyPointsList = getKeyPoints(graphDict) #List of keypoint dictionaries, one dict per "blob"

    removedPoints = set()
    newPoints = {} #To be filled with <point> : {'kids' : set(), 'thickness': float}

    # Look at all the points where edges intersect
    for kpDict in keyPointsList:
        for cp in kpDict['crosspoints']:
            cpDict = {'kids' : set(), 'thickness': None}
            #Generate a list of edges, ordered such that crosspoint is at edge[0]
            edgeList = [] 
            for edge in kpDict['edges']:
                if edge[0] == cp:
                    edgeList.append(list(edge))
                elif edge[-1] == cp:
                    edgeList.append(list(reversed(edge)))

            cpThickness = graphDict[cp]['thickness']
            #log.debug( "CrossPoint %s, thickness %s" % (str(cp), cpThickness/ 2.0) )
            #Remove points from the edges such that they do not enter the "crossing region"
            for edge in edgeList:
                #log.debug( " *Edge:", edge )
                for pt in list(edge):
                    if len(edge) > 1 and \
                       pointsOverlap(cp, pt, rawImg, \
                                     pt1Thickness = cpThickness, \
                                     pt2Thickness = 1, checkSeparation = False):
                        #log.debug( "  Remove %s" % (str(pt)) )
                        edge.remove(pt)
                        removedPoints.add(pt)
                    else:   
                        break

            #Generate a new intersection point and connect the edges to it
            dirSegments = [] #line segments (tuple (pt1, pt2)) for the representative direction of the edge
            for edge in edgeList:
                cpDict['kids'].add(edge[0]) #Connect the edge to the new cross point
                if len(edge) > 1: #Otherwise ignore its trajectory
                    centerPt = ( (edge[0][0] + cp[0]) / 2.0, (edge[0][1] + cp[1]) / 2.0 ) #Point blending the end of the edge and the original crosspoint
                    #centerPt = edge[0]
                    seg = (centerPt, edge[:3][-1]) #Hack to get the endpoint at most 3 away
                    dirSegments.append(seg)

            #log.debug( "Generated %s edge segments" % (len(dirSegments)) )
            #Get the pairwise intersections for all segments
            allCrossPointsX = []
            allCrossPointsY = []
            allIntersects = []

            for i in range(len(dirSegments)):
                for j in range(i + 1, len(dirSegments)):
                    line1 = dirSegments[i]
                    line2 = dirSegments[j]
                    cross = getLinesIntersection(line1, line2)
                    if cross is not None:
                        x,y = cross
                        allIntersects.append( (x,y))
                        allCrossPointsY.append(y)
                        allCrossPointsX.append(x)

            if len(allCrossPointsX) > 0 :
                #The new crossing point has the median X and median Y coords of those intersections
                allCrossPointsX.sort()
                allCrossPointsY.sort()
                medianIdx = len(allCrossPointsY) / 2
                newCrossPoint = (int(allCrossPointsX[medianIdx]), int(allCrossPointsY[medianIdx]))

                #log.debug( " Intersections: %s\n * New median point %s" % (allIntersects, str(newCrossPoint)) )
                #newCrossPoint = (int(sum(allCrossPointsX) / len(allCrossPointsX)), \
                #int(sum(allCrossPointsY) / len(allCrossPointsY)) )
            else:
                #log.debug( " Intersections empty, reverting to old CP" )
                newCrossPoint = cp

            cpDict['thickness'] = thicknessAtPoint(newCrossPoint, rawImg)
            newPoints[newCrossPoint] = cpDict

    for pt in removedPoints:
        _deletePointFromGraph(pt, graphDict)
    for pt , ptDict in newPoints.items():
        _insertPointIntoGraph(pt,ptDict, graphDict) 

def _deletePointFromGraph(point, graphDict):
    """Given a point and a graphdict, delete the point from the graph, and also remove
    any references from its children"""
    if point in graphDict:
        ptDict = graphDict[point]
        for kpt in list(ptDict['kids']):
            if point in graphDict[kpt]['kids']: 
                graphDict[kpt]['kids'].remove(point)
        del(graphDict[point])

def _insertPointIntoGraph(point, pointDict, graphDict):
    """Given a point and its pointDict = {'kids' : set(), 'thickness' : float},
    insert and link the point into the graph.
    If the point is already in the graph, it is overwritten."""

    if point in graphDict:
        _deletePointFromGraph(point, graphDict)
    graphDict[point] = pointDict
    for kpt in list(pointDict['kids']):
        if kpt in graphDict:
            graphDict[kpt]['kids'].add(point)
        else:
            log.debug( "WARNING: Tried to insert point dictionary with invalid children" )
            pointDict['kids'].remove(kpt)


        


def getKeyPoints(graph):
    """Takes in a graph of points and returns a list of keypoint dictionaries.
    {'endpoints', 'crosspoints', 'edges'}"""
    retList = []
    graphCpy = dict(graph)
    while len(graphCpy) > 0:
        seed = graphCpy.keys()[0]
        procStack = [{'pt':seed, 'dist':0}]
        seen = set([])

        endPoints = set([])
        crossPoints = set([])
        while len(procStack) > 0:
            ptDict = procStack.pop()
            pt = ptDict['pt']
            dist = ptDict['dist']

            if pt in seen:
                continue


            if len(graphCpy[pt]['kids']) > 2:
                crossPoints.add(pt)
            elif len(graphCpy[pt]['kids']) <= 1:
                endPoints.add(pt)
            seen.add(pt)
            for nPt in graphCpy[pt]['kids']:
                if nPt in graphCpy and nPt not in seen:
                    procStack.append({'pt':nPt, 'dist': dist + 1})
            del(graphCpy[pt])
        retList.append({'seed': seed, 'endpoints' : endPoints, 'crosspoints' : crossPoints})

    _getGraphEdges(graph, retList) #Add the 'edges' field
    
    return retList

def _getGraphEdges(graph, keyPointsList):
    """Modifies keyPointsList, adding the edge information to each keypoint entry.
    * DOES NOT RETURN ANYTHING *"""
    for kpDict in keyPointsList:
        endPoints = kpDict['endpoints']
        crossPoints = kpDict['crosspoints']
        seedPoint = kpDict['seed']
        edges = kpDict['edges'] = [] #Create a new tag

        #Special case of single point stroke
        if len(graph[seedPoint]['kids']) == 0:
            edges.append([seedPoint])
            continue

        allKeyPts = set(list(endPoints) + list(crossPoints))
        if len(allKeyPts) == 0:
            #Just start the edge at the seed
            allKeyPts.add(seedPoint)

        #Walk the tree linking consecutive points via the edge.
        #  KeyPoints are used to determine start/end points of each edge
        procStack = [{'pt' : list(allKeyPts)[0], 'par' : None, 'edge' : []}]
        seen = set([])
        while len(procStack) > 0:
            ptDict = procStack.pop()
            pt = ptDict['pt']
            par = ptDict['par']
            curEdge = ptDict['edge']

            if pt in seen and pt not in allKeyPts:
                continue

            #Keypoint is starting an edge
            if par == None:
                assert pt in allKeyPts, "Point with no parent, not in keypoint list"
                seen.add(pt)
                for k in graph[pt]['kids']:
                    if k not in seen:
                        procStack.append( {'pt' : k, 'par' : pt, 'edge' : [pt]} )
            #All other keypoints should end an edge and might start a new one
            elif pt in allKeyPts:
                curEdge.append(pt)
                edges.append(curEdge)
                procStack.append( {'pt' : pt, 'par' : None, 'edge' : None} )
            #Otherwise just add it to the current edge and move down the line
            else:
                seen.add(pt)
                curEdge.append(pt)
                numKids = 0
                for k in graph[pt]['kids']:
                    if k != par:
                        procStack.append( {'pt': k, 'par' : pt, 'edge': curEdge} )
                        numKids += 1
                if numKids != 1:
                    log.debug( "Non-keypoint %s added too many/few kids: \n ptDict: %s\n graph[pt]: %s" % (str(pt), ptDict, graph[pt]) )
        #END while len(procStack) ...
    #END for keyPointList ...


def strokesFromSeed(seed, graph):
    """Create a dumb list of strokes from any blob in a graph"""
    retStrokes = []
    retStrokes.append( Stroke() )
    procStack = [{'pt': seed, 'stroke': retStrokes[0]}]
    seen = set([])
    while len(procStack) > 0:
        procDict = procStack.pop()
        pt = procDict['pt']
        stroke = procDict['stroke']

        if pt in seen:
            continue

        seen.add(pt)
        stroke.addPoint(pt)

        branchesTaken = 0
        for nPt in graph[pt]['kids']:
            if nPt not in seen:
                if branchesTaken > 0: #Create a new stroke for each branch
                    stroke = Stroke()
                    stroke.addPoint(pt)
                    retStrokes.append(stroke)
                procStack.append({'pt':nPt, 'stroke':stroke})
                branchesTaken += 1

    return retStrokes 
    

def drawGraph(graph, img):
    """Draw a graph in img"""
    keyPts = set()
    for p, pdict in graph.items():
        if len(pdict['kids']) != 2:
            keyPts.add(p)
        for k in pdict['kids']:
            drawLine(p,k,128,img)
    for p in keyPts:
        setImgVal(p[0], p[1], 220, img)
        

#***************************************************
# Top level processing functions (not helper utils)
#***************************************************    
def pointsToStrokes(pointSet, rawImg):
    """Converts a set() of point tuples into a list of strokes making up those
    points. Mostly glue behind the heavy lifter functions"""
    log.debug( "Generating point graph" )
    graph = pointsToGraph(pointSet, rawImg)
    log.debug( "Converting graph to strokes" )
    retStrokes = graphToStrokes(graph, rawImg)
    log.debug("Generated %d strokes" % (len(retStrokes)))
    return retStrokes


def pointsToGraph(pointSet, rawImg):
    """From a raw, binary image and approximate thinned points associated with it, 
    turn the thinned points into a bunch of trees.
    * Thinned strokes are trimmed according to line thickness for better results.
    * The graphs returned are trees, so closed cycles are split."""
    graphDict = {}
    allThicknesses = {}
    while len(pointSet) > 0:
        endPoints = set([]) #Keep track of all the endpoints
        #Initialize the tracing with an arbitrary seed points
        seed = pointSet.pop()
        pointSet.add(seed)
        path = [] #Maintain the current path we've been tracing (between branches/endpoints)
        procStack = [{'pt': seed, 'path': path}]
        ptsInStack = set([seed])
        
        unusedPaths = [path] #Tracks the paths that get trimmed (for adding back in end-tails)
        while len(procStack) > 0:
            #Set up the variables for the next point
            procDict = procStack.pop(0) #Breadth first
            pt = procDict['pt']
            ptsInStack.remove(pt)

            if pt not in pointSet:
                continue

            #Add this point to the currently traced path
            path = procDict['path']
            path.append(pt)

            #Which neighbors should we add?
            addNbors = []
            for nPt in getEightNeighbors(pt, shuffle = True):
                if nPt in pointSet and nPt not in ptsInStack:
                    addNbors.append(nPt)

            #Add this point as a "pivot" if it's the first, out of range of the
            #    last pivot, or if it is an intersection point. Add all intermediate
            #    pixels that got here from the last pivot node
            #NOTE: The trimming according to thickness happens implicitly by
            #    NOT adding those paths that are entirely within range of
            #    a pivot point
            if len(path) > 0:
                ptThick = allThicknesses.setdefault(pt, thicknessAtPoint(pt, rawImg))
                    
                #If it's the first point or follows an intersection
                if len(path) == 1:
                    ptDict = graphDict.setdefault(pt, {'kids': set([]),
                         'thickness': ptThick})
                #If it's out of range of the last pivot
                elif not pointsOverlap(path[0], pt, rawImg,
                                               pt1Thickness = allThicknesses.setdefault(path[0], thicknessAtPoint(path[0], rawImg)),
                                               pt2Thickness = ptThick) \
                                               or (len(addNbors) > 1): #Last case means intersection
                    unusedPaths.remove(path)
                    for idx in xrange(1,len(path)):
                        par = path[idx-1]
                        kid = path[idx]
                        parThick = allThicknesses.setdefault(par, thicknessAtPoint(par, rawImg))
                        parDict = graphDict.setdefault(par, {'kids': set([]), 'thickness':parThick})
                        kidThick = allThicknesses.setdefault(kid, thicknessAtPoint(kid, rawImg))
                        kidDict = graphDict.setdefault(kid, {'kids': set([]), 'thickness':kidThick})
                        parDict['kids'].add(kid)
                        kidDict['kids'].add(par)
                    path = [pt]
                    unusedPaths.append(path)

                #Add the proper neighbors to the stack with the correct path
                for i, nPt in enumerate(addNbors):
                    if i > 0:
                        path = list(path)
                        unusedPaths.append(path)
                    procStack.append({'pt':nPt, 'path': path})
                    ptsInStack.add(nPt)

            #Cleanup the node as processed
            pointSet.remove(pt)
        #endWhile len(procStack)    Done processing this blob.
        
        #*******************************************************
        #Thickness based pruning has trimmed off the endpoints. Add the pruned
        #  paths if they extend a current endpoint.
        #  Start by marking paths to be added in.
        #*******************************************************
        #Don't fix the unused paths that really should be removed
        usedEndpoints = set([])
        for upath in list(unusedPaths):
            head = upath[0]
            if (#len(upath) == 1 or  
                head in usedEndpoints or #We're already going to another endpoint extender 
                len(graphDict[head]['kids']) != 1): #Head is not an endpoint
                unusedPaths.remove(upath)
            else:
                usedEndpoints.add(head)

        #Actually add in the extending paths
        for upath in unusedPaths:
            log.debug( "Adding back in a trimmed path" )
            head = upath[0]
            for idx in xrange(1,len(upath)):
                par = upath[idx-1]
                kid = upath[idx]
                parDict = graphDict.setdefault(par, {'kids': set([]), 'thickness':thicknessAtPoint(par,rawImg)})
                kidDict = graphDict.setdefault(kid, {'kids': set([]), 'thickness':thicknessAtPoint(par,rawImg)})
                parDict['kids'].add(kid)
                kidDict['kids'].add(par)

        #Handle two-point lines
        for ep in list(endPoints):
            for nPt in getEightNeighbors(nPt):
                if nPt in endPoints:
                    graphDict[ep]['kids'].add(nPt)
                    graphDict[nPt]['kids'].add(ep)
                    
    #endWhile len(pointSet)     Done processing all blobs in the image

    endPoints = set([])
    for pt, pdict in graphDict.items():
        if len(pdict['kids']) == 1:
            endPoints.add(pt)

    #Link back together broken cycles
    for ep in endPoints:
        for nPt in getEightNeighbors(ep):
            if nPt in endPoints:
                graphDict[ep]['kids'].add(nPt)
                graphDict[nPt]['kids'].add(ep)

    log.debug( "Before collapsing, graphdict: %s" % (len(graphDict)) )

    _collapseIntersections(graphDict, rawImg)
    log.debug( "After collapsing, graphdict: %s" % (len(graphDict)) )

    _squareIntersections(graphDict, rawImg)
    log.debug( "After squaring, graphdict: %s" % (len(graphDict)) )

    return graphDict

def _collapseIntersections(graph, rawImg):
    """Given a graph dictionary and a keypoints list (with edge info),
    Collapse overlapping crossing points into one intersection. """
    keyPointsList = getKeyPoints(graph)
    for kpDict in keyPointsList:
        mergeDict = {}
        crossPoints = list(kpDict['crosspoints'])
        #Compare each pair of crossing points
        for i in range(len(crossPoints)):
            cp1 = crossPoints[i]
            p1Thick = graph[cp1]['thickness']
            for j in range(i+1, len(crossPoints)):
                cp2 = crossPoints[j]
                p2Thick = graph[cp2]['thickness']

                if pointsOverlap(cp1, cp2, rawImg, pt1Thickness = p1Thick, pt2Thickness = p2Thick):
                    #Recursively union each set containing any member overlapping
                    #log.debug( "Merging sets:%s, %s\n %s" % (cp1, cp2, mergeDict) )
                    mergeSet = set([cp1, cp2])
                    procSet = set(mergeSet)
                    log.debug( "MERGING INTERSECTIONS" )
                    while len(procSet) > 0:
                        mergePt = procSet.pop()
                        mergeSet.add(mergePt)
                        ptDict = mergeDict.get(mergePt, set([]))
                        for k in ptDict:
                            if k not in mergeSet:
                                procSet.add(k)
                        mergeDict[mergePt] = mergeSet #Merged into the set
            #END for cp2 ...
        #END for cp1 ...

        #Do the merging now
        alreadyMerged = set([])
        for rep, mergeSet in mergeDict.items():
            #HACK to only process each mergeSet once. (Stupid non-hashable types)
            if rep in alreadyMerged: 
                continue
            alreadyMerged.update(mergeSet)
            #/HACK
            log.debug( "Found %s crossPoints to collapse" % (len(mergeSet)) )

            #Compute the point that will take their place
            xList = [pt[0] for pt in mergeSet]
            yList = [pt[1] for pt in mergeSet]
            assert len(xList) > 0 and len(yList) > 0, "Merging an empty set of crossing Points"
            avgPt = ( sum(xList) / len(xList), sum(yList) / len(yList) )
            
            #Gather all of the points to be merged/replaced by the avg point
            mergedPts = set([])
            for edge in kpDict['edges']:
                head = edge[0]
                tail = edge[-1]
                if head in mergeSet and tail in mergeSet: 
                    doMerge = True
                    #All the points had better overlap one of the endpoints. Otherwise, we'd squash down figure-eight's
                    for ePt in edge:
                        if not pointsOverlap(ePt, 
                                                    head, 
                                                    rawImg, 
                                                    pt1Thickness = graph[ePt]['thickness'], 
                                                    pt2Thickness = graph[head]['thickness']) \
                        and not pointsOverlap(ePt, 
                                                    tail, 
                                                    rawImg, 
                                                    pt1Thickness = graph[ePt]['thickness'], 
                                                    pt2Thickness = graph[tail]['thickness']):
                            doMerge = False
                    if doMerge:
                        mergedPts.update(set(edge))  

            #Gather the future kids of the merged point, and disconnect them from the deleted points
            kidSet = set([])
            #pdb.set_trace()
            for mPt in mergedPts:
                for k in list(graph[mPt]['kids']):
                    graph[k]['kids'].remove(mPt)
                    graph[mPt]['kids'].remove(k)
                    if k not in mergedPts: #We want to make sure this kid gets linked ot the merged point
                        kidSet.add(k)
                del(graph[mPt])

            #Add in the new, merged point and link it to its kids
            #Merge the avgPoint with existing if necessary
            avgPtDict = graph.setdefault(avgPt, {'kids': set(), 'thickness': 0.0})
            avgPtDict['kids'].update(kidSet)
            avgPtDict['thickness'] =  thicknessAtPoint(avgPt, rawImg)
            for k in kidSet:
                graph[k]['kids'].add(avgPt)



def scoreConcatSmoothness(ptList1, ptList2):
    "Scores the smoothness of the angle from 0 to 1, 1 being perfectly smooth"

    scalesList = range(3,10) #[3, 5, 10]  #A factor of the shortest stroke, how far into each stroke to go for a candidate point

    totalSmoothness = 0.0
    assert ptList1[-1] == ptList2[0] # They are joined by a point
    allAnglesList = []
    for concatDepth in scalesList:
        step = max([1, min([concatDepth, len(ptList1), len(ptList2)]) ]) #Step at least 1, at most 5 points or 1/10 of the shorter stroke

        #If there are enough points, skip the shared point and get a more representative point
        if len(ptList1) > 1 and step > 2:
            p2a = ptList1[-2]
        else:
            p2a = ptList1[-1] #Use the shared point

        if len(ptList2) > 1 and step > 2:
            p2b = ptList2[1]
        else:
            p2b = ptList2[0]

        p1 = ptList1[-step]
        p3 = ptList2[step - 1]

        p2_cross = getLinesIntersection( (p1, p2a), (p3, p2b) )
        p2_avg = ( (p2a[0] + p2b[0]) / 2.0, (p2a[1] + p2b[1]) / 2.0 )

        angleAvg = interiorAngle(p1, p2_avg, p3) / 180.0
        #log.debug( "  Step width: %s, attempted %s" % (step, concatDepth) )
        #log.debug( "     Avg angle: %s" % (angleAvg) )
        if p2_cross is not None:
            angleCross = interiorAngle(p1, p2_cross, p3) /180.0
        else:
            angleCross = 0.0
        #log.debug( "     Cross angle: %s" % (angleCross) )
        bestAngle = max([angleCross, angleAvg])
        allAnglesList.append(bestAngle)
        
        #totalSmoothness += concatDepth * bestAngle
    #log.debug( "     Angles List: %s" % (sorted(allAnglesList)) )
    #totalSmoothness = totalSmoothness / sum(scalesList)
    totalSmoothness = sorted(allAnglesList) [len(allAnglesList)/2] #Take the median smoothness over all the scales
    #totalSmoothness = totalSmoothness / float( [len(ptList1), len(ptList2)] )) #Drop the smoothness for longer strokes. Assumes long strokes don't tend to jump much?
    #log.debug( "Smoothness scored: %s" % (totalSmoothness) )

    assert (totalSmoothness >= 0 and totalSmoothness <= 1.0)
    return totalSmoothness





def graphToStrokes(graph, rawImg):
    """Takes in a graph of points and generates a list of strokes that covers them"""
    retStrokes = []

    keyPointsList = getKeyPoints(graph)

    allEdgeList = [kp['edges'] for kp in keyPointsList]

    endPointMap = {} #Will map { <endPoint> : [ strokes with that ep ] }
        

    for kpDict in keyPointsList:
        #Straightforward, blob with single edge (no intersections)
        if len(kpDict['edges']) == 1:
            stroke = Stroke(points = kpDict['edges'][0])
#            for pt in kpDict['edges'][0]:
#                stroke.addPoint(pt)
            retStrokes.append(stroke)
        #Complicated, match up edges at intersections to shrink number of lines
        elif len(kpDict['edges']) > 1:
            #log.debug( "%s Edges to cover" % (len(kpDict['edges'])) )
            edgeList = list(kpDict['edges'])
            #log.debug( "%s Crossing points to cover" % (len(kpDict['crosspoints'])) )
            for cp in kpDict['crosspoints']:
                #log.debug( "Processing cross Point" )
                #Build crossingEdges to contain point lists with cp at index 0
                crossingEdges = []
                for edge in list(edgeList):
                    if edge[0] == cp:
                        crossingEdges.append(edge)
                        edgeList.remove(edge)
                    elif edge[-1] == cp:
                        crossingEdges.append(list(reversed(edge)))
                        edgeList.remove(edge)

                #Match the best strokes at this CP
                while len(crossingEdges) > 1:
                    #log.debug( "  %s crossing edges to process" % (len(crossingEdges)) )
                    #Get the smoothest pair intersecting at this point
                    bestPair = (0, 1)
                    bestSmoothness = 0
                    allEdgeLen = sum([ len(edge) for edge in crossingEdges ])
                    for i in xrange(len(crossingEdges)):
                        for j in xrange(i + 1, len(crossingEdges)):
                            curSmoothness = \
                                scoreConcatSmoothness(list(reversed(crossingEdges[i])),
                                                             crossingEdges[j])
                            #curSmoothness = curSmoothness * allEdgeLen / float(len(crossingEdges[i]) + len(crossingEdges[j]) )
                            if curSmoothness > bestSmoothness:
                                bestSmoothness = curSmoothness
                                bestPair = (i, j)
                    e1 = crossingEdges[bestPair[0]]
                    e2 = crossingEdges[bestPair[1]]
                    newEdge = list(reversed(e1)) + e2[1:]
                    #log.debug( "     Covering 2 edges by merging into 1 with smoothness %s" % (bestSmoothness) )
                    edgeList.append(newEdge)
                    crossingEdges.remove(e1)
                    crossingEdges.remove(e2)

                if len(crossingEdges) > 0:
                    edgeList.extend(crossingEdges)
                    #log.debug( "     Covering %s edges by adding each alone" % (len(crossingEdges)) )
            #end for cp in kpDict[...]

            for edge in edgeList:
                stroke = Stroke(points=edge)
#                for pt in edge:
#                    stroke.addPoint(pt)
                retStrokes.append(stroke)
        #end elif len(kpDict ... )
                
    return retStrokes

#Stolen from GeomUtils
def getLinesIntersection(line1, line2):
    "Input: two lines specified as 2-tuples of points. Returns the intersection point of two lines or None."
    p1, p2 = line1
    q1, q2 = line2

    if p1[0] > p2[0]:
        p1, p2 = p2, p1
    if q1[0] > q2[0]:
        q1, q2 = q2, q1    

    #is p __ than q
    isHigher = p1[1] > q1[1] and p2[1] > q2[1] and p1[1] > q2[1] and p2[1] > q1[1]
    isLower = p1[1] < q1[1] and p2[1] < q2[1] and p1[1] < q2[1] and p2[1] < q1[1]
    isLeft= p2[0] < q1[0]
    isRight= p1[0] > q2[0]

    pA = p2[1] - p1[1]
    pB = p1[0] - p2[0]
    pC = pA*p1[0] + pB*p1[1]

    qA = q2[1] - q1[1]
    qB = q1[0] - q2[0]
    qC = qA*q1[0] + qB*q1[1]

    det = pA*qB - qA*pB
    if det == 0.0:
        return None #Parallel
    ret_x = (qB*pC - pB*qC) / float(det)
    ret_y = (pA*qC - qA*pC) / float(det)

    xpoint = (ret_x, ret_y)
    return xpoint

def filledAndCrossingVals(point, img, valsCache, skipCorners = False):
    """
    http://fourier.eng.hmc.edu/e161/lectures/morphology/node2.html
    with some corner cutting capability from Louisa Lam 1992.
    Returns the number of filled pixels in the 8 neighborhood around the point.
    Crossing is set as the number of transitions from black to white
    Returns dict {
        'filled' : number of filled pixels (incl center)
        'crossing' : number of transitions from white to black (tracing around)
        'esnwne' : is this a E/S/NW/NE region?
        'wnsesw' : is this a W/N/SE/SW region?
        }
    """  
    global CENTERVAL, BGVAL
    height = img.rows
    width = img.cols
    px, py = point

    if point in valsCache:
        return valsCache[point]

    pixval = getImgVal(px, py, img)
    if pixval != CENTERVAL:
        retDict = {'filled':0, 'crossing':-1, 'esnwne': False, 'wnsesw': False}
        return retDict
    else:
        crossing = 0
        filled = 1

        n = (px , py + 1)
        s = (px , py - 1)
        e = (px + 1 , py)
        w = (px - 1 , py)
        ne = (px + 1 , py + 1)
        se = (px + 1 , py - 1)
        nw = (px - 1 , py + 1)
        sw = (px - 1 , py - 1)

        #counterclockwise crossing
        nborList = (ne, n, nw, w, sw, s, se, e)
        totLen = 8#len(nborList)
        #Get all the values for these neighbors
        filledList = [0] * totLen
        i = 0
        someBGpixels = False #If the pixel is in all black, shortcut the crossing num
        while i < totLen:
            pt = nborList[i]
            if pt[0] > 0 and pt[0] < width and pt[1] > 0 and pt[1] < height:
                ptVal = img[pt[1], pt[0]]
            else:
                ptVal = BGVAL
            filledList[i] = ptVal == CENTERVAL
            someBGpixels = someBGpixels or (not filledList[i]) #Turn True if any are NOT centerval
            i+= 1
            #nborVals.append(ptVal)
        if False and not someBGpixels: #Short circuit the tracing for the trivial case
            retDict = {'filled':9, 'crossing':0, 'esnwne': False, 'wnsesw': False}
        else:
            #Get the counterclockwise crossing values
            retDict = {}

            """
            ne = ne == CENTERVAL
            n = n == CENTERVAL
            nw = nw == CENTERVAL

            se = se == CENTERVAL
            s = s == CENTERVAL
            sw = sw == CENTERVAL

            e = e == CENTERVAL
            w = w == CENTERVAL
            """

            #filledList = (ne, n, nw, w, sw, s, se, e)
            prevFilled = filledList[-1]
            i = 0
            while i < totLen:
                ptFilled = filledList[i]
                if ptFilled:
                    filled += 1
                if prevFilled and not ptFilled:
                    if skipCorners and i in (0, 2, 4, 6): #don't count if the missing corner doesn't affect connectivity
                        nextNborIdx = (i + 1) % 8
                        nextFilled = filledList[nextNborIdx]
                        if not nextFilled:
                            crossing += 1
                    else:
                        crossing += 1
                #log.debug( "%s, " % (ptVal), )
                prevFilled = ptFilled
                i+= 1


            #log.debug( "\n%s filled, %s crossing" % (filled, crossing) )
            retDict['filled'] = filled
            retDict['crossing'] = crossing
            


            ne, n, nw, w, sw, s, se, e = filledList
            eEdge = (not ne and not e and not se and s)
            sEdge = (not sw and not s and not se and (w and e) )
            nwEdge = (not w  and not n and (sw and ne) )
            neEdge = (not e  and not n and (se and nw) ) 

            wEdge = (not nw and not w and not sw and n)
            nEdge = (not nw and not n and not ne and (w and e))
            seEdge = (not s and not e and (ne and sw) )
            swEdge = (not s and not w and (se and nw) )

            esnwne = eEdge or sEdge or nwEdge or neEdge
            wnsesw = wEdge or nEdge or seEdge or swEdge


            retDict['esnwne'] = esnwne
            retDict['wnsesw'] = wnsesw
        #endif someBGpixels
    #endif
    valsCache[point] = retDict
    return retDict


def thinBlobsPoints(pointSet, img, cleanNoise = False, evenIter = True, finalPass = False):
    """Implements a single step of thinning over the whole image. 
    Returns the number of pixels changed, the total set of all remaining points, and the thinned image"""
    global DEBUGIMG, FILLEDVAL, BGVAL, CACHE
    minFill = 4
    maxFill = 6
    retPoints = set([])
    numChanged = 0
    cacheTag = 'filledVals%s' % (finalPass) #Whatever gets passed to filledAndCrossingVals
    filledvalsCache = CACHE.setdefault(cacheTag, {})
    if cleanNoise:
        noise = 1
    else:
        noise = -1
    if finalPass: #The final pass has to happen with the same input and output image
        log.debug( "Final pass" )
        minFill = 3
        outImg = img #Edit inline
        for p in pointSet:
            values = filledAndCrossingVals(p, img, filledvalsCache, skipCorners = True)
            cnum_p = values['crossing']
            filled = values['filled']
            if cnum_p == 1 \
                and filled >= minFill \
                and filled <= maxFill:
                setImgVal(p[0], p[1], FILLEDVAL, outImg)
                numChanged += 1
            else:
                retPoints.add(p)
    else:
        outImg = cv.CloneMat(img)
        valDict = {}
        for p in pointSet:
            (i,j) = p
            valDict[p] = filledAndCrossingVals(p, img, filledvalsCache, skipCorners = False)

        for p, values in valDict.items():
            (i,j) = p
            filled = values['filled']
            cnum_p = values['crossing']

            if evenIter:
                badEdge = values['esnwne']
            else:
                badEdge = values['wnsesw']

            shouldRemove = filled >= minFill and filled <= maxFill and cnum_p == 1 and (not badEdge or finalPass) or (filled == noise)
            if shouldRemove:
                numChanged += 1
                if p in filledvalsCache:
                    del( filledvalsCache[p])
                setImgVal(i, j, FILLEDVAL, outImg)
                for nbor in getEightNeighbors(p):
                    if nbor in filledvalsCache:
                        del( filledvalsCache[nbor])
            elif filled > 2: #No need to process otherwise
                retPoints.add(p)

    return ( numChanged, retPoints, outImg )

def cleanContours(pointSet, img):
    global BGVAL, CENTERVAL, FILLEDVAL

    #Preprocess: get all of the contour pixels
    linkedContourPoints = {} #Dict mapping <point> : <set(kids)>
    for p in pointSet:
        isContour = False
        (i,j) = p
        if getImgVal(i, j, img) == CENTERVAL:
            for npt in getEightNeighbors(p):
                (ni, nj) = npt
                if getImgVal(ni, nj, img) != CENTERVAL:
                    isContour = True
                    break
            if isContour:
                p_kidSet = set()
                for npt in getEightNeighbors(p):
                    if npt in linkedContourPoints:
                        linkedContourPoints[npt].add(p)
                        p_kidSet.add(npt)
                linkedContourPoints[p] = p_kidSet

    while len(linkedContourPoints) > 0:
        thisContour = {}
        seedPt, kidset = linkedContourPoints.items()[0]
        log.debug( "Seed %s, kidset %s" % (seedPt, kidset) )
        for k in kidset:
            linkedContourPoints[k].remove(seedPt)
        del(linkedContourPoints[seedPt])

        if len(kidset) > 0:
            pointList = [ seedPt ]
            procStack = [ list(kidset)[0] ]
            while len(procStack) > 0:
                point = procStack.pop()
                log.debug( "Processing point %s" % ( str(point)) )
                for k in linkedContourPoints[point]:
                    if k in linkedContourPoints and k not in procStack:
                        linkedContourPoints[k].remove(point)
                        procStack.append(k)

                if True or len(pointList) < 20:
                    pointList.append(point)

                    log.debug( "Point %s, kidset %s" % (point, linkedContourPoints[point]) )
                    for k in linkedContourPoints[point]:
                        log.debug( "Point %s, kidset %s" % (k, linkedContourPoints[k]) )
                        linkedContourPoints[k].remove(point)
                    del(linkedContourPoints[point])
                else:
                    break

            for point in pointList:
                setImgVal(point[0], point[1], 0, DEBUGIMG)
            log.debug( "Saving Contours" )
            saveimg(DEBUGIMG)


                    

def pointDistanceFromLine(point, lineseg):
    """Returns the Euclidean distance of the point from an infinite line formed by extending the lineseg.
    point: point tuple ( <x>, <y> )
    lineseg: tuple( point, point) making up a linesegment
    """

    assert len(lineseg) == 2, "pointDistanceFromLine called with malformed line segment"
    ep1 = lineseg[0]
    ep2 = lineseg[1]

    assert ep1[0] != ep2[0] or ep1[1] != ep2[1], "pointDistanceFromLine called with 0-length line segment"
    if ep1[0] == ep2[0]: #Vertical line segment
        return math.fabs(point[0] - ep1[0])
    elif ep1[1] == ep2[1]:
        return math.fabs(point[1] - ep1[1])
    else:
        inv_slope = - (ep1[0] - ep2[0]) / float(ep1[1] - ep2[1]) #Perpendicular slope!
        point2 = ( point[0] + 10, point[1] + (inv_slope * 10) )
        distancePoint = getLinesIntersection(lineseg, (point, point2))

        return math.sqrt(pointsDistSquared(point, distancePoint) )


def erodeBlobsPoints (pointSet, img, minFill = 1, maxFill = 9 ):
    numChanged = 0
    retPoints = set()
    outImg = cv.CloneMat(img)
    valsCache = {}
    for p in pointSet:
        (i,j) = p
        valDict = filledAndCrossingVals(p, img,valsCache, skipCorners = False)

        if valDict['filled'] > minFill:
            if valDict['filled'] < maxFill:
                numChanged += 1
                setImgVal(i, j, FILLEDVAL, outImg)
            else:
                retPoints.add(p)

    return ( numChanged, retPoints, outImg )

def getImgVal(x,y,img):
    global OOBVAL
    h = img.rows
    w = img.cols
    if x >=0 and x < w and y >= 0 and y < h:
        return img[y,x]
    else:
        #log.debug( "Trying to get invalid pixel %s" % (str( (x,y) )) )
        return OOBVAL
'''
def getImgVal(x,y,img):
    """Returns the image value for pixel x,y in img or -1 as error."""
    global OOBVAL
    try:
        return img[y,x]
    except Exception as e:
        return OOBVAL
'''
      
def setImgVal(x,y,val,img):
    try:
        img[y,x] = val
    except:
        pass

def getHeight(img):
    return img.rows
def getWidth(img):
    return img.cols

def isFilledVal(value):
    """Determine what counts as a filled pixel"""
    global FILLEDVAL
    return value == FILLEDVAL





#***************************************************
#  Image Processing
#***************************************************

def getHoughLines(img, numlines = 4):
    """Largely taken from 
    http://www.seas.upenn.edu/~bensapp/opencvdocs/ref/opencvref_cv.htm"""
    linethresh = 50
    rhoGran = 3
    thetaGran = math.pi / 180
    cannyThresh = (30, 70)
    edgeKernel = 3
    
    gray_img = cv.CreateMat(img.rows, img.cols, cv.CV_8UC1)
    cv.CvtColor(img, gray_img, cv.CV_RGB2GRAY)
    img = gray_img

    edges_img = cv.CreateMat(img.rows, img.cols, cv.CV_8UC1)
    cv.Canny(img, edges_img, cannyThresh[0], cannyThresh[1], edgeKernel)
    saveimg(edges_img)

    seq = cv.HoughLines2(edges_img, 
                                cv.CreateMemStorage(), 
                                cv.CV_HOUGH_STANDARD,
                                rhoGran, thetaGran, 
                                linethresh)
    retLines = []
    edge_mask = cv.CreateMat(edges_img.rows, edges_img.cols, cv.CV_8UC1)
    for line in seq:
        if numlines == 0:
            break
        rho, theta = line

        a = math.cos(theta)
        b = math.sin(theta)
        x0 = a * rho
        y0 = b * rho

        
        p1x = int(x0 + 2000 * (-b))
        p1y = int(y0 + 2000 * (a))
        p1 = (p1x, p1y)

        p2x = int(x0 - 2000 * (-b))
        p2y = int(y0 - 2000 * (a))
        p2 = (p2x, p2y)
        
#        cosT = math.cos(theta)
#        sinT = math.sin(theta)
#        if cosT != 0.0:
#            x1 = rho / cosT
#            y1 = 0
#        
#        x1 = rho / math.cos(theta)
#        y1 = 0
#        x2 = 

        numlines -= 1
        retLines.append( (p1, p2,) )
    
    return retLines



def adaptiveThreshold(img):
    """A fast adaptive threshold using OpenCV's implementation. The image is 
    first brightened to wash out background artifacts, then adaptive threshold
    is used to separate ink from the board."""
    blockSize = 39 #How wide of a block to consider for Ad. Thresh.

    cv.AdaptiveThreshold(img, img, 255, 
        adaptive_method=cv.CV_ADAPTIVE_THRESH_GAUSSIAN_C, 
        blockSize=blockSize, 
        )
    return img

def resizeImage(img, scale = None, targetWidth = None):
    "Take in an image and size it according to scale"
    if scale is None:
        if targetWidth is None:
            raise Exception("Both scale and targetWidth not set!")
        realWidth = img.cols
        scale = targetWidth / float(realWidth) #rough scaling

    retImg = cv.CreateMat(int(img.rows * scale), int(img.cols * scale), img.type)
    cv.Resize(img, retImg)
    return retImg

def smooth(img, ksize=3, t='median'):
    """Do a median or gaussian smoothing with kernel size ksize. Type values
    t are either 'median' or 'gauss'"""
    retimg = cv.CloneMat(img)
    if t == 'gauss':
        smoothtype = cv.CV_GAUSSIAN
    else:
        smoothtype = cv.CV_MEDIAN
    #retimg = cv.CreateMat(img.cols, img.rows, cv.CV_8UC3)
    #                                     cols, rows, anchorx,y, shape
    #kernel = cv.CreateStructuringElementEx(3,3, 1,1, cv.CV_SHAPE_RECT,
                                                        #(0,1,0,1,0,1,0,1,0))
    ksize = min(ksize, img.rows/2, img.cols/2)
    cv.Smooth(img, retimg, smoothtype= smoothtype, param1=ksize)
    return retimg

def invert (cv_img):
    """Return a negative copy of the grayscale image"""
    global BGVAL
    retimg = cv.CloneMat(cv_img)
    cv.Set(retimg, BGVAL)
    cv.AddWeighted(cv_img, -1.0, retimg, 1.0, 0.0,retimg )
    return retimg

def printHistogramList(hist, granularity = 1):
    "Take in a list of values, and print each number prettily, with its index being the bucket"
    accum = 0
    for idx, val in enumerate(hist):
        accum += val
        if idx % granularity == 0:
            print "%s:\t" % (idx),
            while accum / granularity > 0:
                print "X",
                accum -= granularity
            print "\t%3.6f" % (val)
            accum = 0

    if idx % granularity != 0:
        print "%s:\t" % (idx),
        while accum / granularity > 0:
            print "X",
            accum -= granularity
        print "\t%3.6f" % (val)
    
def getHistogramList(img, normFactor = 1000, numBins = 256):
    """Returns a histogram of a GRAYSCALE image, normalized such that all bins add to 1.0"""
    retVector = []
    if img.type != cv.CV_8UC1:
        log.debug( "Error, can only get histogram of grayscale image" )
        return retVector

    hist = cv.CreateHist( [numBins], cv.CV_HIST_ARRAY, [[0,256]], 1)
    cv.CalcHist([cv.GetImage(img)], hist)
    cv.NormalizeHist(hist, normFactor)
    gran = 5
    accum = 0
    for idx in xrange(0, numBins):
        retVector.append(cv.QueryHistValue_1D(hist, idx))
    return retVector

def isForeGroundGone(img, mask = None, borderThresh = 0.05):
    """Figure out whether the strokes of an image have been smoothed 
    away or still remain. borderThresh is the % of the image border
    that should be ignored. Use the mask to filter where we should
    look for foreground info."""
    #Define a region that we want to look at, so we don't try to 
    #smudge out border artifacts and mess up the ink
    #borderThresh = 0.15 #How much of the border to ignore in figuring whether the foreground is gone
    left = int( borderThresh * img.cols)
    right = int( (1 - 2 * borderThresh) * img.cols)
    top = int( borderThresh * img.rows)
    bottom = int( (1 - 2 * borderThresh) * img.rows)
    activeROI = ( left, top, right, bottom)
    img = cv.GetSubRect(img, activeROI)
    
    #Check for edge information
    edges = cv.CreateMat(img.rows, img.cols, cv.CV_8UC1)
    cv.Canny(img, edges, 50,100)
    if mask is not None:
        cv.And(cv.GetSubRect(mask, activeROI), edges, edges)
    edgeAmount = cv.CountNonZero(edges)
    cv.PutText(edges, "Edges", (20, edges.rows - 20), cv.InitFont(cv.CV_FONT_HERSHEY_PLAIN, 1, 1), 255)
    log.debug("Saving Edges")
    saveimg(edges, name="Edges")
    log.debug("Edge info left: %d" % (edgeAmount))
    if edgeAmount == 0:
        log.debug("Short circuiting background removal")
        noForeground = True
        return True
    
    #Get the histogram normalized to 1000 total
    hist = getHistogramList(img)
#    printHistogramList(hist, granularity = 10)
    histNorm = 1000
    #Where is it safe to assume that the rest is foreground?
    foreGroundThresh = 80
    #How far apart must the background be from the foreground?
    smudgeFactor = 35

    total = 0
    targetTotal = 0.7 * histNorm
    noForeground = False #The return value

    if sum(hist) == 0: #Empty image
        return True
    i = 255
    #Add up hist values from white to black, but 
    #don't bother going past foreGroundThresh darkness
    while i >= foreGroundThresh and total < targetTotal: 
        total += hist[i]
        i -= 1

    if total < targetTotal: 
        #Not enough background above what we assume is foreground ink
        return False
    #We have gotten past the peak of background
    #Come down the "peak"
    while i >= 0 and hist[i] >= 1.0:
        i -= 1
    lastNum = i
    #Follow the tail of the peak to the first empty bucket
    while i >= 0 and hist[i] > 0.0:
        i -= 1
    firstZero = i
    #If the range of remaining dark values are within a
    #reasonable range of the background peak, just
    #ignore them
    if lastNum - firstZero <= smudgeFactor:
        #If the foreground picks up again, there is
        #still some ink remaining
        remainingSum = sum(hist[:i])
        if remainingSum > 0:
            log.debug( "Ink remaining with value under %s (%s)" % (i, remainingSum) )
            noForeground = False
        else:
            log.debug( "Not enough Ink remaining with value under %s (%s)" %                     
                          (i, remainingSum) )
            noForeground = True
    return noForeground
        

def convertBlackboardImage(gray_img):
    """Take in a black and white image of a drawing, determine if it's a blackboard,
    and then invert it so it looks more like a whiteboard"""
    global ISBLACKBOARD
    hist = getHistogramList(gray_img)
    #printHistogramList(hist, granularity = 10)
    maxIdx = hist.index(max(hist))
    bright3rd = ( maxIdx + len(hist) )/ 2
    dark3rd = ( maxIdx )/ 2
    darkSum = sum(hist[:dark3rd])
    brightSum = sum(hist[bright3rd:])
    #log.debug( "Maximum bin: ", hist.index(max(hist)) )
    if maxIdx > 200:
        #log.debug( "Not a blackboard: bright peak!" )
        ISBLACKBOARD = False
    elif maxIdx < 50:
        #log.debug( "Blackboard seen: dark peak!" )
        ISBLACKBOARD = True 
    elif darkSum > brightSum:
        #log.debug( "Not a blackboard: more dark than light!" )
        ISBLACKBOARD = False
    else:
        #log.debug( "Blackboard seen: more light than dark" )
        ISBLACKBOARD = True 

    #HACK!
    log.debug( "WARNING: Short circuiting blackboard evaluation" )
    ISBLACKBOARD = False
    #HACK!


    if ISBLACKBOARD:
        log.debug( "Converting Blackboard image to look like a whiteboard" )
        gray_img = invert(gray_img)
        saveimg(gray_img, name="Inverted_Blackboard")
    return gray_img

def getObviousBackgroundMask(image):
    """Get a mask of the places that are too dark to be a whiteboard"""
    backgroundThresh = 120
    obviousBackgroundMask = cv.CreateMat(image.rows, image.cols, cv.CV_8UC1)
    cv.CvtColor(image, obviousBackgroundMask, cv.CV_RGB2GRAY)
    cv.Threshold(obviousBackgroundMask, obviousBackgroundMask, 
                 backgroundThresh, 255, cv.CV_THRESH_BINARY)
    cv.Dilate(obviousBackgroundMask, obviousBackgroundMask, iterations = 5)
    cv.Erode(obviousBackgroundMask, obviousBackgroundMask, iterations = 5)
    return obviousBackgroundMask

def removeBackground(cv_img):
    """Take in a color image and convert it to a binary image of just ink"""
    global BGVAL, ISBLACKBOARD, DEBUG
    #Values computed relative to image resolution 
#    denoise_k = 5 / 1000.0 #Used to smooth out noise
    width = cv_img.cols
    smooth_k  = 3 / 100.0 #Initial smoothing kernel to remove background
    smooth_k = max (1, int(smooth_k * width))
    if smooth_k % 2 == 0:
        smooth_k += 1

    ink_thresh = 90 #Hardcoded value to distinguish between ink and background

#    denoise_k = max (1, int(denoise_k * width))
#    if denoise_k % 2 == 0:
#        denoise_k += 1

    #Convert to grayscale if needed
    if cv_img.type != cv.CV_8UC1:
        gray_img = cv.CreateMat(cv_img.rows, cv_img.cols, cv.CV_8UC1)
        cv.CvtColor(cv_img, gray_img, cv.CV_RGB2GRAY)
    else:
        gray_img = cv.CloneMat(cv_img)


    gray_img = convertBlackboardImage(gray_img)    
    saveimg(gray_img, name="ConvertedBlackboard")


    #Generate the "background image"
    log.debug( "Remove foreground" )
    smoothScale = 1.15 #How fast do we grow the smoothing kernel
    bg_img = gray_img
    i = 0
    while not isForeGroundGone(bg_img) \
            and smooth_k < cv_img.rows / 2.0:
        i+= 1
        bg_img = smooth(bg_img, ksize=smooth_k, t='median')
        smooth_k = int(smooth_k * smoothScale)
        if smooth_k % 2 == 0:
            smooth_k += 1
        if DEBUG :
            log.debug( "Background Image:" )
            saveimg(bg_img, name="SmoothedForeground{}".format(i))
    log.debug( "Remove foreground -- Done" )
    saveimg(bg_img, name="Foreground_Removed")

    #Remove the "background" data from the original image
    ink_img = cv.CloneMat(gray_img)
    cv.AddWeighted(gray_img, 0.5, bg_img, -0.5, 128.0, ink_img )
    if DEBUG :
        log.debug( "Ink isolated -- background removed" )
        saveimg(ink_img, name="Ink_Isolated")
    #cv.EqualizeHist(gray_img, gray_img)

    #Convert the black ink to white and amplify!
    log.debug("Amplifying ink")
    ink_img = invert(ink_img)
    if DEBUG:
        saveimg(ink_img, name="Ink_Inverted")
    #Add the image back onto itself, saturating the light areas (ink), but
    #    leaving the darker areas dark.
    if ISBLACKBOARD:
        amplifyList = [1]
    else:
        amplifyList = [2]
    for i in amplifyList:
        smooth_ink_img = smooth(ink_img, ksize=3, t='median')
        gamma = ( (i * 2 - 1)* -127)#- 127
        cv.AddWeighted(ink_img, i, smooth_ink_img, i, gamma, ink_img )
        if DEBUG:
            saveimg(ink_img, name="Amplify_Ink_{}".format(i))
    ink_img = invert(ink_img)
    if DEBUG:
        log.debug( "Ink Amplified" )
        saveimg(ink_img, name="Ink_Amplify_Finished")

    #Binarize the amplified ink image
    ink_mask = cv.CloneMat(gray_img)
    cv.Threshold(ink_img, ink_mask, ink_thresh, BGVAL, cv.CV_THRESH_BINARY)

    if DEBUG:
        log.debug( "Ink Isolated" )
        saveimg(ink_mask, name="Ink_Isolated")
    

#    lineImage = cv.CreateMat(bg_img.rows, bg_img.cols, cv.CV_8UC3)
#    cv.CvtColor(gray_img, lineImage, cv.CV_GRAY2RGB)
#    for line in getHoughLines(lineImage, 1):
#        cv.Line(lineImage, line[0], line[1], (255,0,0), thickness=3)
#    show (lineImage)
    return ink_mask, bg_img


def floodFill(image, seedPt, thresholds = (0, 255), color=0):
    """Fills a region with color from a seed point, as long as the
    pixels are in the range defined by thresholds (inclusive)."""
    x,y = seedPt
    seedVal = image[y,x]
    loDiff = seedVal - thresholds[0]
    hiDiff = thresholds[1] - seedVal
    log.debug( "Filling %s-%s with %s" % (seedVal - loDiff, seedVal + hiDiff, color) )
    cv.FloodFill(image, seedPt, 
                     color, lo_diff=loDiff , up_diff=hiDiff, 
                     flags = cv.CV_FLOODFILL_FIXED_RANGE)
     

def blobsToStrokes(img):
    "Take in a black and white image of a whiteboard, thin the ink, and convert the points to strokes."
    global DEBUGIMG, BGVAL, FILLEDVAL
    log.debug( "Thinning blobs:" )
    rawImg = cv.CloneMat(img)


    t1 = time.time()
    pointSet = set()
    x = 1
    while x < img.cols:
        y = 1
        while y < img.rows:
            if img[y,x] != BGVAL:
                pointSet.add((x,y))
            y+= 1
        x+=1

    t2 = time.time()
    log.debug( "Candidate Points generated %s ms" % (1000 * (t2 - t1)) )
            

    passnum = 0
    changed1 = True
    changed2 = True
    evenIter = True 
    FILLEDVAL = 240
    psetSize = None
    isHollowed = False

    chartFile = open("pointsData.txt", "w")

    while changed1 or changed2:
        passnum += 1
        log.debug( "Pass %s" % (passnum) )
        if DEBUG:
            saveimg(img, name="Thinning_Pass_{}".format(passnum))
        evenIter = (passnum %2 == 0)
        t1 = time.time()

        numChanged, pointSet, img = thinBlobsPoints(pointSet, img, cleanNoise = (passnum <= 2), evenIter = evenIter)
        if psetSize == None:
            psetSize = len(pointSet)

        t2 = time.time()
        log.debug( "Num changes = %s in %s ms" % (numChanged, (t2-t1) * 1000 ) )
        if passnum % 2 == 0:
            changed1 = numChanged > 0
        else:
            changed2 = numChanged > 0

    log.debug( "" )
    numChanged, pointSet, img = thinBlobsPoints(pointSet, img, finalPass = True)

    chartFile.close()

    if DEBUG:
        saveimg(img, name="Ink_Thinned")
    log.debug( "Tracing strokes" )
    strokelist = pointsToStrokes(pointSet, rawImg)
    return strokelist


def prettyPrintStrokes(img, strokeList):
    """Take in a raw, color image and return a list of strokes extracted from it."""

    temp_img = cv.CloneMat(img)
    cv.Set(temp_img, (255,255,255))
    videoWriter = cv.CreateVideoWriter("Debug.avi", 
                                       cv.CV_FOURCC('D', 'I', 'V', 'X'),
                                       30, cv.GetSize(img))
    cv.WriteFrame(videoWriter, cv.GetImage(temp_img))
    pointsPerFrame = 20
    strokeList = list(strokeList)

    lineColor =  0
    startColor = 128
    stopColor = 220
    for s in strokeList:
        prev = None
        allPoints = s.Points
        for i, p in enumerate(allPoints):
            p = (int(p.X), int(p.Y))
            if prev is not None:
                cv.Line(temp_img, prev, p, lineColor, thickness=1)
            else:
                cv.Circle(temp_img, p, 1, startColor, thickness=-1)
            prev = p 
            if i % pointsPerFrame == 0:
                cv.WriteFrame(videoWriter, cv.GetImage(temp_img))
        cv.Circle(temp_img, p, 1, stopColor, thickness=-1)
        cv.WriteFrame(videoWriter, cv.GetImage(temp_img))
        


def pointDist(p1, p2):
    "Find the squared distance between two points"
    p1x, p1y = p1
    p2x, p2y = p2

    return (p2x-p1x) ** 2 + (p2y-p1y) ** 2



def main(args):
    global SQUARE_ERROR, PRUNING_ERROR, DEBUG
    DEBUG = True

    if len (args) < 2:
        print( "Usage: %s <image_file>" % (args[0]))
        exit(1)

    fname = args[1]
    in_img = cv.LoadImageM(fname)

    strokeList = cvimgToStrokes(in_img, targetWidth = in_img.cols)
    prettyPrintStrokes(in_img, strokeList['strokes'])


if __name__ == "__main__":
    sys.path.append("../")
    main(sys.argv)


