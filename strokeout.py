#!/usr/bin/env python
import cv
import Image
import pickle
import random
import math
import pdb
import time


random.seed("sketchvision")
BLACK = 0
WHITE = 255
GRAY = 200

FILLEDVAL = GRAY
CENTERVAL = BLACK
BGVAL = WHITE

COLORFACTOR = 10

DENOISE_K = 5
SMOOTH_K = 23
INV_FACTOR = 0.5
INK_THRESH = 122

PRUNING_ERROR = 0.2
SQUARE_ERROR = 0.2
PRUNING_ERROR = PRUNING_ERROR * SQUARE_ERROR

NORMWIDTH = 1000
DEBUGSCALE = 1

class Timer (object):
   def __init__(self, desc = "Timer"):
      self.start = time.time()
      self.desc = desc
      self.laps = 0
      self.laptime = self.start
   def lap(self, desc = ""):
      now = time.time()
      print "%s - %s: %s ms, %s ms" % (self.desc, desc, 1000 * (now - self.laptime), 1000 * (now - self.start))
      self.laptime = now


def fname_iter():
   imgnum = 0
   while True:
      fname = "%06.0d.jpg" % (imgnum)
      #print fname
      imgnum += 1
      yield fname 

FNAMEITER = fname_iter()
#***************************************************
# Random Utility Functions
#***************************************************
def printPoint(pt, img):
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
   global BGVAL, FILLEDVAL, CENTERVAL
   px, py = point

   pixval = getImgVal(px, py, img)
   t = 0
   if pixval == BGVAL:
      return t

   horiz = (1, 0)
   vert  = (0, 1)
   rdiag = (1, 1)
   ldiag = (1,-1)
   growthDirs = [horiz, vert, rdiag, ldiag]
   minThickness = 1000
   for d in growthDirs:
      t = 0
      maxPosT = 0
      posVal = pixval
      while posVal == CENTERVAL or posVal == FILLEDVAL:
         maxPosT = t
         posPt = (point[0] + t * d[0], point[1] + t * d[1])
         posVal = getImgVal(posPt[0], posPt[1], img)
         t += 1

      maxNegT = 0
      negVal = pixval
      t = 0
      while negVal == CENTERVAL or negVal == FILLEDVAL:
         maxNegT = t
         negPt = (point[0] - t * d[0], point[1] - t * d[1])
         negVal = getImgVal(negPt[0], negPt[1], img)
         t += 1

      diagScale = math.sqrt(d[0] * d[0] + d[1] * d[1])
      totalThickness = diagScale * (maxPosT + maxNegT + 1)
      if totalThickness < minThickness:
         minThickness = totalThickness
   return minThickness

def linePixels(pt1, pt2):
   """Generates a list of pixels on a line drawn between pt1 and pt2"""
   #print "Pixels from %s to %s" % (pt1, pt2)
   left, right = sorted([pt1, pt2], key = lambda pt: pt[0])

   deltax = right[0] - left[0]
   deltay = right[1] - left[1]

   if deltax != 0:
      slope = deltay / float(deltax)
      y = left[1]
      error = 0.0
      for x in xrange(left[0], right[0] + 1):
         #print "Err:", error
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
      for y in xrange(bottom[1], top[1] + 1):
         yield (left[0], y)


def drawLine(pt1, pt2, color, img):
   """Draw a line from pt1 to pt2 in image img"""
   for x,y in linePixels(pt1, pt2):
      setImgVal(x,y,color,img)


def pointsOverlap(pt1, pt2, img):
   """Checks to see if two points cover each other with their thickness and are not separatred by white"""
   global CENTERVAL
   distSqr = pointsDistSquared(pt1, pt2) 
   pt1ThicknessSqr = (thicknessAtPoint(pt1, img) / 2.0) ** 2
   pt2ThicknessSqr = (thicknessAtPoint(pt2, img) / 2.0) ** 2
   if distSqr > pt2ThicknessSqr and distSqr > pt1ThicknessSqr: #If neither thickness covers the other point
      return False
   for x,y in linePixels(pt1, pt2):
      if getImgVal(x,y,img) != CENTERVAL:
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

   
def pointsToGraph(pointSet, rawImg):
   """From a raw, binary image and approximate thinned points associated with it, 
   turn the thinned points into a graph.
   * Thinned strokes are trimmed according to line thickness for better results."""
   graphDict = {}
   while len(pointSet) > 0:
      seed = pointSet.pop()
      pointSet.add(seed)
      procStack = [{'pt': seed, 'path':[]}]
      while len(procStack) > 0:
         procDict = procStack.pop(0) #Breadth first
         pt = procDict['pt']
         if pt not in pointSet:
            continue

         path = list(procDict['path'])
         path.append(pt)

         if len(path) == 1 or not pointsOverlap(path[0], pt, rawImg):
            for idx in xrange(1,len(path)):
               par = path[idx-1]
               kid = path[idx]
               parDict = graphDict.setdefault(par, {'kids': set([]), 'thickness':thicknessAtPoint(par,rawImg)})
               kidDict = graphDict.setdefault(kid, {'kids': set([]), 'thickness':thicknessAtPoint(par,rawImg)})
               parDict['kids'].add(kid)
               kidDict['kids'].add(par)
            path = [pt]

               
         for nPt in getEightNeighbors(pt, shuffle = True):
            if nPt in pointSet:
               procStack.append({'pt':nPt, 'path': path})
         pointSet.remove(pt)

   return graphDict

   
def getKeyPoints(graph):
   """Takes in a graph of points and returns a list of keypoint dictionaries.
   {'endpoints', 'crosspoints'}"""
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
         elif len(graphCpy[pt]['kids']) == 1:
            endPoints.add(pt)
         seen.add(pt)
         for nPt in graphCpy[pt]['kids']:
            if nPt not in seen:
               procStack.append({'pt':nPt, 'dist': dist + 1})
         del(graphCpy[pt])

      retList.append({'seed': seed, 'endpoints' : endPoints, 'crosspoints' : crossPoints})

   _getGraphEdges(graph, retList)
   
   return retList

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

      finishStroke = True

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
   
def _getGraphEdges(graph, keyPointsList):
   """Adds the edge information to each keypoint entry in keyPointsList"""
   global DEBUGIMG
   #keyPointsList = getKeyPoints(graph)
   for kpDict in keyPointsList:
      endPoints = kpDict['endpoints']
      crossPoints = kpDict['crosspoints']
      seedPoint = kpDict['seed']
      edges = kpDict['edges'] = [] #Create a new tag

      if len(graph[seedPoint]['kids']) == 0: #Special case of single point stroke
         edges.append([seedPoint])
         continue

      allKeyPts = set(list(endPoints) + list(crossPoints))
      if len(allKeyPts) == 0:
         #Just start the edge at the seed
         allKeyPts.add(seedPoint)

      procStack = [{'pt' : list(allKeyPts)[0], 'par' : None, 'edge' : []}]
      seen = set([])
      while len(procStack) > 0:
         ptDict = procStack.pop()
         pt = ptDict['pt']
         par = ptDict['par']
         curEdge = ptDict['edge']

         if pt in seen:
            continue

         if par == None:
            assert pt in allKeyPts, "Point with no parent, not in keypoint list"
            for k in graph[pt]['kids']:
               if k not in seen and k not in allKeyPts:
                  procStack.append( {'pt' : k, 'par' : pt, 'edge' : [pt]} )
         elif pt in allKeyPts:
            curEdge.append(pt)
            edges.append(curEdge)
            procStack.append( {'pt' : pt, 'par' : None, 'edge' : None} )
            """
            #DEBUG
            cv.Set(DEBUGIMG, 255)
            for dbPt in curEdge:
               setImgVal(dbPt[0], dbPt[1], 0, DEBUGIMG)
            saveimg(DEBUGIMG)
            #/DEBUG
            """
         else:
            seen.add(pt)
            curEdge.append(pt)
            numKids = 0
            for k in graph[pt]['kids']:
               if k != par:
                  procStack.append( {'pt': k, 'par' : pt, 'edge': curEdge} )
                  numKids += 1
            assert numKids == 1, "Non-keypoint %s added too many/few kids: \nptDict: %s\ngraph[pt]: %s" % (str(pt), ptDict, graph[pt])
      #END while len(procStack) ...
   #END for keyPointList ...

def _collapseIntersections(graph, keyPoints, edges):
   keyPoints = getKeyPoints(graph)
   for kpDict in keyPoints:
      mergeDict = {}
      crossPoints = list(kpDict['crosspoints'])
      for cp1 in crossPoints:
         for cp2 in crossPoints:
            if cp1 == cp2:
               continue
            else:
               if pointsOverlap(cp1, cp2, rawImg):
                  mergeSet = set([cp1, cp2])
                  procSet = set(mergeSet)
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
      for mergeSet in set(mergeDict.values()):
         xList = [pt[0] for pt in mergeSet]
         yList = [pt[1] for pt in mergeSet]
         assert len(xList) > 0 and len(yList > 0), "Merging an empty set of crossing Points"
         avgPt = ( sum(xList) / len(xList), sum(yList) / len(yList) )

def graphToStrokes(graph):
   """Takes in a graph of points and generates a list of strokes that covers them"""
   retStrokes = []

   keyPointsList = getKeyPoints(graph)
   #_collapseIntersections(keyPointsList)
   allEdgeList = [kp['edges'] for kp in keyPointsList]

   for edgeList in allEdgeList:
      for edge in edgeList:
         stroke = Stroke()
         for pt in edge:
            stroke.addPoint(pt)
         retStrokes.append(stroke)
   return retStrokes
   """
   keyPoints = getKeyPoints(graph)
   edgeList = getGraphEdges(graph)
   for kpDict in keyPoints:
      endPoints = list(kpDict['endpoints'])
      crossPoints = list(kpDict['crosspoints'])
      seedPoint = kpDict['seed']

      if len(endPoints) == 0:             #Zero endpoints
         if len(crossPoints) == 0:
            strokes = strokesFromSeed(seedPoint, graph)
         elif len(crossPoints) == 1:
            strokes = strokesFromSeed(seedPoint, graph)
         elif (len(crossPoints) %2) == 0:
            strokes = strokesFromSeed(seedPoint, graph)
         elif (len(crossPoints) %2) == 1:
            strokes = strokesFromSeed(seedPoint, graph)
      elif len(endPoints) == 1:           #One endpoint
         if len(crossPoints) == 0:
            strokes = strokesFromSeed(endPoints[0], graph)
         elif len(crossPoints) == 1:
            strokes = strokesFromSeed(endPoints[0], graph)
         elif (len(crossPoints) %2) == 0:
            strokes = strokesFromSeed(endPoints[0], graph)
         elif (len(crossPoints) %2) == 1:
            strokes = strokesFromSeed(endPoints[0], graph)
      elif len(endPoints) %2 == 0:        #Even endpoints
         if len(crossPoints) == 0:
            strokes = strokesFromSeed(endPoints[0], graph)
         elif len(crossPoints) == 1:
            strokes = strokesFromSeed(endPoints[0], graph)
         elif (len(crossPoints) %2) == 0:
            strokes = strokesFromSeed(endPoints[0], graph)
         elif (len(crossPoints) %2) == 1:
            strokes = strokesFromSeed(endPoints[0], graph)
      elif len(endPoints) %2 == 1:        #Odd endpoints
         if len(crossPoints) == 0:
            strokes = strokesFromSeed(endPoints[0], graph)
         elif len(crossPoints) == 1:
            strokes = strokesFromSeed(endPoints[0], graph)
         elif (len(crossPoints) %2) == 0:
            strokes = strokesFromSeed(endPoints[0], graph)
         elif (len(crossPoints) %2) == 1:
            strokes = strokesFromSeed(endPoints[0], graph)

      retStrokes.extend(strokes)
   return retStrokes
   """

def drawGraph(graph, img):
   for p, pdict in graph.items():
      for k in pdict['kids']:
         drawLine(p,k,220,img)
         #cv.Line(img, p, k, 220, thickness = 1)
         setImgVal(p[0], p[1], 128, img)
         setImgVal(k[0], k[1], 128, img)
   
def pointsToStrokes(pointSet, rawImg):
   global DEBUGIMG
   graph = pointsToGraph(pointSet, rawImg)
   """
   cv.Set(DEBUGIMG, 255)
   drawGraph(graph, DEBUGIMG)
   saveimg(DEBUGIMG)
   """

   retStrokes = graphToStrokes(graph)
   return retStrokes

def filledAndCrossingVals(point, img, skipCorners = False):
   """
   http://fourier.eng.hmc.edu/e161/lectures/morphology/node2.html
   with some corner cutting capability from Louisa Lam 1992.
   """  
   global CENTERVAL, BGVAL
   height = img.rows
   width = img.cols
   retDict = {'filled':0, 'crossing':-1, 'esnwne': False, 'wnsesw': False}
   px, py = point

   pixval = getImgVal(px, py, img)
   if pixval == CENTERVAL:
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
      nborList = [ne, n, nw, w, sw, s, se, e]
      #Get all the values for these neighbors
      nborVals = []
      for i, pt in enumerate(nborList):
         if pt[0] > 0 and pt[0] < width and pt[1] > 0 and pt[1] < height:
            ptVal = img[pt[1], pt[0]]
         else:
            ptVal = BGVAL
         nborVals.append(ptVal)
      
      #Get the counterclockwise crossing values
      ne, n, nw, w, sw, s, se, e = nborVals

      ne = ne == CENTERVAL
      n = n == CENTERVAL
      nw = nw == CENTERVAL

      se = se == CENTERVAL
      s = s == CENTERVAL
      sw = sw == CENTERVAL

      e = e == CENTERVAL
      w = w == CENTERVAL

      filledList = [ne, n, nw, w, sw, s, se, e]
      prevFilled = e
      for i, ptFilled in enumerate(filledList):
         if ptFilled:
            filled += 1
         if prevFilled and not ptFilled:
            if skipCorners and i in [0, 2, 4, 6]: #don't count if the missing corner doesn't affect connectivity
               nextNborIdx = (i + 1) % 8
               nextFilled = filledList[nextNborIdx]
               if not nextFilled:
                  crossing += 1
            else:
               crossing += 1
         #print "%s, " % (ptVal),
         prevFilled = ptFilled


      #print "\n%s filled, %s crossing" % (filled, crossing)
      retDict['filled'] = filled
      retDict['crossing'] = crossing
      


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
   #endif
   return retDict


def thinBlobsPoints(pointSet, img, cleanNoise = False, evenIter = True, finalPass = False):
   global DEBUGIMG, FILLEDVAL, BGVAL
   minFill = 4
   maxFill = 6
   retPoints = set([])
   numChanged = 0
   if finalPass:
      print "Final pass"
      minFill = 3
      outImg = img #Edit inline
   else:
      outImg = cv.CloneMat(img)

   if cleanNoise:
      #minFill = 3
      noise = 1
   else:
      noise = -1
   for p in pointSet:
      (i,j) = p
      valDict = filledAndCrossingVals(p, img, skipCorners = finalPass)
      filled = valDict['filled']
      cnum_p = valDict['crossing']

      if evenIter:
         badEdge = valDict['esnwne']
      else:
         badEdge = valDict['wnsesw']

      if (filled >= minFill and filled <= maxFill and cnum_p == 1 and (not badEdge or finalPass) ) or \
         (filled == noise): 
         numChanged += 1
         setImgVal(i, j, FILLEDVAL, outImg)
         #saveimg(outImg)
      elif filled > 2: #No need to process otherwise
         retPoints.add(p)
   saveimg(outImg)

   return ( numChanged, retPoints, outImg )


def getImgVal(x,y,img, errorVal = -1):
   """Returns the image value for pixel x,y in img or -1 as error."""
   h = img.rows
   w = img.cols
   if y < 0 or y >= h or x < 0 or x >= w:
      return errorVal
      #print "Returning -1 for %s, %s" % (x,y)
   try:
      return img[y,x]
   except:
      print "Trying to get invalid pixel %s" % (str( (x,y) ))
     
def setImgVal(x,y,val,img):
   img[y,x] = val

def getHeight(img):
   return img.rows
def getWidth(img):
   return img.cols

def isFilledVal(value):
   """Determine what counts as a filled pixel"""
   global FILLEDVAL
   return value == FILLEDVAL



#***************************************************
#  Stroke Class
#***************************************************



class Stroke(object):
   """A stroke consisting of a list of points"""
   def __init__(self):
      self.points = []
      self.thicknesses = []
      self.thickness = 0
      self.center = (-1, -1)
      self.topleft = (-1, -1)
      self.bottomright = (-1, -1)
   def addPoint(self,point, thickness = 1):
      """Add a point to the end of the stroke"""
      x,y = point
      left = min( x, self.topleft[0])
      right = max( x, self.bottomright[0])

      top = max( y, self.topleft[1])
      bottom = min( y, self.bottomright[1])

      self.topleft = (left, top)
      self.bottomright = (right, bottom)

      self.center = ( (left + right ) / 2, 
                      (top + bottom ) / 2 )

      self.points.append( (x, y) )
      self.thicknesses.append(thickness)
      
   def getPoints(self):
      """Return a list of points"""
      return self.points
   def getThickness(self):
      sortedList = list(self.thicknesses)
      sortedList.sort()
      if len(self.thicknesses) > 0:
         return sortedList[(len(sortedList) / 2) ]
      else:
         return 0
   def getThicknesses(self):
      return self.thicknesses

#***************************************************
#  Image Processing
#***************************************************

def getHoughLines(img, numlines = 4, method = 1):
   """Largely taken from http://www.seas.upenn.edu/~bensapp/opencvdocs/ref/opencvref_cv.htm"""
   global DEBUGIMG
   linethresh = 300
   rhoGran = 1
   thetaGran = math.pi / 180
   minLen = 50
   maxGap = 10
   

   gray_img = cv.CreateMat(img.rows, img.cols, cv.CV_8UC1)
   cv.CvtColor(img, gray_img, cv.CV_RGB2GRAY)
   img = gray_img

   edges_img = cv.CreateMat(img.rows, img.cols, cv.CV_8UC1)
   cv.Canny(img, edges_img, 50, 200, 3)

   if method == 1:
      seq = cv.HoughLines2(edges_img, cv.CreateMemStorage(), cv.CV_HOUGH_STANDARD, rhoGran, thetaGran, linethresh)
      
      numLines = 0
      for line in seq:
         if numLines > numlines:
            break
         rho, theta = line

         a = math.cos(theta)
         b = math.sin(theta)
         x0 = a * rho
         y0 = b * rho

         p1x = x0 + 2000 * (-b)
         p1y = y0 + 2000 * (a)
         p1 = (p1x, p1y)

         p2x = x0 - 2000 * (-b)
         p2y = y0 - 2000 * (a)
         p2 = (p2x, p2y)


         cv.Line(DEBUGIMG, p1,p2, 200, thickness=5)

         numLines += 1

   elif method == 2:
      seq = cv.HoughLines2(edges_img, cv.CreateMemStorage(), cv.CV_HOUGH_PROBABILISTIC, rhoGran, thetaGran, linethresh, minLen, maxGap)
      
      numLines = 0
      for line in seq:
         if numLines > numlines:
            break
         p1, p2 = line


         cv.Line(DEBUGIMG, p1,p2, 200, thickness=5)

         numLines += 1




def resizeImage(img, scale = None):
   global NORMWIDTH
   if scale is None:
      targetWidth = NORMWIDTH
      realWidth = img.cols
      scale = targetWidth / float(realWidth) #rough scaling

   print "Scaling %s" % (scale)
   retImg = cv.CreateMat(int(img.rows * scale), int(img.cols * scale), img.type)
   cv.Resize(img, retImg)
   return retImg

def smooth(img, ksize = 9, t='median'):
   """Do a median smoothing with kernel size ksize"""
   retimg = cv.CloneMat(img)
   if t == 'gauss':
      smoothtype = cv.CV_GAUSSIAN
   else:
      smoothtype = cv.CV_MEDIAN
   #retimg = cv.CreateMat(img.cols, img.rows, cv.CV_8UC3)
   #                            cols, rows, anchorx,y, shape
   #kernel = cv.CreateStructuringElementEx(3,3, 1,1, cv.CV_SHAPE_RECT,
                                          #(0,1,0,1,0,1,0,1,0))
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
   
def getHistogramList(img, normFactor = 1000):
   """Returns a histogram of a GRAYSCALE image, normalized such that all bins add to 1.0"""
   retVector = []
   if img.type != cv.CV_8UC1:
      print "Error, can only get histogram of grayscale image"
      return retVector

   hist = cv.CreateHist( [255], cv.CV_HIST_ARRAY, [[0,255]], 1)
   cv.CalcHist([cv.GetImage(img)], hist)
   cv.NormalizeHist(hist, normFactor)
   gran = 5
   accum = 0
   for idx in xrange(0, 255):
      retVector.append(cv.QueryHistValue_1D(hist, idx))
   return retVector

def isForeGroundGone(img):
   debug = False
   hist = getHistogramList(img)
   histNorm = 1000
   foreGroundThresh = 80
   smudgeFactor = 35
   total = 0
   targetTotal = 0.7 * histNorm

   if sum(hist) == 0: #Empty image
      return True

   noForeground = False
   i = 254
   while i >= foreGroundThresh and total < targetTotal: #Add up hist values from white to black, but don't bother going past foreGroundThresh darkness
      total += hist[i]
      i -= 1

   #print "foreGroundThresh %s reached at %s" % (total, i)
   if total < targetTotal: #We didn't make it to the background
      #print "Total at %s is %s" % (i, total)
      return False

   #We have gotten past the peak of background
   #Come down the "peak"
   while i >= 0 and hist[i] >= 1.0:
      i -= 1
   lastNum = i
   #print "last num > 1 reached at %s" % (i)

   while i >= 0 and hist[i] > 0.0:
      i -= 1
   firstZero = i
   #print "first zero reached at %s" % (i)

   if lastNum - firstZero <= smudgeFactor:
      noForeground = True
      while i >= 0:
         if hist[i] > 0.0:
            noForeground = False
            break
         i -= 1

   return noForeground

         

   
      
   
   
class ImageStrokeCoverter(object):
   DEBUGIMG = None
   WIDTH = 1000 #Normalized width of an image
   #****************************
   # Status constants
   #****************************
   EMPTY = 0
   IMAGELOADED = 1
   STROKESEXTRACTED = 2
   #****************************
   # Image Processing constants
   #****************************
   BGVAL = 255 #Background color
   DENOISE_K = 5 / 1000.0
   SMOOTH_K  = 3 / 100.0
   INK_THRESH = 240
   def __init__(self, width = WIDTH):
      self._rawImg = None
      self._width = width
      self._state = ImageStrokeCoverter.EMPTY

   def loadImage(self, fname):
      self._state = ImageStrokeCoverter.EMPTY
      self._rawImg = cv.LoadImageM(fname)
      self._removeImageBackground()
      self._state = ImageStrokeCoverter.IMAGELOADED

   def getStrokes(self):
      if self._state >= ImageStrokeCoverter.IMAGELOADED:
         strokelist = blobsToStrokes(temp_img)
      else:
         return []

   def _removeImageBackground(self):
      """Take in a color image and convert it to a binary image of just ink"""
      #Hardcoded for resolution/phone/distance
      #tranScale = min (cv_img.cols / float(NORMWIDTH), NORMWIDTH)
      denoise_k = ImageStrokeCoverter.DENOISE_K
      smooth_k  = ImageStrokeCoverter.SMOOTH_K
      ink_thresh = ImageStrokeCoverter.INK_THRESH
      width = self._rawImg.cols

      denoise_k = max (1, int(denoise_k * width))
      if denoise_k % 2 == 0:
         denoise_k += 1
      smooth_k = max (1, int(smooth_k * width))
      if smooth_k % 2 == 0:
         smooth_k += 1

      inv_factor = 0.5
      gray_img = cv.CreateMat(self._rawImg.rows, self._rawImg.cols, cv.CV_8UC1)
      cv.CvtColor(self._rawImg, gray_img, cv.CV_RGB2GRAY)
      #Create histogram for single channel (0..255 range), into 255 bins
      bg_img = gray_img
      while not isForeGroundGone(bg_img):
         printHistogramList(getHistogramList(bg_img), granularity = 5)
         bg_img = smooth(bg_img, ksize=smooth_k, t='median')
         smooth_k = int(smooth_k * 1.1)
         if smooth_k % 2 == 0:
            smooth_k += 1

         saveimg(bg_img)
      #cv.EqualizeHist(bg_img, bg_img)
      #cv.EqualizeHist(gray_img, gray_img)
      bg_img = invert(bg_img)
      #gray_img = smooth(gray_img, ksize=denoise_k)

      saveimg(gray_img)
     
      cv.AddWeighted(gray_img, 1, bg_img, 1, 0.0, gray_img )
      saveimg(gray_img)
      #cv.EqualizeHist(gray_img, gray_img)
      gray_img = smooth(gray_img, ksize=denoise_k, t='gauss')
      saveimg(gray_img)
      cv.Threshold(gray_img, gray_img, ink_thresh, BGVAL, cv.CV_THRESH_BINARY)
      saveimg(gray_img)
      self._rawImg = gray_img
      #gray_img = smooth(gray_img, ksize=denoise_k)

      
def removeBackground(cv_img):
   """Take in a color image and convert it to a binary image of just ink"""
   global BGVAL
   #Hardcoded for resolution/phone/distance
   #tranScale = min (cv_img.cols / float(NORMWIDTH), NORMWIDTH)
   denoise_k = 5 / 1000.0
   smooth_k  = 3 / 100.0
   ink_thresh = 230
   width = cv_img.cols

   denoise_k = max (1, int(denoise_k * width))
   if denoise_k % 2 == 0:
      denoise_k += 1
   smooth_k = max (1, int(smooth_k * width))
   if smooth_k % 2 == 0:
      smooth_k += 1

   print "Foreground denoise kernel = %s x %s" % ( denoise_k, denoise_k)
   print "Background Median kernel = %s x %s" % ( smooth_k, smooth_k)

   inv_factor = 0.5
   gray_img = cv.CreateMat(cv_img.rows, cv_img.cols, cv.CV_8UC1)
   cv.CvtColor(cv_img, gray_img, cv.CV_RGB2GRAY)
   #Create histogram for single channel (0..255 range), into 255 bins
   bg_img = gray_img
   while not isForeGroundGone(bg_img):
      printHistogramList(getHistogramList(bg_img), granularity = 5)

      print "Background Median kernel = %s x %s" % ( smooth_k, smooth_k)
      bg_img = smooth(bg_img, ksize=smooth_k, t='median')
      smooth_k = int(smooth_k * 1.1)
      if smooth_k % 2 == 0:
         smooth_k += 1

      saveimg(bg_img)
   #cv.EqualizeHist(bg_img, bg_img)
   #cv.EqualizeHist(gray_img, gray_img)
   bg_img = invert(bg_img)
   #gray_img = smooth(gray_img, ksize=denoise_k)

   saveimg(gray_img)
  
   cv.AddWeighted(gray_img, 1, bg_img, 1, 0.0, gray_img )
   saveimg(gray_img)
   #cv.EqualizeHist(gray_img, gray_img)
   gray_img = smooth(gray_img, ksize=3, t='gauss')
   saveimg(gray_img)
   cv.Threshold(gray_img, gray_img, ink_thresh, BGVAL, cv.CV_THRESH_BINARY)
   saveimg(gray_img)
   #show(gray_img)
   #gray_img = smooth(gray_img, ksize=denoise_k)

   return gray_img




def blobsToStrokes(img):
   global DEBUGIMG, BGVAL
   print "Thinning blobs:"
   rawImg = cv.CloneMat(img)

   def AllPtsIter(w,h):
      for i in xrange(w):
         for j in xrange(h):
            yield (i, j)

   t1 = time.time()
   pointSet = AllPtsIter(img.cols, img.rows)
   t2 = time.time()
   print "Candidate Points generated %s ms" % (1000 * (t2 - t1))
         

   passnum = 1
   changed1 = True
   changed2 = True
   evenIter = True 
   while changed1 or changed2:
      print "Pass %s" % (passnum)
      saveimg(img)
      evenIter = (passnum %2 == 0)
      t1 = time.time()
      numChanged, pointSet, img = thinBlobsPoints(pointSet, img, cleanNoise = (passnum <= 2), evenIter = evenIter)
      t2 = time.time()
      print "Num changes = %s in %s ms" % (numChanged, (t2-t1) * 1000 )
      if passnum % 2 == 0:
         changed1 = numChanged > 0
      else:
         changed2 = numChanged > 0
      passnum += 1
   print ""
   numChanged, pointSet, img = thinBlobsPoints(pointSet, img, finalPass = True)

   saveimg(img)
   print "Tracing strokes"
   strokelist = pointsToStrokes(pointSet, rawImg)
   return strokelist

def imageToStrokes(filename):
   in_img = cv.LoadImageM(filename)
   small_img = resizeImage(in_img)
   temp_img = removeBackground(small_img)
   strokelist = blobsToStrokes(temp_img)
   return strokelist
      



      

def processStrokes(cv_img):
   """Take in a raw, color image and return a list of strokes extracted from it."""

   global DEBUGIMG, BGVAL

   #show(cv_img)
   small_img = resizeImage(cv_img)
   #small_img = cv.CloneMat(cv_img)

   #getHoughLines(small_img)

   temp_img = removeBackground(small_img)
   DEBUGIMG = cv.CloneMat(temp_img)
   #cv.Set(DEBUGIMG, 255)

   
   #DEBUGIMG = cv.CreateMat(DEBUGSCALE * temp_img.rows, DEBUGSCALE * temp_img.cols, cv.CV_8UC1)
   cv.Set(DEBUGIMG, 255)
   strokelist = blobsToStrokes(temp_img)
      
   #DEBUGIMG = cv.CloneMat(temp_img)
   #cv.Set(DEBUGIMG, 255)
   
   cv.Set(temp_img, BGVAL)
   pointsPerFrame = 5
   numPts = 0
   strokelist.sort(key = (lambda s: s.center[1] * 10 + s.center[0]) ) 
   lineColor =  0
   startColor = 128
   stopColor = 220
   thicknesses = []
   for s in strokelist:
      prev = None
      #t = s.getThickness()
      t = 1
      #print "Stroke thickness = %s" % (t)
      thicks = s.getThicknesses()
      thicknesses.extend(thicks)
      for i, p in enumerate(s.getPoints()):
         #t = int(thicks[i] / 2)
         debugPt = ( DEBUGSCALE * p[0], DEBUGSCALE * p[1])
         setImgVal(DEBUGSCALE * p[0], DEBUGSCALE * p[1], 0, temp_img)
         if prev is not None:
            pass
            cv.Line(temp_img, prev, debugPt, lineColor, thickness=t)
            #cv.Line(temp_img, prev, debugPt, 0, thickness=2)
            #saveimg (temp_img)
         else:
            pass
            cv.Circle(temp_img, debugPt, 1, startColor, thickness=-1)
            #saveimg(temp_img)
         numPts += 1
         prev = debugPt
         if numPts % pointsPerFrame == 0:
            pass
            #saveimg(temp_img)
            #if numPts % (5 * pointsPerFrame) == 0:
               #cv.Set(temp_img, 255)
      cv.Circle(temp_img, debugPt, 1, stopColor, thickness=-1)
      saveimg(temp_img)

   print "Average line thickness : %s" % ( sum(thicknesses) / len(thicknesses) )

   return temp_img

def pointDist(p1, p2):
   p1x, p1y = p1
   p2x, p2y = p2

   return (p2x-p1x) ** 2 + (p2y-p1y) ** 2

def show(cv_img):
   if cv_img.type == cv.CV_8UC1:
      Image.fromstring("L", cv.GetSize(cv_img), cv_img.tostring()).show()
   elif cv_img.type == cv.CV_8UC3:
      Image.fromstring("RGB", cv.GetSize(cv_img), cv_img.tostring()).show()
   saveimg(cv_img)
   

def saveimg(cv_img, outdir = "./temp/"):
   global FNAMEITER
   if __name__ == '__main__':
      outfname = outdir + FNAMEITER.next()
      print "Saving %s"  % outfname

      cv.SaveImage(outfname, cv_img)

def main(args):
   global SQUARE_ERROR, PRUNING_ERROR
   if len (args) < 2:
      print( "Usage: %s <image_file> [output_file]" % (args[0]))
      exit(1)

   fname = args[1]

   if len(args) > 2:
      outfname = args[2]
   else:
      outfname = None


   in_img = cv.LoadImageM(fname)
   print "Processing image %sx%s" % (getWidth(in_img), getHeight(in_img))
   out_img = processStrokes(in_img)
   saveimg(out_img)
   
   if outfname is not None:
      print "Saving to %s" % (outfname)
      cv.SaveImage(outfname, out_img)

   #show(out_img)




if __name__ == "__main__":
   import sys
   main(sys.argv)
   #test()


