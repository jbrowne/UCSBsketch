#!/usr/bin/env python
from Image import Image
from Utils.CamArea import warpFrame
from cv2 import cv
from sketchvision import ImageStrokeConverter as ISC

MAXCAPSIZE = (2592, 1944)
HD1080 = (1920, 1080)
HD720 = (1280, 720)

class ForegroundFilter(object):
    def __init__(self):
        #Complete model of board contents
        self.bgImage = None
    def setBackground(self, image):
        self.bgImage = cv.CloneMat(image)
        
    def updateBackground(self, newImage):
        """Given a new image (possibly containing occluding objects)
        update the model of the background board"""
#        self.bgImage = processImage(self.bgImage, newImage)
    
    def filterForeground(self, newImage):
        retImage = cv.CloneMat(self.bgImage)
        diffImage = cv.CloneMat(self.bgImage)
        cv.AbsDiff(self.bgImage, newImage, diffImage)
        diffImage = max_allChannel(diffImage)
#        cv.Smooth(diffImage, diffImage, smoothtype=cv.CV_MEDIAN)
#        cv.ShowImage("RawDifference", diffImage)
        
        diffImageEroded = cv.CloneMat(diffImage)
#        cv.Smooth(diffImage, diffImageEroded)

        cv.Erode(diffImageEroded, diffImageEroded, iterations = 5)
        cv.Dilate(diffImageEroded, diffImageEroded, iterations = 5)
        
        #Get the parts that were completely erased due to the opening
#        cv.ShowImage("Eroded Difference", diffImageEroded)
        cv.AbsDiff(diffImage, diffImageEroded, diffImageEroded)
        cv.Dilate(diffImageEroded, diffImageEroded, iterations = 5)
#        cv.ShowImage("Separated Difference", diffImageEroded)
        cv.Threshold(diffImageEroded, diffImageEroded, 24, 255, cv.CV_THRESH_BINARY)
        cv.Dilate(diffImageEroded, diffImageEroded, iterations=3)

#        cv.Erode(diffImageEroded, diffImageEroded)
    #    cv.AdaptiveThreshold(diffImageEroded, diffImageEroded, 255)
        cv.Copy(newImage, retImage, diffImageEroded)
        return retImage
    
    def getBackgroundImage(self):
        return cv.CloneMat(self.bgImage)
        

def main():
    warpCorners = [(434, 240), (900, 52), (893, 636), (362, 631)]
    fgFilter = ForegroundFilter()
    capture, dimensions = initializeCapture(dims = HD720)
    windowCorners = [ (0,0), (dimensions[0], 0), (dimensions[0], dimensions[1]), (0, dimensions[1])]
    baseImage = cv.CloneMat(captureImage(capture))
    fgFilter.setBackground(baseImage)
    cv.NamedWindow("Output")
    cv.SetMouseCallback("Output", lambda e, x, y, f, p: onMouseDown(warpCorners, e, x, y, f, p))
    _, historyImage = diffSettled(baseImage, baseImage)
    i = 0
    while True:
        image = captureImage(capture)
        if len(warpCorners) == 4:
            image = warpFrame(image, warpCorners, windowCorners)
   
        displayImage = fgFilter.filterForeground(image)
        isSettled, historyImage = diffSettled(historyImage, displayImage)

        cv.ShowImage("Output", displayImage)

        key = cv.WaitKey(50)
        if key != -1:
            key = chr(key % 256)
        if key == 'r':
            fgFilter.setBackground(image)
            _, historyImage = diffSettled(baseImage, baseImage)
        if key == 'q':
            print "Quitting"
            break
        i+=1
        
    cv.DestroyAllWindows()
    
    
def diffSettled(historyImage, curImage):
    """Return a new history image, and True/False whether
    the differences have settled and should update the base image"""
    diffImage = cv.CloneMat(historyImage)
    retImage = cv.CloneMat(historyImage)
    cv.AbsDiff(historyImage, curImage, diffImage)
    diffImage = max_allChannel(diffImage)
#    cv.ShowImage("Difference", diffImage)
#    cv.ShowImage("CurImage", curImage)
    
    (minVal, maxVal, minLoc, maxLoc) = cv.MinMaxLoc(diffImage)
#    print "Max Value %s" % (maxVal,)
    if (maxVal < 25):
        isSettled = True
    else:
        isSettled = False
        
    cv.AddWeighted(historyImage, 0.95, curImage, 0.05, 0.0, retImage)
#    cv.ShowImage("BlendImage", retImage)
    return (isSettled, retImage)
    
def onMouseDown(warpCorners, event, x, y, flags, param):
    if event == cv.CV_EVENT_LBUTTONDOWN:
        if len(warpCorners) == 4:
            warpCorners.pop()
            warpCorners.pop()
            warpCorners.pop()
            warpCorners.pop()
        else:        
            warpCorners.append( (x,y) )
            if len(warpCorners) == 4:
                print "Corners: %s" % (warpCorners)

def initializeCapture(dims=(1280, 1024,)):
    """Try to initialize the capture to the requested dimensions. 
    Returns the capture and the actual dimensions"""
    capture = cv.CaptureFromCAM(-1)
    w, h = dims
    cv.SetCaptureProperty(capture, cv.CV_CAP_PROP_FRAME_HEIGHT, h) 
    cv.SetCaptureProperty(capture, cv.CV_CAP_PROP_FRAME_WIDTH, w)
    reth = int(cv.GetCaptureProperty(capture, cv.CV_CAP_PROP_FRAME_HEIGHT))
    retw = int(cv.GetCaptureProperty(capture, cv.CV_CAP_PROP_FRAME_WIDTH))
    return capture, (retw, reth,)

def captureImage(capture):
    """Capture a new image from capture, then set it as the data
    of gtkImage.
    Returns cv Image of the capture"""
    cvImg = cv.QueryFrame(capture)
    #cv.CvtColor(cvImg, cvImg, cv.CV_BGR2RGB)
    cvMat = cv.GetMat(cvImg)
    return cvMat

def max_allChannel(image):
    """Return a grayscale image with values equal to the MAX
    over all 3 channels """
    retImage = cv.CreateMat(image.rows, image.cols, cv.CV_8UC1)
    ch1 = cv.CreateMat(image.rows, image.cols, cv.CV_8UC1)
    ch2 = cv.CreateMat(image.rows, image.cols, cv.CV_8UC1)
    ch3 = cv.CreateMat(image.rows, image.cols, cv.CV_8UC1)
    cv.Split(image, ch1, ch2, ch3, None)
    cv.Max(ch1, ch2, retImage)
    cv.Max(ch3, retImage, retImage)
    return retImage

if __name__ == "__main__":
    main()
