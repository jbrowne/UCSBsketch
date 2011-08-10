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
"""
class Blob(object):
   BLOBCOLOR = 128
   SKELETONCOLOR = 0
   def __init__(self):
      self.rawpixels = set([])
      self.thinpixels = None
      self.tree = {}
      self.treeRoot = None
   def addPixel(self, p):
      self.rawpixels.add(p)

   def draw(self, img):
      for x,y in self.rawpixels:
         img[y,x] = Blob.BLOBCOLOR
      if self.thinpixels is not None:
         for x,y in self.thinpixels:
            img[y,x] = Blob.SKELETONCOLOR

   def thin(self):
      global DEBUGIMG
      self.thinpixels = set(self.rawpixels)
      changed1 = True
      changed2 = True
      passNum = 0
      while changed1 or changed2:
         self.draw(DEBUGIMG)
         saveimg(DEBUGIMG)
         evenIter = ( passNum % 2 == 0 )
         numChanged, self.thinpixels = self._thinByOneLayer(cleanNoise = False, evenIteration = evenIter)
         print "Pass %s: %s changes" % (passNum, numChanged)
         if evenIter:
            if numChanged > 0:
               changed1 = True
            else:
               changed1 = False
         else:
            if numChanged > 0:
               changed2 = True
            else:
               changed2 = False
         passNum += 1
      self.draw(DEBUGIMG)
      saveimg(DEBUGIMG)

   def _thinByOneLayer(self, cleanNoise = False, evenIteration = False, finalPass = False):
      minFill = 3
      maxFill = 6
      retPoints = set([])
      numChanged = 0
      if cleanNoise:
         noise = 2
         #minFill = 1
      else:
         noise = -1
         #minFill = 3
      for p in self.thinpixels:
         i,j = p
         valDict = _filledAndCrossingVals2(p, self.thinpixels, skipCorners = False)
         filled = valDict['filled']
         cnum_p = valDict['crossing']

         if evenIteration:
            badEdge = valDict['esnwne']
         else:
            badEdge = valDict['wnsesw']

         if (filled >= minFill and filled <= 6 and cnum_p == 1 and (not badEdge or finalPass) ) or \
            (filled == noise): 
            numChanged += 1

         elif filled >= 2:
            retPoints.add(p)
      return numChanged, retPoints



def printSetPoint(pt, pointSet):
   x, y = pt

   pixval = (x,y) in pointSet
   n = (x , y + 1) in pointSet
   s = (x , y - 1) in pointSet
   e = (x + 1 , y) in pointSet
   w = (x - 1 , y) in pointSet
   ne = (x + 1 , y + 1) in pointSet
   se = (x + 1 , y - 1) in pointSet
   nw = (x - 1 , y + 1) in pointSet
   sw = (x - 1 , y - 1) in pointSet

   chars = (' ', '#')
   print "--------------------------"
   for row in [ [nw, n, ne], [w, pixval, e], [sw, s, se] ]:
      print "\t|",
      for val in row:
         print "%s" % (chars[int(val)]),
      print "|"
   print "--------------------------"
      


def blobsFromImage(cv_img):
   global CENTERVAL, DEBUGIMG
   procQueue = [ (Blob(), (-1, -1)) ]
   seen = set([])
   width = cv_img.cols
   height = cv_img.rows

   allBlobs = set([])
   #totalPixels = 0
   while len(procQueue) > 0:
      blob, pt = procQueue.pop()
      x,y = pt
      #print "Processing point %s" % (str(pt))
      n = (x , y + 1)
      s = (x , y - 1)
      e = (x + 1 , y)
      w = (x - 1 , y)
      ne = (x + 1 , y + 1)
      se = (x + 1 , y - 1)
      nw = (x - 1 , y + 1)
      sw = (x - 1 , y - 1)
      for nPt in [n, s, e, w, ne, nw, se, sw]:
         nx, ny = nPt
         if nPt not in seen and nx >= 0 and nx < width and ny >= 0 and ny < height:
            #Check to see if it's part of the current blob
            if cv_img[ny,nx] == CENTERVAL:
               blob.addPixel(nPt)
               allBlobs.add(blob)
               procQueue.append( (blob, nPt) ) #process this next
            else:
               procQueue.insert(0, (Blob(), nPt) ) #Otherwise process it after all the black pixels
         seen.add(nPt)
   #print allBlobs

   return allBlobs
      
   
"""

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
# Bitmap thinning functions
#***************************************************
def pointsDistSquared (pt1, pt2):
   x1, y1 = pt1
   x2, y2 = pt2

   return (x1 - x2) ** 2 + (y1 - y2) ** 2

def pointsToTrees(pointSet, rawImg):
   global DEBUGIMG
   cv.Set(DEBUGIMG, 255)
   linkDict = {}
   seen = {}
   allKeyPoints = []
   print "Converting points to strokes"

   numStrokes = 0
   while len(pointSet) > 0:
      print "%s points left to process" % (len(pointSet))
      numStrokes += 1
      seed = pointSet.pop()
      procStack = [ {'pt' :seed, 'leafDist' : 0, 'parent': None, 'path': []} ]
      seen[seed] = set([])
      #cv.Circle(DEBUGIMG, seed, 2, 128, thickness=-1)
      
      crossPoints = set([])
      endPoints = set([])


      maxLeaf = seed
      maxDist = 0

      #Initial pass to build the a linkDict tree from some seed point
      while len(procStack) > 0:
         procDict = procStack.pop(0)
         pt = procDict['pt']
         dist = procDict['leafDist']
         parPt = procDict['parent'] 
         parPath = procDict['path']
         (x,y) = pt
         #setImgVal(x,y,220, DEBUGIMG)

         pointOutOfRange = False
         if parPt is None:
            pointOutOfRange = True
         else:
            distSqr = pointsDistSquared(parPt, pt) 
            parThicknessSqr = (linkDict[parPt]['thickness'] / 2.0) ** 2
            ptThicknessSqr = (pointThickness(pt, rawImg) / 2.0) ** 2
            if parThicknessSqr < distSqr and ptThicknessSqr < distSqr:
               pointOutOfRange = True

         if pointOutOfRange:
            #Add this point to the linkdict
            if dist > maxDist:
               maxLeaf = (x,y)
               maxDist = dist
            #setImgVal(pt[0], pt[1], 128, DEBUGIMG)
            thickness = pointThickness(pt, rawImg)
            ptDict = linkDict.setdefault( pt , {'kids' : set([]), 'thickness' : thickness } )
            #cv.Circle(DEBUGIMG, pt, linkDict[pt]['thickness']/ 2.0, 128, thickness=-1)
            #Link the two points together
            if parPt is not None:
               ptDict['kids'].add(parPt)
               linkDict[parPt]['kids'].add(pt)
            parPt = pt
            parPath = []
            #Go through this point to get to its siblings (added previous round)
            for siblingDict in procStack:
               ptThickness = linkDict[pt]['thickness'] ** 2
               if pointsDistSquared(pt, siblingDict['pt']) < ptThickness:
                  siblingDict['parent'] = pt
                  siblingDict['path'] = [pt]


         parPath.append(pt)

         n = (x , y + 1)
         s = (x , y - 1)
         e = (x + 1 , y)
         w = (x - 1 , y)
         ne = (x + 1 , y + 1)
         se = (x + 1 , y - 1)
         nw = (x - 1 , y + 1)
         sw = (x - 1 , y - 1)
         fourNbors = [ n, e, s, w ]

         eightNbors = fourNbors + [ne, se, nw, sw]
         random.shuffle(eightNbors)

         for nPt in eightNbors:
            if nPt in pointSet and nPt not in seen:
                  procStack.append({'pt' :nPt, 'leafDist' : dist + 1, 'parent': parPt, 'path' : parPath} )
                  pointSet.remove(nPt)
            #elif (npt in linkdict and npt != parpt and npt not in linkdict[parpt]['kids']):
               #linkdict[nPt]['kids'].add(parpt)
               #linkdict[parpt]['kids'].add(npt)

            seen.setdefault(nPt, set([])).add(parPt)
         #saveimg(DEBUGIMG)

      #endWhile len(procStack)
      """
      for p, pdict in linkDict.items():
         for k in pdict['kids']:
            cv.Line(DEBUGIMG, p, k, 220, thickness = 1)
            setImgVal(p[0], p[1], 128, DEBUGIMG)
            setImgVal(k[0], k[1], 128, DEBUGIMG)

      saveimg(DEBUGIMG)
      """
      for pt, parset in seen.items():
         for par1 in parset:
            for par2 in parset:
               if par1 == par2:
                  continue
               else:
                  if par2 not in linkDict[par1]['kids']:
                     print "Discontinuity: %s and %s" % (par1, par2)
                     assert par1 in linkDict and par2 in linkDict, "Uh oh"
                     linkDict[par1]['kids'].add(par2)
                     linkDict[par2]['kids'].add(par1)
                     #cv.Circle(DEBUGIMG, par1, 1, 0, thickness=-1)
                     #cv.Line(DEBUGIMG, par1, par2, 0, thickness = 1)
                     #cv.Circle(DEBUGIMG, par2, 1, 0, thickness=-1)

      #The tree is hooked together, and needs to be pruned

      #collapseCrossingPoints(keyPoints, linkDict)
      endPoints, crossPoints = getKeyPoints(linkDict, endPoints, maxLeaf)
      """

      for debugPt in (endPoints) :
         setImgVal(pt[0], pt[1], 128, DEBUGIMG)
         cv.Circle(DEBUGIMG, debugPt, 1, 128, thickness=-1)
      saveimg(DEBUGIMG)
      for debugPt in list(crossPoints):
         setImgVal(pt[0], pt[1], 128, DEBUGIMG)
         cv.Circle(DEBUGIMG, debugPt, 1, 128, thickness=-1)
      saveimg(DEBUGIMG)
      """


      allKeyPoints.append( {'crosses' : list(crossPoints), 'ends' :list(endPoints)} ) #Pair crosspoints with endpoints

   #endwhile PointSet > 0

   #saveimg(DEBUGIMG)
   return {'trees' : linkDict, 'keypoints' : allKeyPoints}

def getKeyPoints(tree, seeds, leaf):
   #global DEBUGIMG

   endPoints = set(seeds)
   crossPoints = set()
   #collapseCrossingPoints(keyPoints, linkDict):
   #collapseCrossingAndEndPoints(crossPoints, endPoints, linkDict)

   seen = set([])
   maxPath = [leaf]
   procStack = [ (leaf, maxPath) ]
   while len(procStack) > 0:
      pt, path = procStack.pop()
      #print "Pt %s" % (str(pt))
      if len(path) >=2:
         p1 = path[-2]
         p2 = path[-1]
         #cv.Line(DEBUGIMG, p1,p2, 0, thickness=1)
         p1col = p2col = 128
         if len(tree[p1]['kids']) > 2:
            p1col = 50
            p2col = 220
         if len(tree[p2]['kids']) > 2:
            if p1col != 50:
               p1col = 220
            p2col = 50
         #setImgVal(p1[0], p1[1], p1col, DEBUGIMG)
         #setImgVal(p2[0], p2[1], p2col, DEBUGIMG)
      if pt not in seen:
         seen.add(pt)

         if len(path) > len(maxPath):
            maxPath = path
         for k in tree[pt]['kids']:
            procStack.append( (k, path + [k]) )

      if len(tree[pt]['kids']) == 1:
         endPoints.add(pt)
      elif len(tree[pt]['kids']) > 2:
         crossPoints.add(pt)

   if len(endPoints) == 0: #No real endpoints, have to fake some
      #Search for the farthest away point from here
      endPoints.add(maxPath[-1])
      endPoints.add(maxPath[0])
   #saveimg(DEBUGIMG)
   return list(endPoints), list(crossPoints)

def collapseCrossingPoints(keyPoints, linkDict):
   assert False, "This function not yet working"
   endPoints = keyPoints['ends']
   crossPoints = keyPoints['crosses']
   collapsedPoints = set([])
   #Find out what nodes all collapse together
   for cp in crossPoints:
      if cp not in linkDict:
         continue

      thickness = linkDict[cp]['thickness']
      collapsedPoints = set([])
      procStack = [( cp, 0 )]
      while len(procStack) > 0:
         pt, depth = procStack.pop()
         collapsedPoints.add(pt)
         if depth < thickness / float(2):
            for k in linkDict[pt]['kids']:
               procStack.append( (k, depth +1) )

      #collapsedPoints contains all of the points to be merged
      numPts = len(collapsedPoints)
      avgPoint = None
      nBorPts = set([])
      for p in collapsedPoints:
         pWeightX = p[0] / float(numPts)
         pWeightY = p[1] / float(numPts)
         if avgPoint == None:
            avgPoint = [pWeightX, pWeightY]
         else:
            avgPoint[0] += pWeightX
            avgPoint[1] += pWeightY

         if p in collapsedPoints:
            nBorPts.add(p)
         elif p in linkDict:
            nBors = removeFromTreeDict(p, linkDict) 
            nBorPts.update(nBors)

      #points are removed from the tree, and the collapsed point is figured from the average

      avgPoint = tuple(avgPoint)
      avgPtDict = linkDict.setdefault(avgPoint, {'kids' : set([]), 'thickness' : None})
      avgPtDict['thickness'] = thickness
      for npt in nBorPts:
         if npt in linkDict: #Might have been removed earlier
            avgPtDict['kids'].add(npt)
            linkDict[npt]['kids'].add(avgPoint)
      if len(nBorPts) == 1: #May have created an endpoint
         endPoints.append(avgPoint)
   #endFor cp in crossPoints
   for ep in list(endPoints):
      if ep not in linkDict:
         endPoints.remove(ep)
      elif len(linkDict[ep]['kids']) != 1:
         endPoints.remove(ep)

def removeFromTreeDict(point, treeDict):
   if point in treeDict:
      kidlist = treeDict[pt]['kids']
      for k in kidlist:
         assert k in treeDict, "Removing point with invalid 'kids'"
         assert point in treeDict[k], "Removing point but neighbor doesn't know about it"
         treeDict[k]['kids'].remove(point)
      del(treeDict[pt])
      return kidlist
   else:
      print "Warning: Trying to remove point not present in treeDict"

         

def collapseCrossingAndEndPoints(crossPoints, endPoints, linkDict):
   """Destructively collapses intersection points within the link tree"""
   #Collapse internal nodes. Also prunes single-point subtrees
   for ePt in list(endPoints):
      if ePt in linkDict:
         #print "Checking endpoint: %s\n  %s" % (ePt, linkDict[ePt])
         kidlist = list(linkDict[ePt]['kids'])
         for kid in kidlist:
            if kid in endPoints:
               continue #Leave 2-coupled line segs alone, since only one child, same as BREAK
            if kid in crossPoints:
               crossPoints.remove(kid)

            linkDict[ePt]['kids'].remove(kid) #Remove mutual connection
            linkDict[kid]['kids'].remove(ePt)
            #print "  ", kid, linkDict[kid]
            gkidlist = list(linkDict[kid]['kids'])
            for gkid in gkidlist:
               #print "    ", gkid, linkDict[gkid]
               linkDict[gkid]['kids'].remove(kid) #Link grandkid to this point
               linkDict[gkid]['kids'].add(ePt)
               linkDict[ePt]['kids'].add(gkid)
               #print "    ", gkid, linkDict[gkid], "After"
            del(linkDict[kid])

         if len(linkDict[ePt]['kids']) != 1:
            assert len(linkDict[ePt]) != 0 #Sanity check
            #print "After collapse, %s no longer endpoint\n   %s" % (ePt, linkDict[ePt])
            endPoints.remove(ePt)
         if len(linkDict[ePt]['kids']) > 2:
            crossPoints.add(ePt)
            #print "   Removing %s" % (str(kid))

   for kPt in list(crossPoints):
      if kPt in linkDict and kPt in crossPoints:
         #print kPt, linkDict[kPt] 
         kidlist = list(linkDict[kPt]['kids'])
         for kid in kidlist:
            linkDict[kPt]['kids'].remove(kid) #Remove mutual connection
            linkDict[kid]['kids'].remove(kPt)
            #print "  ", kid, linkDict[kid]
            gkidlist = list(linkDict[kid]['kids'])
            for gkid in gkidlist:
               #print "    ", gkid, linkDict[gkid]
               linkDict[gkid]['kids'].remove(kid) #Link grandkid to this point
               linkDict[gkid]['kids'].add(kPt)
               linkDict[kPt]['kids'].add(gkid)
               #print "    ", gkid, linkDict[gkid], "After"
            #print "   Removing %s" % (str(kid))
            if kid in endPoints:
               endPoints.remove(kid)
            if kid in crossPoints:
               crossPoints.remove(kid)
            crossPoints.add(kPt)
            del(linkDict[kid])

         if len(linkDict[kPt]['kids']) <= 2:
            assert len(linkDict[kPt]) != 0 #Sanity check
            crossPoints.remove(kPt)
         if len(linkDict[kPt]['kids']) <= 1:
            endPoints.add(kPt)
         #print kPt, linkDict[kPt], "After"

def pointThickness(point, img):
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
   




def pointsToStrokes(pointSet, rawImg):
   global DEBUGIMG
   trees = pointsToTrees(pointSet, rawImg)
   for p, pdict in trees['trees'].items():
      for k in pdict['kids']:
         cv.Line(DEBUGIMG, p, k, 220, thickness = 1)
         setImgVal(p[0], p[1], 128, DEBUGIMG)
         setImgVal(k[0], k[1], 128, DEBUGIMG)

   saveimg(DEBUGIMG)
   """
   for keypts in trees['keypoints']:
      for pt in keypts['crosses']:
         cv.Circle(DEBUGIMG, pt, 1, 128, thickness=2)
      for pt in keypts['ends']:
         cv.Circle(DEBUGIMG, pt, 1, 50, thickness=2)
   """
   retStrokes = pointtreesToStrokes(trees['keypoints'], trees['trees'])
   return retStrokes


def pointtreesToStrokes(keyPoints, linkDict):
   global DEBUGIMG
   #Build up smaller link graph of intersection points and end points
   
   retStrokes = []
   for strokeDict in keyPoints:
      if len(strokeDict['ends']) + len(strokeDict['crosses']) == 1:
         singlePoint = (strokeDict['ends'] + strokeDict['crosses'])[0] 
         stroke = Stroke()
         stroke.addPoint( singlePoint, linkDict[singlePoint]['thickness'])
         retStrokes.append(stroke)
         continue
      endPoints = list(strokeDict['ends'])
      crossingPoints = list(strokeDict['crosses'])
      
      #print "Crosses: %s\nEnds: %s" % (crossingPoints, endPoints)
      seen = {}
      strokeGraph = {}
      seed = endPoints[0]
      endPoints.remove(seed)
      seen[seed] = True
      #print "Seed: %s" % (str(seed))
      procStack = []
      for k in linkDict[seed]['kids']:
         procStack.append( (k, [seed] ) ) #point, parent vertex

      while len(procStack) > 0:
         curPt, links = procStack.pop()
         if curPt in seen:
            continue
         links.append(curPt)

         if curPt in endPoints or curPt in crossingPoints: #Did we just reach a vertex?
            src = links[0]
            dest = links[-1]
            #print "Path found from %s to %s" % (src, dest)
            #print "Links: %s" % (links)
            prev = None
            for i in xrange( len(links)): #Set each dest pointer to the next in line
               edgePt = links[i]
               ptDict = strokeGraph.setdefault(edgePt, {})
               if i < len(links) - 1:
                  ptDict[dest] = links[i + 1]
               if prev is not None: #set each src pointer to the previous
                  ptDict[src] = prev
               prev = edgePt
            #links = [curPt]
            if curPt in endPoints:
               endPoints.remove(curPt)
            if curPt in crossingPoints:
               crossingPoints.remove(curPt)

            seen[curPt] = True
            for k in linkDict[curPt]['kids']:
               if k not in seen:
                  procStack.append( (k, [curPt]) )

         #endif curPt 
         elif curPt not in seen: #Keep searching down the tree
            seen[curPt] = True
            for k in linkDict[curPt]['kids']:
               procStack.append( (k, links) )
      #endWhile
      #Now have a graph for the stroke(s)

      #continue


      endPoints = list(strokeDict['ends'])
      crossingPoints = list(strokeDict['crosses'])
      #for cp in crossingPoints:
      procList = crossingPoints + endPoints
      seen = {}
      while len(procList) > 0:
         cp = procList.pop()
         seen[cp] = True

         for dest in strokeGraph[cp].keys():
            if dest in seen:
               continue
            stroke = Stroke()
            pt = cp
            while dest in strokeGraph[pt]:
               stroke.addPoint(pt, linkDict[pt]['thickness'])
               pt = strokeGraph[pt][dest]

            assert pt == dest
            stroke.addPoint(dest, linkDict[dest]['thickness'])
            retStrokes.append(stroke)
            #print "New stroke %s to %s" % (cp, dest)
      





   return retStrokes


def buildStrokeFromVertices(vertices, strokeGraph):

   retStroke = Stroke()
   prev = None
   target = None
   while len(vertices) > 0:
      prev = target
      target = vertices.pop()
      if prev == None:
         continue

      while pt != target:
         if pt != target:
            retStroke.addPoint(pt)
            pt = strokeGraph[pt][target]
   if target is not None:
      retStroke.addPoint(target) #Add that last vertex point

   return retStroke

   

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

def angularDistance(p1, p2, p3):
   p1x, p1y = p1
   p2x, p2y = p2
   p3x, p3y = p3

   Xvect = ( (p1x - p2x) , (p1y - p2y) )
   Yvect = ( (p3x - p2x) , (p3y - p2y) )
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


   
def _filledAndCrossingVals2(point, pointSet, skipCorners = False):

   retDict = {'filled':0, 'crossing':0}
   if point in pointSet:
      crossing = 0
      filled = 1
      px, py = point

      n = (px , py + 1) in pointSet
      s = (px , py - 1) in pointSet
      e = (px + 1 , py) in pointSet
      w = (px - 1 , py) in pointSet
      ne = (px + 1 , py + 1) in pointSet
      se = (px + 1 , py - 1) in pointSet
      nw = (px - 1 , py + 1) in pointSet
      sw = (px - 1 , py - 1) in pointSet

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
         prevFilled = ptFilled

      retDict['filled'] = filled
      retDict['crossing'] = crossing
      


      eEdge = (not ne and not e and not se and s)
      sEdge = (not ne and not e and not se and s)
      nwEdge = (not w  and not n and (sw and ne) )
      neEdge = (not e  and not n and (se and nw) ) 

      wEdge = (not nw and not w and not sw and n)
      nEdge = (not nw and not n and not ne and w)
      seEdge = (not s and not e and (ne and sw) )
      swEdge = (not s and not w and (se and nw) )

      esnwne = eEdge or sEdge or nwEdge or neEdge
      wnsesw = wEdge or nEdge or seEdge or swEdge


      retDict['esnwne'] = esnwne
      retDict['wnsesw'] = wnsesw
   #endif
   return retDict
      
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
      sEdge = (not ne and not e and not se and s)
      nwEdge = (not w  and not n and (sw and ne) )
      neEdge = (not e  and not n and (se and nw) ) 

      wEdge = (not nw and not w and not sw and n)
      nEdge = (not nw and not n and not ne and w)
      seEdge = (not s and not e and (ne and sw) )
      swEdge = (not s and not w and (se and nw) )

      esnwne = eEdge or sEdge or nwEdge or neEdge
      wnsesw = wEdge or nEdge or seEdge or swEdge


      retDict['esnwne'] = esnwne
      retDict['wnsesw'] = wnsesw
   #endif
   return retDict

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
   outImg = img #Edit inline

   if cleanNoise:
      minFill = 3
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
      elif filled > 2:
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

         

   
      
   
   
def removeBackground(cv_img):
   """Take in a color image and convert it to a binary image of just ink"""
   global BGVAL, NORMWIDTH
   #Hardcoded for resolution/phone/distance
   #tranScale = min (cv_img.cols / float(NORMWIDTH), NORMWIDTH)
   denoise_k = 5 / 1000.0
   smooth_k  = 3 / 100.0
   ink_thresh = 240 
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
      bg_img = smooth(bg_img, ksize=smooth_k)
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
   cv.Threshold(gray_img, gray_img, ink_thresh, BGVAL, cv.CV_THRESH_BINARY)
   saveimg(gray_img)
   #gray_img = smooth(gray_img, ksize=denoise_k)

   """
   itr = 0
   bg_img = cv.CloneMat(gray_img)
   while not isForeGroundGone(bg_img):
      itr += 1
      #print "Iteration %s" % (itr)
      #printHistogramList(getHistogramList(bg_img), granularity = 5)

      #print "Background Median kernel = %s x %s" % ( smooth_k, smooth_k)
      bg_img = smooth(gray_img, ksize= (2 * itr + 1))

      saveimg(bg_img)

   print "Foreground disappeared in %s iterations" % (itr)
   saveimg(bg_img)
   """

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
   saveimg(img)
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
      #cv.Circle(temp_img, debugPt, t/2, stopColor, thickness=-1)
      #saveimg(temp_img)

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
   

def fname_iter():
   imgnum = 0
   while True:
      fname = "%06.0d.jpg"
      print fname
      imgnum += 1
      yield None

def animimg(cv_img):
   """BROKEN"""
   global VIDEO_WRITER
   if VIDEO_WRITER is None:
      size = (cv_img.cols, cv_img.rows)
      init_video(size = size)
   if cv_img.type != cv.CV_8UC1:
      temp_img = cv.CreateMat(cv_img.rows, cv_img.cols, cv.CV_8UC1)
      cv.CvtColor(cv_img, temp_img, cv.CV_RGB2GRAY)
      cv_img = temp_img

   iplImg = cv.GetImage(cv_img)
   print iplImg
   cv.WriteFrame(VIDEO_WRITER, iplImg)

def init_video(size = (800, 600), fname = "./vid.mpg"):
   global VIDEO_WRITER
   fps = 30
   VIDEO_WRITER = cv.CreateVideoWriter (fname, cv.CV_FOURCC('M', 'P', 'E', 'G'), fps, size, 0)
   print "Saving video to %s at %s" % (fname, size)

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
