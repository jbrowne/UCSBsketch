#!/usr/bin/env python2.6
import cv
import Image
import pickle
import random
import pdb

FILLEDVAL = 0.0 
COLORFACTOR = 10


#***************************************************
#Square filling + helper functions
#***************************************************

def fillSquares(startPoint, img, squareFill=255):
   """Get a list of squares filling a blob starting at startPoint.
   Overwrites the blob with squareFill value"""

   centersTree = {}

   returnSquares = []
   squareSeeds = [(startPoint, None)]

   while len(squareSeeds) > 0:
      seedPt, parentPt = squareSeeds.pop()
      #print "Checking %s for square" % (str(seedPt))
      newSquare = growSquare(seedPt, img)
      if newSquare is not None:
         #print "  Found"
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
         squareSeeds.append(((p1x-1, p1y-1), center)) #NW
         squareSeeds.append(((p2x+1, p2y+1), center)) #SE
         squareSeeds.append(((p1x-1, p2y+1), center)) #SW
         squareSeeds.append(((p2x+1, p1y-1), center)) #NE
         for x in range(p1x, p2x+1):
            squareSeeds.append(((x, p1y-1), center)) #Add the top/bottom perimeter points
            squareSeeds.append(((x, p2y+1), center))
            for y in range(p1y, p2y+1):
               setImgVal(x,y,squareFill,img)  #Don't match any of these points next time

         for y in range(p1y, p2y+1): #Add the right/left perimeter points
            squareSeeds.append(((p1x-1, y), center))
            squareSeeds.append(((p2x+1, y), center))
         #endfor y
      #endif
   #endwhile
   return centersTree

def getImgVal(x,y,img):
   return img[y,x]
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

def isValidPoint(point, img):
   """Checks with an img to see if the point should be filled or not"""
   height = getHeight(img)
   width = getWidth(img[0])
   x,y = point
   if y < 0 or y >= height or x < 0 or x >= width:
      #Bounds check
      retval  = False
   else:
      retval = isFilledVal(getImgVal(x,y,img))
   return retval

def isValidSquare(square, img):
   """Check to see if square is unbroken"""
   p1, p2 = square
   p1x, p1y = square[0] 
   p2x, p2y = square[1] 

   if not isValidPoint(p1, img) or not isValidPoint(p2, img):
      #***INVALID square
      return False


   for x in range(p1x, p2x+1):
      for y in range(p1y, p2y+1):
         if not isValidPoint((x,y), img):
            #INVALID square
            return False

   #VALID
   return True

def growSquare(point, img, directions = ['nw','ne','sw','se']):
   """Given an input point, find the biggest square that can fit around it.
   Returns a square tuple ( (tlx, tly), (brx, bry) )"""
   #Sanity check
   if not isValidPoint(point, img):
     return None

   #Initialize to simplest case
   curSquare = maxSquare = (point, point)
   maxSize = 0

   squareStack = [curSquare]
   while len(squareStack) > 0:
      curSquare = squareStack.pop()

      curSize = curSquare[1][1] - curSquare[0][1] #Y difference = size
      if curSize > maxSize:
         maxSquare = tuple(curSquare)
         maxSize = curSize

      p1x, p1y = list(curSquare[0])
      p2x, p2y = list(curSquare[1])

      testSquares = {}
      testSquares['nw'] = ( (p1x-1, p1y-1), (p2x, p2y) ) #NorthWest
      testSquares['ne'] = ( (p1x, p1y-1), (p2x+1, p2y) ) #NorthEast
      testSquares['sw'] = ( (p1x-1, p1y), (p2x, p2y+1) ) #SouthWest
      testSquares['se'] = ( (p1x, p1y), (p2x+1, p2y+1) ) #SouthEast

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
   def addPoint(self,point):
      """Add a point to the end of the stroke"""
      #print "Adding point. Are you sure you don't want addline?"
      self.points.append(point)
   def getPoints(self):
      """Return a list of points"""
      return self.points
   def merge(self, rhsStroke):
      """Merge two strokes together"""
      self.points.extend(rhsStroke.points)

def smooth(img, ksize = 9):
   """Do a median smoothing with kernel size ksize"""
   retimg = cv.CloneMat(img)
   #retimg = cv.CreateMat(img.cols, img.rows, cv.CV_8UC3)
   #                            cols, rows, anchorx,y, shape
   #kernel = cv.CreateStructuringElementEx(3,3, 1,1, cv.CV_SHAPE_RECT,
                                          #(0,1,0,1,0,1,0,1,0))
   cv.Smooth(img, retimg, smoothtype= cv.CV_MEDIAN, param1=ksize, param2=ksize)
   return retimg

def invert (cv_img):
   """Return a negative copy of the grayscale image"""
   retimg = cv.CloneMat(cv_img)
   cv.Set(retimg, 255)
   cv.AddWeighted(cv_img, -1.0, retimg, 1.0, 0.0,retimg )
   return retimg

def removeBackground(cv_img):
   """Take in a color image and convert it to a binary image of just ink"""
   bg_img = cv.CreateMat(cv_img.rows, cv_img.cols, cv.CV_8UC1)
   cv.CvtColor(cv_img, bg_img, cv.CV_RGB2GRAY)
   inv_img = smooth(bg_img, ksize=23)
   bg_img = smooth(bg_img, ksize=5)
   #bg_img = cv.CloneImage(cv_img)
  
   inv_img = invert(inv_img)
   cv.AddWeighted(bg_img, 0.5, inv_img, 0.5, 0.0,bg_img )
   cv.Threshold(bg_img, bg_img, 123, 255, cv.CV_THRESH_BINARY)


   return bg_img



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
   global DEBUGIMG
   temp_img = removeBackground(cv_img)


   DEBUGIMG = cv.CloneMat(temp_img)
   cv.Set(DEBUGIMG, 255)

   strokelist = bitmapToUnorderedStrokes(temp_img,step = 1)
   
   for s in strokelist:
      prev = None
      for p in s.getPoints():
         if prev is not None:
            #cv.Circle(temp_img, p, 2, 0x0, thickness=1)
            cv.Line(temp_img, prev, p, 0x0, thickness=1)
         prev = p
   return temp_img

def pruneSquareTree(squareTree):
   threshold = 0.8 #how close a fit to all of the blobs
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

   print "Available: %s" % (availSizes)
   useSizes = {}
   while target > 0:
      print "Target: %s" % (target)
      s = sizes.pop(0)
      needed = (target + 1) / (s*s) #Ceiling
      if needed > availSizes[s]:
         useSizes[s] = availSizes[s]
         target -= useSizes[s] * (s * s)
      elif needed > 0:
         useSizes[s] = int(needed)
         target -= needed * (s*s) #should be zero!
   print "Used: %s" % (useSizes)

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

   print "Pruned square tree to %s points at %s accuracy" % (len(retTree), 100 * threshold)
   return retTree

def squareTreeToStrokes(squareTree):

   retStrokes = []
   tempTree = dict(squareTree) #Copy the orig tree
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

      print "Longest path length: %s" % (len(maxPath))
      #Make it a stroke
      newStroke = Stroke()
      for point in maxPath:
         newStroke.addPoint(point)
         del(tempTree[point])

      retStrokes.append(newStroke)

   print "Blob completed in %s strokes" % (len (retStrokes))
   return retStrokes
def squaresToStrokes(squareTree):
   """Take in a bunch of squares and output one or more strokes approximating them"""
   prunedSquareTree = pruneSquareTree(squareTree)
   strokes = squareTreeToStrokes(prunedSquareTree)

   """
   squares = [node['square'] for node in squareTree.values()]
   pointlist = squaresToPoints(squares)
   strokes =  pointsToStrokes(pointlist)
   """
   return strokes

def pointsToStrokes(points):
   """Take in an unordered list of points and convert it into one or more strokes"""
   global DEBUGIMG 
   retStroke = Stroke()
   distances = {}

   edgecount = 0
   for i, p1 in enumerate(points):
      for j, p2 in enumerate(points):
         if i != j:
            pointdist = pointDist(p1, p2)
            pointsOfDist = distances.setdefault(pointdist, [])
            pointsOfDist.append((p1, p2))
            edgecount += 1
   #print "%s points, %s edges in matrix" % (len(points), edgecount)

   dists = distances.keys()
   dists.sort()

   
   curPoints = {}
   for d in dists:
      for edge in distances[d]:
         p1, p2 = edge
         if ( 
             (p1 in curPoints or p2 in curPoints) \
             and not (p1 in curPoints and p2 in curPoints) \
            ) \
            or len(curPoints) == 0 : #First add
            curPoints.setdefault(p1, []).append(p2) #Append p2 as a neighbor of p1
            curPoints.setdefault(p2, []).append(p1) #P1 as a neighbor of p2
      if len(curPoints) == len(points):
         print "Got all the points at distance %s" % (d)
         break

   """
   print "%s points in MST" % (len(curPoints.keys()))
   for p1 in curPoints.keys():
      for p2 in curPoints[p1]:
         cv.Line(DEBUGIMG, p1, p2, 0x0, thickness=1)

   show(DEBUGIMG)
   

### BREAAAAKK ###
   """

   #curPoints is now the MST


   #Find a good leaf
   maxLeaf = curPoints.keys()[0]
   maxDist = 0
   pointStack = [(maxLeaf, 0)]
   seen = []
   while len(pointStack) > 0:
      top, curlevel = pointStack.pop()
      if curlevel > maxDist:
         maxDist = curlevel
         maxLeaf = top
      seen.append(top)
      for kid in curPoints[top]:
         if kid not in seen:
            pointStack.append( (kid, curlevel+1) )



   pointlist = []
   if len(curPoints) > 0:
      pointStack = [ maxLeaf ]
      while len(pointStack)> 0:
         print pointStack
         top = pointStack.pop()
         #print "Adding point %s" % (str(top))
         #print "  Checking kids: %s" % (curPoints[top])
         pointlist.append(top) #Random root
         for kid in curPoints[top]:
            if kid not in pointlist:
               pointStack.append(kid) #Add the children

   for p in pointlist:
      retStroke.addPoint(p)

   return [retStroke]

def squaresToPoints(squares):
   """Take in a list of squares, find a set of the biggest squares that approximates
   the blob to a threshold accuracy, and convert the squares to a list of those squares'
   center points.
   Each square is a tuple of topleft, bottom right (x,y) point tuples: ( (tlx, tly), (brx, bry) )
   """
   errorThreshold = 0.1
   retStrokes = []
   pointList = []
   sizeSqrs = {}
   totalSize = 0
   #Sort squares into descending order of size
   for sqr in squares:
      (p1x, p1y), (p2x, p2y) = sqr
      size = (p2x - p1x)
      totalSize += size * size #Add all of this squares pixes to total size
      sizelist = sizeSqrs.setdefault(size, [])
      sizelist.append(sqr)
   sizes = sizeSqrs.keys()
   sizes.sort(key=(lambda x: -x)) #sort descending

   #Add progressively smaller squares until blob is approximately present
   absTarget = totalSize - errorThreshold * totalSize #how many pixels do we need to fill to be "good enough"
   currentPixels = 0
   isDone = False
   for size in sizes:
      for sqr in sizeSqrs[size]:
         (p1x, p1y), (p2x, p2y) = sqr 
         center = ( (p1x + p2x)/2, (p1y + p2y) /2)
         #retStroke.addPoint(center)
         pointList.append(center)

         currentPixels += size * size
         if currentPixels > absTarget:
            isDone = True
            break
            #return pointList 
      if isDone:
         break

   return pointList


def OrderStrokePoints(stroke):
   """Take an stroke with an arbitrary order on its points and 
   order them such that they could be drawn in a single gesture"""
   retStroke = Stroke()
   points = stroke.getPoints()

   if len(points) == 0:
      return retStroke

   pointTree = {}
   for i in range(0, len(points)):
      minDist = None
      minPoint = None
      for j in range(0, len(points)):
         if i == j: #Don't measure against myself
            continue
         curDist = pointDist(points[i], points[j])
         if minDist is None or minDist < curDist:
            minDist = curDist
            minPoint = points[j]
      iNode = pointTree.setdefault(points[i], {})
      jNode = pointTree.setdefault(points[j], {})
      iNode['next'] = points[j]

def bitmapToUnorderedStrokes(img,step = 1):
   """Take in a binary image and group blobs of black into strokes.
   Point ordering of these strokes is undefined"""
   retStrokes = []
   print img.cols
   for i in range (0, img.cols, step):
      #print "Processing column %s" % (i)
      for j in range(0, img.rows, step):
         p = (i,j)
         pixval = img[j,i]
         if isFilledVal(pixval):
            blobSquareTree = fillSquares(p, img, 255)
            blobSquares = []
            for center, squareNode in blobSquareTree.items():
               blobSquares.append(squareNode['square'])
            retStrokes.extend(squaresToStrokes(blobSquareTree))

   print "\rFound %s strokes                 " % (len(retStrokes))
   return retStrokes

def pointDist(p1, p2):
   p1x, p1y = p1
   p2x, p2y = p2

   return (p2x-p1x) ** 2 + (p2y-p1y) ** 2

def show(cv_img):
   Image.fromstring("L", cv.GetSize(cv_img), cv_img.tostring()).show()
   
def main(args):
   if len (args) < 2:
      print( "Usage: %s <image_file> [output_file]" % (args[0]))
      exit(1)

   fname = args[1]
   if len(args) > 2:
      outfname = args[2]
   else:
      outfname = None


   in_img = cv.LoadImageM(fname)
   out_img = processStrokes(in_img)
   
   if outfname is not None:
      cv.SaveImage(outfname, out_img)

   show(out_img)



def tester(args):
   import pdb

   print """
           #0  1  2  3  4
   IMG = [ [1, 1, 1, 1, 1], #0
           [0, 1, 1, 1, 1], #1
           [1, 1, 1, 0, 1], #2
           [1, 1, 1, 1, 1], #3
           [1, 1, 1, 1, 1], #4
          ]
   """
           #0  1  2  3  4
   IMG = [ [1, 1, 1, 1, 1], #0
           [0, 1, 1, 1, 1], #1
           [1, 1, 1, 0, 1], #2
           [1, 1, 1, 1, 1], #3
           [1, 1, 1, 1, 1], #4
          ]


   height = len(IMG)
   width = len(IMG[0])

   startpt = (random.randint(0,width-1), random.randint(0,height-1))
   while not isValidPoint(startpt, IMG):
      startpt = (random.randint(0,width-1), random.randint(0,height-1))


   print "FillSquares"
   squares = fillSquares(startpt, IMG)
   
   print "List of squares"
   for i, s in enumerate(squares):
      print "  Square %s: %s" % (i, s)

   print "Filled image"
   for row in IMG:
      print row
   
   """

   print "growSquare((1,1))"
   print growSquare((1,1))

   print "growSquare((1,0))"
   print growSquare((0,2))
   """

if __name__ == "__main__":
   import sys
   main(sys.argv)
   #tester(sys.argv)
