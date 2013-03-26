from Utils.ImageUtils import captureImage
from Utils.ImageUtils import changeExposure
from Utils.ImageUtils import getFillPoints
from Utils.ImageUtils import initializeCapture
from Utils.ImageUtils import max_allChannel
from Utils.ImageUtils import showResized
from Utils.ImageUtils import warpFrame
from sketchvision.ImageStrokeConverter import saveimg
import cv
import os
import sys
import threading
import time
if __name__ == "__main__":
    sys.path.append("./")

CAPSIZE00 = (2592, 1944)
CAPSIZE01 = (2048,1536)
CAPSIZE02 = (1600,1200)
CAPSIZE02 = (1280, 960)
CAPSIZE03 = (960, 720)
CAPSIZE04 = (800, 600)
PROJECTORSIZE = (1024, 768)

DEBUG = False

class ForegroundFilter(object):
    def __init__(self):
        #Complete model of board contents
        self._bgImage = None

 
    def setBackground(self, image):
        self._bgImage = cv.CloneMat(image)
        
        
    def updateBackground(self, newImage):
        """Given a new image (possibly containing occluding objects)
        update the model of the background board"""
        if self._bgImage is None:
            self.setBackground(newImage)
            return

        self._bgImage = processImage(self._bgImage, newImage)
        return self._bgImage

    def filterForeground(self, newImage):
        diffImage = cv.CloneMat(self._bgImage)
        retImage = cv.CloneMat(newImage)
        cv.AbsDiff(newImage, self._bgImage, diffImage)
        cv.AddWeighted(retImage, 1.0, diffImage, 0.5, 0.0, retImage)
        return retImage
    
    def getBackgroundImage(self):
        if self._bgImage is not None:
            return cv.CloneMat(self._bgImage)
        else:
            return None
              


    
def processImage(bgImage, newImage):
    """Within a single frame, try to filter out non-ink occlusions,
    given an image of roughly the background"""
    erodeIterations = max(bgImage.cols/256, bgImage.rows/256, 1)
    smoothKernel = max(bgImage.cols / 50, bgImage.rows / 50, 1)
    if smoothKernel % 2 == 0:
        smoothKernel += 1

    #Get a mask of the places that are too dark to be a whiteboard
    backgroundThresh = 120
    obviousBackgroundMask = cv.CreateMat(newImage.rows, newImage.cols, cv.CV_8UC1)
    cv.CvtColor(newImage, obviousBackgroundMask, cv.CV_RGB2GRAY)
    cv.Threshold(obviousBackgroundMask, obviousBackgroundMask, 
                 backgroundThresh, 255, cv.CV_THRESH_BINARY)
    cv.Dilate(obviousBackgroundMask, obviousBackgroundMask, iterations = 5)
    cv.Erode(obviousBackgroundMask, obviousBackgroundMask, iterations = 5)

    #Get the raw diff from the background
    retImage = cv.CloneMat(bgImage)
    diffImage = cv.CloneMat(bgImage)
    cv.AbsDiff(bgImage, newImage, diffImage)
    diffImage = max_allChannel(diffImage)

    #Get the diff without "small" components (e.g. writing)
    # by performing a "close" on small components
    diffImageEroded = cv.CloneMat(diffImage)
    cv.Erode(diffImageEroded, diffImageEroded, iterations = erodeIterations)
    cv.Dilate(diffImageEroded, diffImageEroded, iterations = erodeIterations)

    #Get the parts that were completely erased due to the opening,
    # and correspond to thin, ink-like differences
    inkDifferences = cv.CloneMat(diffImage)
    cv.AbsDiff(diffImage, diffImageEroded, inkDifferences)
    cv.Smooth(inkDifferences, inkDifferences, smoothtype=cv.CV_MEDIAN)
    cv.Dilate(inkDifferences, inkDifferences, iterations=4)
    cv.Erode(inkDifferences, inkDifferences, iterations=2)
    cv.Threshold(inkDifferences, inkDifferences, 20, 255, cv.CV_THRESH_BINARY)
    
    #Figure out if the thin change is due to something big covering
    # the writing, i.e. a large region of high difference surrounding it
    smoothDiff = cv.CloneMat(diffImage)
    cv.Smooth(diffImage, smoothDiff, smoothtype=cv.CV_MEDIAN, param1=smoothKernel, param2=smoothKernel)
    
    #Don't count ink-differences covered by large change components
    largeBlobMask = cv.CreateMat(diffImage.rows, diffImage.cols, diffImage.type)
    cv.AbsDiff(smoothDiff, diffImageEroded, largeBlobMask)
    cv.Max(largeBlobMask, smoothDiff, largeBlobMask)

    cv.Threshold(largeBlobMask, largeBlobMask, 30, 255, cv.CV_THRESH_BINARY)
    cv.Dilate(largeBlobMask, largeBlobMask, iterations=4)
    
    # Only consider the changes that are small, and not a result of occlusion
    # Remove from the blend mask anything connected to obvious foreground
    #    differences
    fillPoints = getFillPoints(largeBlobMask)
    finalInkMask = cv.CloneMat(inkDifferences)
    cv.Max(largeBlobMask, inkDifferences, finalInkMask)
    for pt in fillPoints:
        cv.FloodFill(finalInkMask, pt, 0)
    
    cv.And(obviousBackgroundMask, finalInkMask, finalInkMask)
    
    # Actually integrate the changes
    cv.Copy(newImage, retImage, finalInkMask)
    
    # Debug the masks
    if DEBUG:
        tempMat = cv.CloneMat(finalInkMask)
        cv.AddWeighted(inkDifferences, 0.5, tempMat, 0.5, 0.0, tempMat)
        showResized("Mask Combo", tempMat, 0.5)
        cv.AddWeighted(largeBlobMask, 1.0, inkDifferences, -0.5, 0.0, tempMat)
        showResized("Blob coverage", tempMat, 0.5)
        showResized("ObviousBackground", obviousBackgroundMask, 0.5)
    # /Debug

    return retImage


def main(args):
    global DEBUG
    DEBUG = True
    if len(args) > 1:
        camNum = int(args[1])
        print "Using cam %s" % (camNum,)
    else:
        camNum = 0
    capture, dims = initializeCapture(cam = camNum, dims=CAPSIZE02)    
    dispScale = 0.5    
    warpCorners = []
    targetCorners = [ (0,0), (dims[0], 0), (dims[0], dims[1]), (0, dims[1]) ] 
    
    def onMouseClick(event, x,y, flags, param):
        if event == cv.CV_EVENT_LBUTTONUP:
            if len(warpCorners) == 4:
                warpCorners.pop()
                warpCorners.pop()
                warpCorners.pop()
                warpCorners.pop()
            else:
                print "Adding warp corner {}".format( (x,y,) )
                warpCorners.append((x/dispScale,y/dispScale,))
    cv.NamedWindow("Foreground Filter")
    cv.SetMouseCallback("Foreground Filter", onMouseClick)    
    fgFilter = ForegroundFilter()
    while True:
        image = captureImage(capture)
        if len(warpCorners) == 4: 
            image = warpFrame(image, warpCorners, targetCorners)
        fgFilter.updateBackground(image)
        dispImage = fgFilter.getBackgroundImage()
        
        showResized("Foreground Filter", dispImage, dispScale)
        key = cv.WaitKey(10)
        if key != -1:
            key = chr(key%256)
            if key == 'q':
                break
            if key == 'r':
                fgFilter.setBackground(image)
            if key in ('+', '='):
                changeExposure(camNum, 100)
            elif key in ('-', '_'):
                changeExposure(camNum, -100)
    cv.DestroyAllWindows()
                
        
    
if __name__ == "__main__":
    main(sys.argv)
