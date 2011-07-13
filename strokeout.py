#!/usr/bin/env python
import cv
import Image
import pickle
import random
import random
import math
import pdb

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

def pointsToTrees(pointSet, rawImg):
   global DEBUGIMG
   linkDict = {}
   repPoints = []
   seen = {}
   allKeyPoints = []
   print "Converting points to strokes"
   while len(pointSet) > 0:
      seed = pointSet.pop()
      pointSet.add(seed)
      #repPoints.append(seed)
      procStack = [ (seed, 0) ]
      keyPoints = set([])


      endPoint1 = seed
      maxDist = 0

      while len(procStack) > 0:
         ( pt, dist ) = procStack.pop(0)
         (x,y) = pt

         if pt in seen:
            continue
         else:
            seen[ (x,y) ] = True

         if dist > maxDist:
            endPoint1 = (x,y)
            maxDist = dist

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

         passTwoPoints = set([])
         ptDict = linkDict.setdefault( pt , {'kids' : set([]) } )
         for nPt in eightNbors:
            if nPt in pointSet:
               nptDict = linkDict.setdefault( nPt , {'kids' : set([]) } )

               nptDict['kids'].add( pt )
               ptDict['kids'].add(nPt)

               if nPt not in seen:
                  procStack.append( (nPt, dist + 1) )


         if len(ptDict['kids']) > 2:
            keyPoints.add(pt)

         pointSet.remove( (x,y) )

      #Collapse internal nodes. Also prunes single-point subtrees
      for kPt in list(keyPoints):
         if kPt in linkDict:
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
               del(linkDict[kid])
               if kid == endPoint1:
                  endPoint1 = kPt
               if kid in keyPoints:
                  keyPoints.remove(kid)
               keyPoints.add(kPt)
            #print kPt, linkDict[kPt], "After"
      allKeyPoints.extend(list(keyPoints))

      #Search for the farthest away point from here
      seen = {}
      maxPath = [endPoint1]
      procStack = [ (endPoint1, maxPath) ]
      while len(procStack) > 0:
         pt, path = procStack.pop()
         if pt not in seen:
            seen[pt] = True

            linkDict[pt]['thickness'] = pointThickness(pt, rawImg)
            if len(path) > len(maxPath):
               maxPath = path
            for k in linkDict[pt]['kids']:
               procStack.append( (k, path + [pt]) )

      #Annotate each point with the direction to the next endpoint
      endPoint2 = maxPath[-1]
      for i, pt in enumerate(maxPath):
         if pt != endPoint2:
            linkDict[pt]['kidToEndPoint'] = maxPath[i+1]
      linkDict[pt]['kidToEndPoint'] = None

      repPoints.append(endPoint1)
   return {'reps' : repPoints, 'trees' : linkDict, 'keypoints' : allKeyPoints}

def pointThickness(point, img):
   global BGVAL

   px, py = point

   pixval = getImgVal(px, py, img)
   t = 0
   if pixval == BGVAL:
      return t

   keepGrowing = True
   while keepGrowing:
      t += 1 #thickness

      nw = (px - t, py - t)
      n  = (px    , py - t)
      ne = (px + t, py - t)
      sw = (px - t, py + t)
      s  = (px    , py + t)
      se = (px + t, py + t)
      e  = (px + t, py - t)
      w  = (px - t, py + t)

      for (x,y) in (nw, n, ne, e, se, s, sw, w):
         pVal = getImgVal(x,y, img)
         if pVal == BGVAL:
            keepGrowing = False
            break

   return 2 * (t - 1) + 1 #Return last good thickness

   




def pointsToStrokes(pointSet, rawImg):
   global DEBUGIMG
   trees = pointsToTrees(pointSet, rawImg)
   #for pt in trees['keypoints']:
      #cv.Circle(DEBUGIMG, pt, 2, 128, thickness=2)
   retStrokes = pointtreesToStrokes(trees['reps'], trees['trees'])
   return retStrokes


def pointtreesToStrokes(repPoints, linkDict):
   global DEBUGIMG
   ptsInStrokes = {}
   retStrokes = []
   seen = {}


   for r in repPoints:
      #Get a good start point
      #Build up a stroke
      numLeaves = 0
      strk = Stroke()
      procStack = [ (r, []) ]
      while len(procStack) > 0:
        pt, traceStack = procStack.pop()
        if pt in seen:
           continue
        thickness = linkDict[pt]['thickness']

        

        seen[pt] = True

        par = None
        if len(traceStack) > 0:
           par = traceStack.pop()
           if pt not in linkDict[par]['kids']:
              numLeaves += 1

           numBackpoints = 0
           while len(traceStack) > 0 and pt not in linkDict[par]['kids']:
              numBackpoints += 1
              if numBackpoints % 4 == 0:
                 strk.addPoint(par, thickness = linkDict[par]['thickness'] )

              par = traceStack.pop()

           traceStack.append(par) #add back in the last parent
        traceStack.append(pt)

        strk.addPoint(pt, thickness = thickness)
        ptsInStrokes[pt] = True

        progressKid = linkDict.get('kidToEndPoint', None)

        if progressKid is not None:
           procStack.append( (progressKid, traceStack) )

        kids = list(linkDict[pt]['kids'])
        if par is not None:
           kids.sort (key = (lambda k: angularDistance(par, pt, k) ) )
        for k in kids:
            if k not in seen and k != progressKid:
               procStack.append( (k, traceStack ) )
      #endwhile

      retStrokes.append(strk)
      print "%s Leaves in stroke" % (numLeaves)
   #endfor

   return retStrokes

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


   
def filledAndCrossingVals(point, img, skipCorners = False):
   """
   http://fourier.eng.hmc.edu/e161/lectures/morphology/node2.html
   with some corner cutting capability from Louisa Lam 1992.
   """  
   global CENTERVAL, BGVAL
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
      for i, pt in enumerate(nborList):
         prevNbor = nborList[(i + 8 - 1) % 8]

         ptFilled = getImgVal(pt[0], pt[1], img) == CENTERVAL 
         prevFilled = getImgVal(prevNbor[0], prevNbor[1], img) == CENTERVAL

         if ptFilled:
            filled += 1
         if prevFilled and not ptFilled:
            if skipCorners and pt in [ne, nw, se, sw]: #don't count if the missing corner doesn't affect connectivity
               nextNbor = nborList[(i + 1) % 8]
               nextFilled = getImgVal(nextNbor[0], nextNbor[1], img) == CENTERVAL
               if not nextFilled:
                  crossing += 1
               else:
                  pass
            else:
               crossing += 1
         #print "%s, " % (ptVal),
         prev = pt

      #print "\n%s filled, %s crossing" % (filled, crossing)
      retDict['filled'] = filled
      retDict['crossing'] = crossing
      
      nw = getImgVal(px-1, py+1, img) == CENTERVAL
      n = getImgVal(px, py+1, img) == CENTERVAL
      ne = getImgVal(px+1, py+1, img) == CENTERVAL

      w = getImgVal(px-1, py, img) == CENTERVAL
      #pixval = getImgVal(px, py, img) == CENTERVAL
      e = getImgVal(px+1, py, img) == CENTERVAL

      sw = getImgVal(px-1, py-1, img) == CENTERVAL
      s = getImgVal(px, py-1, img) == CENTERVAL
      se = getImgVal(px+1, py-1, img) == CENTERVAL

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
   minFill = 3
   maxFill = 6
   retPoints = set([])
   numChanged = 0
   if finalPass:
      print "Final pass"
      outImg = img #Edit inline
   else:
      outImg = cv.CloneMat(img)
   outImg = img #Edit inline

   if cleanNoise:
      noise = 2
      #minFill = 1
   else:
      noise = -1
      #minFill = 3
   for p in pointSet:
      (i,j) = p
      valDict = filledAndCrossingVals(p, img, skipCorners = finalPass)
      filled = valDict['filled']
      cnum_p = valDict['crossing']
      if evenIter:
         badEdge = valDict['esnwne']
      else:
         badEdge = valDict['wnsesw']

      if (filled >= minFill and filled <= 6 and cnum_p == 1 and (not badEdge or finalPass) ) or \
         (filled == noise): 
         numChanged += 1
         #if filled == 3:
            #printPoint(p, img)
         setImgVal(i, j, FILLEDVAL, outImg)
      elif filled > 2:
         retPoints.add(p)
   saveimg(outImg)

   return ( numChanged, retPoints, outImg )


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
   def merge(self, rhsStroke):
      """Merge two strokes together"""
      self.points.extend(rhsStroke.points)

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




def resizeImage(img):
   global NORMWIDTH
   targetWidth = NORMWIDTH
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
   global BGVAL, NORMWIDTH
   #Hardcoded for resolution/phone/distance
   tranScale = min (cv_img.cols / float(NORMWIDTH), NORMWIDTH)
   denoise_k =3
   smooth_k = 13

   denoise_k = max (1, int(denoise_k * tranScale))
   if denoise_k % 2 == 0:
      denoise_k += 1
   smooth_k = max (1, int(smooth_k * tranScale))
   if smooth_k % 2 == 0:
      smooth_k += 1

   inv_factor = 0.5
   ink_thresh = 122
   gray_img = cv.CreateMat(cv_img.rows, cv_img.cols, cv.CV_8UC1)
   cv.CvtColor(cv_img, gray_img, cv.CV_RGB2GRAY)
   bg_img = smooth(gray_img, ksize=smooth_k)
   bg_img = invert(bg_img)
   gray_img = smooth(gray_img, ksize=denoise_k)

   saveimg(gray_img)
  
   cv.AddWeighted(gray_img, 1, bg_img, 1, 0.0, gray_img )
   cv.Threshold(gray_img, gray_img, 250, BGVAL, cv.CV_THRESH_BINARY)

   saveimg(gray_img)


   return gray_img




def blobsToStrokes(img):
   global DEBUGIMG
   print "Thinning blobs:"
   rawImg = cv.CloneMat(img)

   def AllPtsIter(w,h):
      for i in xrange(w):
         for j in xrange(h):
            yield (i, j)

   pointSet = AllPtsIter(img.cols, img.rows)

   passnum = 1
   changed1 = True
   changed2 = True
   evenIter = True 
   while changed1 or changed2:
      print "Pass %s" % (passnum)
      #saveimg(img)
      evenIter = (passnum %2 == 0)
      numChanged, pointSet, img = thinBlobsPoints(pointSet, img, cleanNoise = False and (passnum <= 2), evenIter = evenIter)
      print "Num changes = %s" % (numChanged)
      if passnum % 2 == 0:
         changed1 = numChanged > 0
      else:
         changed2 = numChanged > 0
      passnum += 1
   print ""
   numChanged, pointSet, img = thinBlobsPoints(pointSet, img, finalPass = True)

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

   pointsPerFrame = 10
   #show(cv_img)
   small_img = resizeImage(cv_img)

   #getHoughLines(small_img)

   temp_img = removeBackground(small_img)
   #DEBUGIMG = cv.CloneMat(temp_img)
   DEBUGIMG = cv.CreateMat(DEBUGSCALE * temp_img.rows, DEBUGSCALE * temp_img.cols, cv.CV_8UC1)
   cv.Set(DEBUGIMG, 255)
   #DEBUGIMG = cv.CloneMat(temp_img)
   strokelist = blobsToStrokes(temp_img)
   
   cv.Set(temp_img, BGVAL)
   numPts = 0
   strokelist.sort(key = (lambda s: s.center[1] * 10 + s.center[0]) ) 
   lineColor = 200
   startColor = 0
   stopColor = 128
   for s in strokelist:
      prev = None
      t = s.getThickness()
      print "Stroke thickness = %s" % (t)
      for p in s.getPoints():
         debugPt = ( DEBUGSCALE * p[0], DEBUGSCALE * p[1])
         #setImgVal(DEBUGSCALE * p[0], DEBUGSCALE * p[1], 0, DEBUGIMG)
         if prev is not None:
            cv.Line(DEBUGIMG, prev, debugPt, lineColor, thickness=t)
            #saveimg (temp_img)
         else:
            pass
            cv.Circle(DEBUGIMG, debugPt, 2, startColor, thickness=2)
         numPts += 1
         prev = debugPt
         if numPts % pointsPerFrame == 0:
            pass
            saveimg(DEBUGIMG)
      cv.Circle(DEBUGIMG, debugPt, 2, stopColor, thickness=2)
   saveimg(DEBUGIMG)

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
   #show(out_img)
   
   if outfname is not None:
      print "Saving to %s" % (outfname)
      cv.SaveImage(outfname, out_img)

   #show(out_img)



if __name__ == "__main__":
   import sys
   main(sys.argv)
