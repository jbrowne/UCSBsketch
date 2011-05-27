#!/usr/bin/env python2.6
import cv
import Image
import pickle
import random
import pdb

FILLEDVAL = 0.0 
COLORFACTOR = 10
class TStroke(object):
   def __init__(self):
      self.rootPt = None
      self.treemap = None #Hash each point to its tree node
   def addPoint(self, pt, parent):
      if self.rootPt is None:
         self.rootPt = pt
      node = {'parent' : parent, 'kids': []} 
      self.treemap[pt] = node
      self.treemap[parent]['kids'].append(pt)
   def getPoints(self):
      retPoints = []
      proc = [self.rootPt]
      while len(proc) > 0:
         pt = proc.pop()
         retPoints.append(pt)
         proc.extend(self.treemap[pt]['kids'])
   
   def containsPoint(self, point):
      return point in self.treemap

   def merge(self, rhsStroke, linkPt):
      """merge another stroke into this stroke"""
      node = self.treemap[linkPt]
      node['kids'].append(rhsStroke.rootPt)
      for pt, node in rhsStroke.treemap.items():
         if pt in self.treemap:
            raise (Exception("Oh noes"))
         else:
            self.treemap[pt] = node

def getFillVal(number):
   global COLORFACTOR
   return (number * COLORFACTOR) % 256

def fillSquares(startPoint, img):
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
         squareFill = getFillVal(squareNum)

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
   #return img[y][x]
def setImgVal(x,y,val,img):
   img[y,x] = val
   #img[y][x] = val

def getHeight(img):
   return img.rows
def getWidth(img):
   return img.cols

def isValidPoint(point, img):
   global FILLEDVAL
   """Checks with an img to see if the point should be filled or not"""
   height = getHeight(img)
   width = getWidth(img[0])
   x,y = point
   if y < 0 or y >= height or x < 0 or x >= width:
      #Bounds check
      retval  = False
   else:
      retval = getImgVal(x,y,img) == FILLEDVAL
   """

   if retval:
      print "   Point %s is valid" % (str(point))
   else:
      print "   Point %s is NOT valid" % (str(point))
   """

   return retval

def isValidSquare(square, img):
   #print "**Testing square %s" % (str(square))
   p1, p2 = square
   p1x, p1y = square[0] 
   p2x, p2y = square[1] 

   #assert p2x - p1x == p2y - p1y, "ERROR: NOT A SQUARE %s" % (str(square))
   if not isValidPoint(p1, img) or not isValidPoint(p2, img):
      #print "***INVALID square %s" % (str(square))
      return False


   for x in range(p1x, p2x+1):
      for y in range(p1y, p2y+1):
         if not isValidPoint((x,y), img):
            #print "***INVALID square %s" % (str(square))
            return False

   #print "***Square %s is VALID" % (str(square))
   return True

def growSquare(point, img, directions = ['nw','ne','sw','se']):
   """Given an input point, find the biggest square that can fit around it"""

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






class Stroke(object):
   def __init__(self):
      self.points = {}
      self.segments = []
   def addPoint(self,point):
      #print "Adding point. Are you sure you don't want addline?"
      self.points[point] = True
   def getPoints(self):
      return self.points.keys()
   def merge(self, rhsStroke):
      self.points.update(rhsStroke.points)
      self.segments = set(self.segments).union(set(rhsStroke.segments))

   def addLine(self, seg):
      p,q = seg
      self.points[q] = True
      self.segments.append(seg)



def show(cv_img):
   print cv_img.type
   Image.fromstring("L", cv.GetSize(cv_img), cv_img.tostring()).show()


def smooth(img, ksize = 9):
   print type(img)
   retimg = cv.CloneMat(img)
   #retimg = cv.CreateMat(img.cols, img.rows, cv.CV_8UC3)
   #                            cols, rows, anchorx,y, shape
   #kernel = cv.CreateStructuringElementEx(3,3, 1,1, cv.CV_SHAPE_RECT,
                                          #(0,1,0,1,0,1,0,1,0))
   cv.Smooth(img, retimg, smoothtype= cv.CV_MEDIAN, param1=ksize, param2=ksize)
   return retimg

def invert (cv_img):
   retimg = cv.CloneMat(cv_img)
   cv.Set(retimg, 255)
   cv.AddWeighted(cv_img, -1.0, retimg, 1.0, 0.0,retimg )
   return retimg

def removeBackground(cv_img):
   
   bg_img = cv.CreateMat(cv_img.rows, cv_img.cols, cv.CV_8UC1)
   cv.CvtColor(cv_img, bg_img, cv.CV_RGB2GRAY)
   inv_img = smooth(bg_img, ksize=13)
   #bg_img = cv.CloneImage(cv_img)
  
   inv_img = invert(inv_img)
   cv.AddWeighted(bg_img, 0.5, inv_img, 0.5, 0.0,bg_img )
   cv.Threshold(bg_img, bg_img, 123, 255, cv.CV_THRESH_BINARY)

   return bg_img


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

def squareCenter(square):
   ((p1x, p1y), (p2x, p2y)) = square

   #             CentX          CentY
   return ( (p1x + p2x)/2, (p1y+p2y)/2 )
   
def squareSize(square):
   ((p1x, p1y), (p2x, p2y)) = square
   return (p2x - p1x)

def processStrokes(cv_img):
   temp_img = removeBackground(cv_img)

   strokelist = bitmapToUnorderedStrokes(temp_img,step = 1)
   strokeSquares = []
   for s in strokelist:
      seedPt = s.getPoints()[0]
      #pdb.set_trace()
      squares = fillSquares(seedPt, temp_img)
      strokeSquares.append(squares)

   retimg = cv.CloneMat(temp_img)
   cv.Set(retimg, 255)
   for stk in strokeSquares:
      prev = None
      for square in stk:
         size = squareSize(square)
         if size > 1:
            x,y = squareCenter(square)
            #retimg[y,x] = 0
            cv.Circle(retimg, (x,y), size/2, 0x0)
            if prev is not None:
               cv.Line(retimg, prev, (x,y), 0x0, thickness=1)
            #prev = (x,y)
   
   """
   cv.Set(temp_img, 255)
   for idx,s in enumerate(strokelist):
      for pt in s.points:
         print pt
         cv.Circle(temp_img, pt, 2, 0x0)
      for seg in s.segments:
         p,q = seg
         cv.Line(temp_img, p,q, 0x0, thickness=1)
   """
   return retimg

def bitmapToUnorderedStrokes(img,step = 1):
   strokes = {} 
   s = TStroke()
   for i in range(0,img.cols, step):
      print "Col: %s / %s\tTracking %s strokes" % (i, img.cols, len(strokes.keys()))
      for j in range(0,img.rows, step):

         p = (i,j)
         if (img[j,i] == 0):
            #Neighbor indices
            nw = (i-step,j-step)
            n =  (i, j-step)
            ne = (i+step,j-step)
            e = (i+step, j)
            sw = (i-step,j+step)
            s =  (i, j+step)
            se = (i+step,j+step)
            w = (i-step, j)
            neighbors = [nw, n, ne, e, se, s, sw, w]

            isMerged = False
            n_points = []
            #Find connected strokes
            connectedStrokes = {} 
            for s in strokes.keys():
               for n_p in neighbors:
                  if n_p in s.points:
                     #print "Found neighbor, merging with %s" % (str(s_i))
                     n_points.append(n_p)
                     isMerged = True
                     connectedStrokes[s] = True 

            if isMerged:
               #Merge the connected strokes
               mergedStroke = Stroke()
               for n_p in n_points:
                  mergedStroke.addLine((n_p,p))
               for s in connectedStrokes.keys():
                  mergedStroke.merge(s)
                  del(strokes[s])
               strokes[mergedStroke] = True
            #Otherwise, just add me as a stroke
            else:
               """
               #Prune single points
               shouldAdd = False
               for ni,nj in neighbors:
                  try:
                     if img[nj,ni] == 0:
                        shouldAdd = True
                  except:
                     continue
               if shouldAdd:
               """
               newS = Stroke()
               newS.addPoint(p)
               strokes[newS] = True

         #endif point is black
      #endfor j
   #endfor i

   return strokes





   
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
