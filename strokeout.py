#!/usr/bin/env python
import cv
import Image
import pickle
import random
import pdb
import random

FILLEDVAL = 220
CENTERVAL = 0
BGVAL = 255
COLORFACTOR = 10

DENOISE_K = 5
SMOOTH_K = 23
INV_FACTOR = 0.5
INK_THRESH = 122

PRUNING_ERROR = 0.2
SQUARE_ERROR = 0.2
PRUNING_ERROR = PRUNING_ERROR * SQUARE_ERROR

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

def pointsToStrokes(points):
   linkDict = {}
   retStrokes = []
   for (x,y) in points:
      n = (x , y + 1)
      s = (x , y - 1)
      e = (x + 1 , y)
      w = (x + 1 , y)
      ne = (x + 1 , y + 1)
      se = (x + 1 , y - 1)
      nw = (x + 1 , y + 1)
      sw = (x + 1 , y - 1)
      fourNbors = [ n, e, s, w ]
      eightNbors = fourNbors + [ne, se, nw, sw]

      #Link the neighbor points together
      ptDict = linkDict.setdefault( (x,y) , {'kids' : [] } )
      for nPt in eightNbors:
            nborDict = linkDict.setdefault(nPt, {'kids' : [] } )
            nborDict['kids'].append( (x,y) )
            ptDict['kids'].append(nPt)
      linkDict[ (x,y) ] = ptDict
   #endfor

   print "Link Tree generated"
   #linkDict is now a bunch of trees, each with one representative pt in reps
   while len(linkDict) > 0:
      #Get a good start point
      r, linkNode = linkDict.items()[0]
      procStack = [(r, 0)]
      maxLeaf = r
      maxDist = 0
      seen = {}
      while len(procStack) > 0:
         pt, dist = procStack.pop()

         seen[pt] = True
         if dist > maxDist:
            maxLeaf = pt
            maxDist = dist
         for k in linkDict[pt]['kids']:
            if k != pt and k not in seen:
               procStack.append( (k, dist + 1) )
      #endwhile
      print "Found a good leaf, depth %s" % (maxDist)

      #Build up a stroke
      strk = Stroke()
      procStack = [maxLeaf]
      seen = {}
      while len(procStack) > 0:
        pt = procStack.pop()
        seen[pt] = True
        if pt in linkDict: #Otherwise, already processed
           strk.addPoint(pt)
           kids = linkDict[pt]['kids']
           del(linkDict[pt])
           for k in kids:
               if k in linkDict and k not in seen:
                  procStack.append( k )
      #endwhile
      print "Created a stroke"

      retStrokes.append(strk)
   #endfor

   return retStrokes

   
def filledAndCrossingVals(point, img):
   """
   http://fourier.eng.hmc.edu/e161/lectures/morphology/node2.html
   """
   global CENTERVAL, BGVAL
   retDict = {'filled':0, 'crossing':-1, 'esnwne': False, 'wnsesw': False}
   px, py = point

   pixval = getImgVal(px, py, img)
   if pixval == CENTERVAL:
      crossing = 0
      filled = 1

      nw = getImgVal(px-1, py+1, img) == CENTERVAL
      n = getImgVal(px, py+1, img) == CENTERVAL
      ne = getImgVal(px+1, py+1, img) == CENTERVAL

      w = getImgVal(px-1, py, img) == CENTERVAL
      #pixval = getImgVal(px, py, img) == CENTERVAL
      e = getImgVal(px+1, py, img) == CENTERVAL

      sw = getImgVal(px-1, py-1, img) == CENTERVAL
      s = getImgVal(px, py-1, img) == CENTERVAL
      se = getImgVal(px+1, py-1, img) == CENTERVAL
      #counterclockwise crossing
      proclist = [ne, n, nw, w, sw, s, se, e]

      #First point val
      prevFilled = e
      #print "Neighbors:\n  ",
      for ptFilled in proclist:
         if ptFilled:
            filled += 1
         if prevFilled and not ptFilled:
            crossing += 1
         #print "%s, " % (ptVal),
         prevFilled = ptFilled
      #print "\n%s filled, %s crossing" % (filled, crossing)
      retDict['filled'] = filled
      retDict['crossing'] = crossing
      
      esnwne = (not ne and not e and not se and s) or \
      (not sw and not s and not se and e) or \
      (not w and not n and sw and ne) or \
      (not e and not n and se and nw)

      wnsesw = (not nw and not w and not sw and n) or \
      (not nw and not n and not ne and w) or \
      (not s and not e and ne and sw) or \
      (not s and not w and se and nw)

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

def thinBlobsPoints(points, img, evenIter = True, dir = 0):
   global DEBUGIMG, FILLEDVAL, BGVAL
   outImg = cv.CloneMat(img)
   retPoints = []
   changed = False
   print "Thinning blobs"
   for p in points:
      (i,j) = p
      valDict = filledAndCrossingVals(p, img)
      filled = valDict['filled']
      cnum_p = valDict['crossing']
      if evenIter:
         badEdge = valDict['esnwne']
      else:
         badEdge = valDict['wnsesw']

      if filled >= 3 and filled <= 6 and cnum_p == 1 and not badEdge: 
         changed = True
         #printPoint(p, img)
         #printPoint(p, img)
         #setImgVal(i, j, 220, outImg)
         setImgVal(i, j, FILLEDVAL, outImg)
      elif filled > 1:

         retPoints.append(p)
   saveimg(outImg)

   return ( changed, retPoints, outImg )


#***************************************************
#Square filling + helper functions
#***************************************************

def fillSquares(startPoint, img, squareFill=FILLEDVAL):
   """Get a list of squares filling a blob starting at startPoint.
   Overwrites the blob with squareFill value"""

   centersTree = {}

   returnSquares = []
   squareSeeds = [(startPoint, None, 'E')] #Start looking east

   while len(squareSeeds) > 0:
      seedPt, parentPt, direction = squareSeeds.pop()
      #print "Checking %s for square" % (str(seedPt))
      dirs = []
      if direction == 'NW':
         dirs.append('NW')
         dirs.append('NE')
         dirs.append('SW')
      elif direction == 'N':
         dirs.append('NW')
         dirs.append('NE')
      elif direction == 'NE':
         dirs.append('NW')
         dirs.append('NE')
         dirs.append('SE')
      elif direction == 'SE':
         dirs.append('SE')
         dirs.append('NE')
         dirs.append('SW')
      elif direction == 'S':
         dirs.append('SE')
         dirs.append('SW')
      elif direction == 'SW':
         dirs.append('SE')
         dirs.append('SW')
         dirs.append('NW')
      elif direction == 'W':
         dirs.append('SW')
         dirs.append('NW')
      elif direction == 'E':
         dirs.append('SE')
         dirs.append('NE')
      else:
         dirs = ['NW','NE','SE','SW']
      newSquare = growSquare(seedPt, img, dirs)
      if newSquare is not None:
         returnSquares.append(newSquare)
         squareNum = len(returnSquares)

         p1x, p1y = newSquare[0]
         p2x, p2y = newSquare[1]

         cx = (p1x + p2x) / 2
         cy = (p1y + p2y) / 2
         center = (cx, cy)
         size = (p2x + 1) - p1x

         cNode = centersTree.setdefault(center, {'kids':[], 'size': None, 'square': None})
         cNode['size'] = size
         cNode['square'] = newSquare
         if parentPt is not None:
            pNode = centersTree.setdefault(parentPt, {'kids':[], 'size': None, 'square': None})
            pNode['kids'].append(center)
            cNode['kids'].append(parentPt)


         #Look at diagonal points later
         next_N = []
         next_S = []
         next_E = []
         next_W = []
         next_N.append(((p1x-1, p1y-1), center, 'NW')) #NW
         next_S.append(((p1x-1, p2y+1), center, 'SW')) #SW
         for x in range(p1x, p2x+1):
            ew = ''
            if x < (p1x + p2x +1) / 3:
               ew = 'W'
            elif x > (2 * (p1x + p2x) +1) / 3:
               ew = 'E'

            next_N.append(((x, p1y-1), center, 'N'+ew)) #Add the top/bottom perimeter points
            next_S.append(((x, p2y+1), center, 'S'+ew))
            for y in range(p1y, p2y+1):
               if isValidPoint((x,y), img, filledVal = CENTERVAL):
                  setImgVal(x,y,squareFill,img)  #Don't match any of these points next time
         next_N.append(((p2x+1, p1y-1), center, 'NE')) #NE
         next_S.append(((p2x+1, p2y+1), center, 'SE')) #SE

         for y in range(p1y, p2y+1): #Add the right/left perimeter points
            ns = ''
            if y < (p1y + p2y +1) / 3:
               ns = 'N'
            elif y > (2 * (p1y + p2y) +1) / 3:
               ns = 'S'
            next_W.append(((p1x-1, y), center, ns+'W'))
            next_E.append(((p2x+1, y), center, ns+'E'))
         #endfor y 

         pushList = []
         if direction == 'NW':
            pushList.extend(next_N + next_W)
         elif direction == 'N':
            random.shuffle(next_N)
            pushList.extend(next_N + next_W + next_E)
         elif direction == 'NE':
            next_N.reverse()
            pushList.extend(next_N + next_E)
         elif direction == 'SE':
            next_S.reverse()
            next_E.reverse()
            pushList.extend(next_S + next_E)
         elif direction == 'S':
            random.shuffle(next_S)
            next_E.reverse()
            next_W.reverse()
            pushList.extend(next_S + next_E + next_W)
         elif direction == 'SW':
            next_W.reverse()
            pushList.extend(next_S + next_W)
         elif direction == 'W':
            random.shuffle(next_W)
            pushList.extend(next_W + next_N + next_S)
         elif direction == 'E':
            next_S.reverse()
            next_N.reverse()
            random.shuffle(next_E)
            pushList.extend(next_E + next_N + next_S)
         pushList.reverse()

         squareSeeds.extend(pushList)

         #saveimg(img)
      #endif
   #endwhile
   return centersTree

def getImgVal(x,y,img):
   h = img.rows
   w = img.cols
   if y < 0 or y >= h or x < 0 or x >= w:
      #print "Returning -1 for %s, %s" % (x,y)
      return -1
   try:
      return img[y,x]
   except:
      print "Trying to get invalid pixel %s" % (str(x,y))
     
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

def isValidPoint(point, img, filledVal = FILLEDVAL):
   """Checks with an img to see if the point is filled or not"""
   height = getHeight(img)
   width = getWidth(img[0])
   x,y = point
   if y < 0 or y >= height or x < 0 or x >= width:
      #Bounds check
      retval  = False
   else:
      retval = ( getImgVal(x,y,img) == filledVal )
   return retval

def isValidSquare(square, img):
   """Check to see if square is error free enough"""
   global SQUARE_ERROR, CENTERVAL
   errorThresh  = SQUARE_ERROR
   p1, p2 = square
   p1x, p1y = square[0] 
   p2x, p2y = square[1] 
   size = 1 + (p2x - p1x)

   maxInvalidPixels = int( errorThresh * (4 * size - 2)) 
   badPixels = 0
   #Assume that the inner square is valid and only check the perimeter
   for x in range(p1x, p2x+1):
      pTopVal = getImgVal(x, p1y, img)
      if not pTopVal == FILLEDVAL and not pTopVal == CENTERVAL:
         badPixels += 1
      pBotVal = getImgVal(x, p2y, img)
      if not pBotVal == FILLEDVAL and not pBotVal == CENTERVAL:
         badPixels += 1
   if badPixels > maxInvalidPixels:
      #INVALID square
      return False
   for y in range(p1y+1, p2y): #Don't overlap with top/bottom
      pLeftVal = getImgVal(p1x,y,img)
      if not pLeftVal == FILLEDVAL and not pLeftVal == CENTERVAL:
         badPixels += 1
      pRightVal = getImgVal(p2x,y,img)
      if not pRightVal == FILLEDVAL and not pRightVal == CENTERVAL:
         badPixels += 1
   if badPixels > maxInvalidPixels:
      #INVALID square
      return False
   #VALID
   return True

def growSquare(point, img, directions = ['NW','NE','SW','SE']):
   """Given an input point, find the biggest square that can fit around it.
   Returns a square tuple ( (tlx, tly), (brx, bry) )"""
   #Sanity check
   global CENTERVAL

   pointVal = getImgVal( point[0], point[1], img)
   if pointVal != CENTERVAL: #Center must be this value
      return None


   #Initialize to simplest case
   curSquare = maxSquare = (point, point)
   maxSize = 0

   squareStack = [curSquare]
   while len(squareStack) > 0:
      curSquare = squareStack.pop()

      curSize = curSquare[1][1] + 1 - curSquare[0][1] #Y difference = size
      if curSize > maxSize:
         maxSquare = tuple(curSquare)
         maxSize = curSize

      p1x, p1y = list(curSquare[0])
      p2x, p2y = list(curSquare[1])

      testSquares = {}
      growth = 1 #(curSize + 1) / 2
      testSquares['NW'] = ( (p1x-growth, p1y-growth), (p2x, p2y) ) #NorthWest
      testSquares['NE'] = ( (p1x, p1y-growth), (p2x+growth, p2y) ) #NorthEast
      testSquares['SW'] = ( (p1x-growth, p1y), (p2x, p2y+growth) ) #SouthWest
      testSquares['SE'] = ( (p1x, p1y), (p2x+growth, p2y+growth) ) #SouthEast

      for dir, newSquare in testSquares.items():
         if dir in directions and isValidSquare(newSquare, img):
            squareStack.append(newSquare)
     
   return maxSquare

#***************************************************
#  Stroke Class
#***************************************************



class Stroke(object):
   """A stroke consisting of a list of points"""
   def __init__(self):
      self.points = []
      self.center = (-1, -1)
      self.topleft = (-1, -1)
      self.bottomright = (-1, -1)
   def addPoint(self,point):
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

      self.points.append(point)
      
   def getPoints(self):
      """Return a list of points"""
      return self.points
   def merge(self, rhsStroke):
      """Merge two strokes together"""
      self.points.extend(rhsStroke.points)

#***************************************************
#  Image Processing
#***************************************************


def resizeImage(img):
   targetWidth = 1280
   realWidth = img.cols

   scale = targetWidth / float(realWidth) #rough scaling
   print "Scaling %s" % (scale)
   retImg = cv.CreateMat(int(img.rows * scale), int(img.cols * scale), img.type)
   cv.Resize(img, retImg)
   return retImg

def smooth(img, ksize = 9, type='median'):
   """Do a median smoothing with kernel size ksize"""
   retimg = cv.CloneMat(img)
   if type == 'gauss':
      smoothtype = cv.CV_GAUSSIAN
   else:
      smoothtype = cv.CV_MEDIAN
   #retimg = cv.CreateMat(img.cols, img.rows, cv.CV_8UC3)
   #                            cols, rows, anchorx,y, shape
   #kernel = cv.CreateStructuringElementEx(3,3, 1,1, cv.CV_SHAPE_RECT,
                                          #(0,1,0,1,0,1,0,1,0))
   cv.Smooth(img, retimg, smoothtype= smoothtype, param1=ksize, param2=ksize)
   return retimg

def invert (cv_img):
   """Return a negative copy of the grayscale image"""
   global BGVAL
   retimg = cv.CloneMat(cv_img)
   cv.Set(retimg, BGVAL)
   cv.AddWeighted(cv_img, -1.0, retimg, 1.0, 0.0,retimg )
   return retimg

def removeBackground(cv_img):
   """Take in a color image and convert it to a binary image of just ink"""
   global BGVAL
   #Hardcoded for resolution/phone/distance
   denoise_k = 3
   smooth_k = 13
   inv_factor = 0.5
   ink_thresh = 122
   gray_img = cv.CreateMat(cv_img.rows, cv_img.cols, cv.CV_8UC1)
   cv.CvtColor(cv_img, gray_img, cv.CV_RGB2GRAY)
   bg_img = smooth(gray_img, ksize=smooth_k)
   bg_img = invert(bg_img)
   gray_img = smooth(gray_img, ksize=denoise_k)
  
   cv.AddWeighted(gray_img, 1, bg_img, 1, 0.0, gray_img )
   cv.Threshold(gray_img, gray_img, 250, BGVAL, cv.CV_THRESH_BINARY)

   show(gray_img)


   return gray_img



def squareCenter(square):
   """Get the integer center point of this square"""
   ((p1x, p1y), (p2x, p2y)) = square

   #             CentX          CentY
   return ( (p1x + p2x)/2, (p1y+p2y)/2 )
   
def squareSize(square):
   """Return the length of a side of this square"""
   ((p1x, p1y), (p2x, p2y)) = square
   return (p2x - p1x)

def processStrokes(cv_img):
   """Take in a raw, color image and return a list of strokes extracted from it."""
   global DEBUGIMG, BGVAL

   #show(cv_img)
   small_img = resizeImage(cv_img)
   temp_img = removeBackground(small_img)

   DEBUGIMG = cv.CloneMat(temp_img)
   cv.Set(DEBUGIMG, BGVAL)
   #cv.AddWeighted(temp_img, 0.0, temp_img, 1.0, 220 ,DEBUGIMG )


   points = []
   for i in range (0, temp_img.cols):
      points.extend([ (i,j) for j in range(0, temp_img.rows)] )

   changed1 = True
   changed2 = True
   evenIter = True 
   while changed1 or changed2:
      #saveimg(temp_img)
      changed, points, temp_img = thinBlobsPoints(points, temp_img, evenIter = evenIter)
      if evenIter:
         changed1 = changed
      else:
         changed2 = changed

      evenIter = not evenIter 

   
   strokelist = pointsToStrokes(points)
   #strokelist = bitmapToStrokes(temp_img,step = 1)
   
   cv.Set(temp_img, BGVAL)
   numPts = 0
   strokelist.sort(key = (lambda s: s.center[1] * 10 + s.center[0]) ) 
   for s in strokelist:
      prev = None
      for p in s.getPoints():
         if prev is not None:
            cv.Line(temp_img, prev, p, 0x0, thickness=1)
            #saveimg (temp_img)
         else:
            cv.Circle(temp_img, p, 2, 0x0, thickness=1)
         prev = p
         numPts += 1
         if numPts %100 == 0:
            saveimg(temp_img)
   return temp_img

def pruneSquareTree(squareTree):
   global PRUNING_ERROR
   threshold = (1 - PRUNING_ERROR) #how close a fit to all of the blobs
   availSizes = {}
   totalSize = 0
   for node in squareTree.values():
      size = node['size']
      totalSize += size * size
      sizeCount = availSizes.get(size, 0)
      availSizes[size] = sizeCount + 1



   target = threshold * totalSize
   sizes = availSizes.keys()
   sizes.sort(key=(lambda x: -x))
   for s in sizes:
      num = ( availSizes[s] + 10 )/ 10
      print "%s\t%s" % (s, 'X'*num)
      
   useSizes = {}
   while target > 0:
      s = sizes.pop(0)
      needed = (target + 1) / (s*s) #Ceiling
      if needed > availSizes[s]:
         useSizes[s] = availSizes[s]
         target -= useSizes[s] * (s * s)
      elif needed > 0:
         useSizes[s] = int(needed)
         target -= needed * (s*s) #should be zero!
   print "Using:"
   
   sizes = useSizes.keys()
   sizes.sort(key=(lambda x: -x))
   for s in sizes:
      num = ( useSizes[s] + 10 )/ 10
      print "%s\t%s" % (s, 'X'*num)

   #Now we know how many of each size we need
   retTree = {}
   root = None
   for pt, node in squareTree.items():
      if node['size'] in useSizes:
         root = pt
         break

   procStack = [(root, None)]
   seen = {}
   while len(procStack) > 0:
      curPt, parent = procStack.pop()
      seen[curPt] = True
      curNode = dict(squareTree[curPt])
      size = curNode['size'] 
      linkParent = parent #link kids to parent
      if size in useSizes and useSizes[size] > 0:
         #Add to tree
         retTree[curPt] = curNode
         curNode['kids'] = [] #Clear its children

         #link to parent
         if parent is not None:
            retTree[parent]['kids'].append(curPt)
            retTree[curPt]['kids'].append(parent)

         useSizes[size] -= 1 #Covered

         linkParent = curPt #Link kids to curPt

      #Keep traversing the original tree
      for k in squareTree[curPt]['kids']:
         if k not in seen:
            procStack.append((k, linkParent))

   print "Pruned square tree from %s to %s points at %s%% accuracy" % (len(squareTree), len(retTree), 100 * threshold)
   return retTree

def squareTreeToStrokes(squareTree):
   global DEBUGIMG

   retStrokes = []
   tempTree = pruneSquareTree(squareTree)
   preTree = dict(tempTree)
   #tempTree = dict(squareTree) #Copy the orig tree
   totPoints = 0
   while len(tempTree) > 0:
      #Find a good leaf
      maxLeaf = tempTree.keys()[0]
      maxDist = 0
      pointStack = [(maxLeaf, 0)]
      seen = {}
      while len(pointStack) > 0:
         top, curlevel = pointStack.pop()
         if curlevel > maxDist:
            maxDist = curlevel
            maxLeaf = top
         seen[top] = True
         for kid in tempTree[top]['kids']:
            if kid not in seen and kid in tempTree:
               pointStack.append( (kid, curlevel+1) )

      #Find the longest path from the leaf
      root = maxLeaf
      maxPath = []
      pathStack = [[root]]
      seen = {}
      while len(pathStack) > 0:
         curPath = pathStack.pop()
         thisNode = curPath[-1]
         seen[thisNode] = True

         if len(curPath) > len(maxPath):
            maxPath = curPath

         for kid in tempTree[thisNode]['kids']:
            if kid not in seen and kid in tempTree:
               pathStack.append( curPath + [kid] )


      #Make it a stroke
      newStroke = Stroke()
      #nextTree = {}
      keyDict = tempTree.keys()
      for point in keyDict:
         node = tempTree[point]
         newkids = []
         for kid in node['kids']:
            if point not in maxPath or kid not in maxPath and kid in tempTree:
               #Keep all of the connections not part of the current stroke
               newkids.append(kid)

         node['kids'] = newkids

         if len(newkids) == 0 :
            del(tempTree[point])
      #tempTree = nextTree

      for point in maxPath:
         newStroke.addPoint(point)
      totPoints += len(newStroke.points)
      retStrokes.append(newStroke)

   """
   allPoints = []
   for s in retStrokes:
      allPoints.extend(s.points)

   for p in preTree.keys():
      if p not in allPoints:
         print "%s in tree but not covered by strokes" % (str(p))
         #cv.Circle(DEBUGIMG, p, 1, 0x0, thickness=3)

   """
   print "Blob completed in %s strokes" % (len (retStrokes))
   return retStrokes

def debugSquareTreeToStrokes(squareTree):
   print "*** USING DEBUG TREE TO STROKES ***"
   
   squareTree = pruneSquareTree(squareTree)
   retStrokes = []
   for p, node in squareTree.items():
      for kid in node['kids']:
         newStroke = Stroke()
         newStroke.addPoint( p )
         newStroke.addPoint( kid )
         retStrokes.append(newStroke)

   print "*** USING DEBUG TREE TO STROKES ***"

   return retStrokes


def bitmapToPoints(img, step = 1):
   global DEBUGIMG
   allSquares = set([])
   print img.cols
   for i in range (0, img.cols, step):
      for j in range(0, img.rows, step):
         print "Processing point  %s" % (str((i,j)))
         p = (i,j)
         maxSquare = growSquare(p, img)
         allSquares.add(maxSquare)

   for sqr in allSquares:
      (p1x, p1y) , (p2x, p2y) = sqr
      center = ( (p1x + p2x) / 2, (p1y + p2y) /2 )
      setImgVal(center[0], center[1], 0, DEBUGIMG)




def bitmapToStrokes(img,step = 1):
   """Take in a binary image and group blobs of black into strokes.
   Point ordering of these strokes is undefined"""
   global DEBUGIMG
   retStrokes = []
   print img.cols
   for i in range (0, img.cols, step):
      #print "Processing column %s" % (i)
      for j in range(0, img.rows, step):
         p = (i,j)
         pixval = getImgVal(i, j, img) 
         if pixval == CENTERVAL:
            blobSquareTree = fillSquares(p, img)
            blobSquares = []
            for center, squareNode in blobSquareTree.items():
               size = squareNode['size']
               cv.Circle(DEBUGIMG, center, (size / 2), 0x0, thickness=1)
            retStrokes.extend(squareTreeToStrokes(blobSquareTree))

   print "\rFound %s strokes                 " % (len(retStrokes))
   return retStrokes

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

def saveimg(cv_img, outdir = "./temp/"):
   global FNAMEITER
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
   
   if outfname is not None:
      cv.SaveImage(outfname, out_img)

   #show(out_img)



if __name__ == "__main__":
   import sys
   main(sys.argv)
