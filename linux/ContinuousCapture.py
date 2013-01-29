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
        self._bgImage = None
        self._lastFrames = []
    def setBackground(self, image):
        self._bgImage = cv.CloneMat(image)
        self._lastFrames = []
        
    def updateBackground(self, newImage):
        """Given a new image (possibly containing occluding objects)
        update the model of the background board"""
        if len(self._lastFrames) >= 10:
            self._lastFrames.pop(0)
        self._lastFrames.append(self.filterForeground(newImage))
        
        blendFrame = None
        prevFrame = None
        frameDiffSum = None
#        blendRatio = 1 / float(len(self._lastFrames))
        for frame in self._lastFrames:
            if prevFrame is None:
                prevFrame = frame
                frameDiffSum = cv.CloneMat(frame)
                blendFrame = cv.CloneMat(frame)
                cv.Set(frameDiffSum, (0,0,0))
                continue
            cv.AddWeighted(frame, 0.5, blendFrame, 0.5, 0.0, blendFrame)
            diffImage = cv.CloneMat(prevFrame)
            cv.AbsDiff(prevFrame, frame, diffImage)
#            cv.AddWeighted(diffImage, blendRatio, frameDiffSum, 1.0, 0.0, frameDiffSum)
            cv.Max(diffImage, frameDiffSum, frameDiffSum)
        frameDiffMask = max_allChannel(frameDiffSum)
        cv.Threshold(frameDiffMask, frameDiffMask, 10, 255, cv.CV_THRESH_BINARY_INV)
        cv.Copy(blendFrame, self._bgImage, mask=frameDiffMask)

    def filterForeground(self, newImage):
        retImage = cv.CloneMat(self._bgImage)
        diffImage = cv.CloneMat(self._bgImage)
        cv.AbsDiff(self._bgImage, newImage, diffImage)
        diffImage = max_allChannel(diffImage)
        
        diffImageEroded = cv.CloneMat(diffImage)
        cv.Erode(diffImageEroded, diffImageEroded, iterations = 5)
        cv.Dilate(diffImageEroded, diffImageEroded, iterations = 5)
        
        #Get the parts that were completely erased due to the opening
        cv.AbsDiff(diffImage, diffImageEroded, diffImageEroded)
        cv.Dilate(diffImageEroded, diffImageEroded, iterations = 5)
        cv.Threshold(diffImageEroded, diffImageEroded, 24, 255, cv.CV_THRESH_BINARY)
        cv.Dilate(diffImageEroded, diffImageEroded, iterations=3)
        cv.Copy(newImage, retImage, diffImageEroded)
        return retImage
    
    def getBackgroundImage(self):
        return cv.CloneMat(self._bgImage)
        

def main():
    warpCorners = [(337, 219), (929, 27), (957, 688), (240, 667)]
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
   
        fgFilter.updateBackground(image)
#        displayImage = fgFilter.filterForeground(image)
        displayImage = fgFilter.getBackgroundImage()
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
