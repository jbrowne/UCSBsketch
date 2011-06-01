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
   returnSquares = []
   squareSeeds = [startPoint]

   while len(squareSeeds) > 0:
      seedPt = squareSeeds.pop()
      #print "Checking %s for square" % (str(seedPt))
      newSquare = growSquare(seedPt, img)
      if newSquare is not None:
         #print "  Found"
         returnSquares.append(newSquare)
         squareNum = len(returnSquares)

         p1x, p1y = newSquare[0]
         p2x, p2y = newSquare[1]

         #Look at diagonal points later
         squareSeeds.append((p1x-1, p1y-1)) #NW
         squareSeeds.append((p2x+1, p2y+1)) #SE
         squareSeeds.append((p1x-1, p2y+1)) #SW
         squareSeeds.append((p2x+1, p1y-1)) #NE
         for x in range(p1x, p2x+1):
            squareSeeds.append((x, p1y-1)) #Add the top/bottom perimeter points
            squareSeeds.append((x, p2y+1))
            for y in range(p1y, p2y+1):
               setImgVal(x,y,squareFill,img)  #Don't match any of these points next time

         for y in range(p1y, p2y+1): #Add the right/left perimeter points
            squareSeeds.append((p1x-1, y))
            squareSeeds.append((p2x+1, y))
         #endfor y
      #endif
   #endwhile
   return returnSquares

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
      self.points = {}
   def addPoint(self,point):
      """Add a point to the end of the stroke"""
      #print "Adding point. Are you sure you don't want addline?"
      self.points[point] = True
   def getPoints(self):
      """Return a list of points"""
      return self.points.keys()
   def merge(self, rhsStroke):
      """Merge two strokes together"""
      self.points.update(rhsStroke.points)

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


"""
Deprecated
def trimStrokes(strokelist):
   retlist = []
   for stk in strokelist:
      srcDict = {}
      for pt in stk.points:
         i,j = pt

         setSrc = True #Should we make this a root node
         for updown in [-1, 0, 1]:
            for leftright in [-1, 0, 1]:
               if (updown, leftright) is not (0,0):
                  n_p = (i + leftright, j + updown)
                  if n_p in srcDict and srcDict[n_p] is None: #A neighbor is a root candidate
                     #srcDict[pt] = n_p
                     setSrc = False
         if setSrc:
            srcDict[pt] = None
      #endfor stk.points
      stkCopy = Stroke()
      for pt in srcDict.keys():
         stkCopy.addPoint(pt)
      retlist.append(stkCopy)
   #endfor strokelist
   return retlist
"""

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
   temp_img = removeBackground(cv_img)

   strokelist = bitmapToUnorderedStrokes(temp_img,step = 1)
   for s in strokelist:
      for p in s.getPoints():
         cv.Circle(temp_img, p, 2, 0x0, thickness=-1)
   return temp_img


def squaresToStroke(squares):
   """Take in a list of squares and convert it to a stroke with an undefined 
   ordering of points. 
   Each square is a tuple of topleft, bottom right (x,y) point tuples: ( (tlx, tly), (brx, bry) )
   """
   errorThreshold = 0.1
   retStroke = Stroke()
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
   for size in sizes:
      if size == 1:
         print "Stroke using single-pixel points!"
      for sqr in sizeSqrs[size]:
         (p1x, p1y), (p2x, p2y) = sqr 
         center = ( (p1x + p2x)/2, (p1y + p2y) /2)
         retStroke.addPoint(center)

         currentPixels += size * size
         if currentPixels > absTarget:
            return retStroke

   return retStroke


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
   for i in range (0, img.cols, step):
      print "\rProcessing column %s" % (i),
      for j in range(0, img.rows, step):
         p = (i,j)
         pixval = img[j,i]
         if isFilledVal(pixval):
            blobSquares = fillSquares(p, img, 255)
            retStrokes.append(squaresToStroke(blobSquares))

   print "Found %s strokes" % (len(retStrokes))
   return retStrokes

def pointDist(p1, p2):
   p1x, p1y = p1
   p2x, p2y = p2

   return (p2x-p1x) ** 2 + (p2y-p1y) ** 2

def show(cv_img):
   print cv_img.type
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
