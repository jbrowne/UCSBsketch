#!/usr/bin/env python
from Utils import ForegroundFilter as ff
from cv2 import cv
from sketchvision import ImageStrokeConverter as ISC
from Utils.ForegroundFilter import max_allChannel
from Utils.ForegroundFilter import ForegroundFilter
from ImageShow import show
MAXCAPSIZE = (2592, 1944)
HD1080 = (1920, 1080)
HD720 = (1280, 720)


class BoardChangeWatcher(object):
    """This class watches a whiteboard, and bundles up
    changes of the board's contents as discreet "diff" events"""
    def __init__(self):
        self._fgFilter = ForegroundFilter()
        self._boardDiffHist = []
        self._lastCaptureImage = None
    
    def reset(self):
        self._fgFilter = ForegroundFilter()
        self._boardDiffHist = []
        self._lastCaptureImage = None
        
    def setBoardImage(self, image):
        print "Setting board image"
        self._lastCaptureImage = cv.CloneMat(image)
        self._fgFilter.setBackground(image)
        self._boardDiffHist = []
    
    def updateBoardImage(self, image):
        if self._lastCaptureImage is None:
            self.setBoardImage(image)
            return
        
        self._fgFilter.updateBackground(image)
        #Now that we've updated the background a little bit, analyze the difference from the
        #    previous backgrounds for consistency
        #    background images for consistency
        #Track the new strokes that are added
        captureDiffMask = cv.CloneMat(self._fgFilter.getBackgroundImage())
        cv.AbsDiff(captureDiffMask, self._lastCaptureImage, captureDiffMask)
        captureDiffMask = max_allChannel(captureDiffMask)
        cv.Threshold(captureDiffMask, captureDiffMask, 50, 255, cv.CV_THRESH_BINARY)
        if len(self._boardDiffHist) > 5:
            self._boardDiffHist.pop(0)
        self._boardDiffHist.append(captureDiffMask)
        
        prev = None
        cumulativeDiff = None
        thisDiff = None
        for frame in self._boardDiffHist:
            if prev is None:
                prev = frame
                cumulativeDiff = cv.CreateMat(prev.rows, prev.cols, prev.type)
                cv.Set(cumulativeDiff, (0,0,0))
                thisDiff = cv.CreateMat(prev.rows, prev.cols, prev.type)
            else:
                cv.AbsDiff(prev, frame, thisDiff)
                cv.Max(thisDiff, cumulativeDiff, cumulativeDiff)
        #Now that we have the max sequential difference between frames,
        #    smooth out the edge artifacts due to noise
        cv.Smooth(cumulativeDiff, cumulativeDiff, smoothtype=cv.CV_MEDIAN)
        #The difference percentage is in terms of the size of the changed component from the background
        percentDiff = cv.CountNonZero(cumulativeDiff) / float(max(cv.CountNonZero(captureDiffMask), 1))
        if percentDiff < 0.02 and percentDiff > 0.001:
            self.isCaptureReady = True
        else:
            self.isCaptureReady = False

    def captureBoardDifferences(self):
        """Returns a tuple of binary images: (darkerDiff, lighterDiff)
        where the non-zero mask in darkerDiff is the board contents that 
        is darker than the last capture, and lighterDiff is the contents
        that is lighter. 
        Should check isCaptureReady field before using the results"""
        differenceThresh = 25
        darkerDiff = cv.CreateMat(self._lastCaptureImage.rows, self._lastCaptureImage.cols, cv.CV_8UC1)
        lighterDiff = cv.CloneMat(darkerDiff)

        curBackground = self._fgFilter.getBackgroundImage()
        subtractedImage = cv.CloneMat(curBackground)
        
        cv.Sub(self._lastCaptureImage, curBackground, subtractedImage)
#        darkerDiff = max_allChannel(subtractedImage)
        cv.Threshold(max_allChannel(subtractedImage), darkerDiff, differenceThresh, 255, cv.CV_THRESH_TOZERO)
        cv.Smooth(darkerDiff, darkerDiff, smoothtype=cv.CV_MEDIAN)

        cv.Sub(curBackground, self._lastCaptureImage, subtractedImage)
#        lighterDiff = max_allChannel(subtractedImage)
        cv.Threshold(max_allChannel(subtractedImage), lighterDiff, differenceThresh, 255, cv.CV_THRESH_TOZERO)            
        cv.Smooth(lighterDiff, lighterDiff, smoothtype=cv.CV_MEDIAN)
        
        #Check to see if the "darker" or "lighter" differences are from edge 
        #    digitization artifacts (the board is lighter around dark marks) 
#        validDiffCheckImage = cv.CloneMat(darkerDiff)
#        cv.Erode(validDiffCheckImage, validDiffCheckImage, iterations=3)
#        validity = cv.CountNonZero(validDiffCheckImage)
#        print " Darker Validity: %s" % (validity)
#        if not validity > 0:
#            print " Not counting 'Darker'"
#            cv.Set(darkerDiff, 0)
#
#        validDiffCheckImage = cv.CloneMat(lighterDiff)
#        cv.Erode(validDiffCheckImage, validDiffCheckImage, iterations=3)
#        validity = cv.CountNonZero(validDiffCheckImage)
#        print " Lighter Validity: %s" % (validity)
#        if not validity > 0:
#            print " Not counting 'Lighter'"
#            cv.Set(lighterDiff,0)
        
        retImage = cv.CreateMat(darkerDiff.rows, darkerDiff.cols, cv.CV_8UC1)
        cv.Set(retImage, 128)
        cv.Sub(retImage, darkerDiff, retImage)
        cv.Add(retImage, lighterDiff, retImage)
        showResized("BoardDiffs", retImage, 0.3)
        showResized("Darker", darkerDiff, 0.25)
        showResized("Lighter", lighterDiff, 0.25)       
        return (darkerDiff, lighterDiff)
        
        
        

def main():
    displayScale = 0.4
    warpCorners = [(1177.5, 722.5), (2245.0, 135.0), (2380.0, 1577.5), (1070.0, 1537.5)]
#    fgFilter = ff.ForegroundFilter()
    boardCapture = BoardChangeWatcher()
    capture, dimensions = initializeCapture(dims = MAXCAPSIZE)
    windowCorners = [ (0,0), (dimensions[0], 0), (dimensions[0], dimensions[1]), (0, dimensions[1])]
    baseImage = cv.CloneMat(captureImage(capture))
    boardCapture.setBoardImage(baseImage)
#    fgFilter.setBackground(baseImage)
    cv.NamedWindow("Output")
    cv.SetMouseCallback("Output", lambda e, x, y, f, p: onMouseDown(warpCorners, e, x/displayScale, y/displayScale, f, p))
    i = 0
#    diffHistory = []
    while True:
        image = captureImage(capture)
        if len(warpCorners) == 4:
            image = warpFrame(image, warpCorners, windowCorners)
   
#        fgFilter.updateBackground(image)
        boardCapture.updateBoardImage(image)
        displayImage = boardCapture._fgFilter.getBackgroundImage()
        displayImage = resizeImage(displayImage, scale=displayScale)
        cv.ShowImage("Output", displayImage)

#        prevBGImage = boardCapture._fgFilter.getBackgroundImage()
        (darkerDiff, lighterDiff) = boardCapture.captureBoardDifferences()
        if boardCapture.isCaptureReady:
            ISC.saveimg(boardCapture._lastCaptureImage)
            cv.AddWeighted(darkerDiff, -1, darkerDiff, 0.0, 255, darkerDiff)
            cv.AddWeighted(lighterDiff, -1, lighterDiff, 0.0, 255, lighterDiff)
            ISC.saveimg(darkerDiff)
            ISC.saveimg(lighterDiff)
            boardCapture.setBoardImage(boardCapture._fgFilter.getBackgroundImage())
#        #Track the new strokes that are added
#        captureDiff = cv.CloneMat(fgFilter.getBackgroundImage())
#        cv.AbsDiff(captureDiff, lastCaptureImage, captureDiff)
#        captureDiff = max_allChannel(captureDiff)
#        cv.Threshold(captureDiff, captureDiff, 50, 255, cv.CV_THRESH_BINARY)
#
#        
#        #Initiate a new capture when the changes settle
#        captureChanges = trackChanges(captureDiff, diffHistory)
#        if captureChanges < 0.02 and captureChanges > 0.001:
#            print "CAPTURE"
#            lastCaptureImage = cv.CloneMat(fgFilter.getBackgroundImage())
#            fgFilter.setBackground(lastCaptureImage)
#            diffHistory = []            
##        showResized("LastDiff", captureDiff, displayScale)
        key = cv.WaitKey(50)
        if key != -1:
            key = chr(key % 256)
        if key == 'r':
            boardCapture.setBoardImage(image)
#            fgFilter.setBackground(image)
#            key = 'c'
#        if key == 'c':
#            lastCaptureImage = cv.CloneMat(fgFilter.getBackgroundImage())
#            fgFilter.setBackground(lastCaptureImage)
#            diffHistory = []
        if key == 'q':
            print "Quitting"
            break
        i+=1
        
    cv.DestroyAllWindows()
    

def trackChanges(image, history):
    if len(history) > 5:
        history.pop(0)
    history.append(image)
    prev = None
    cumulativeDiff = None
    thisDiff = None
    for frame in history:
        if prev is None:
            prev = frame
            cumulativeDiff = cv.CreateMat(prev.rows, prev.cols, prev.type)
            cv.Set(cumulativeDiff, (0,0,0))
            thisDiff = cv.CreateMat(prev.rows, prev.cols, prev.type)
        else:
            cv.AbsDiff(prev, frame, thisDiff)
            cv.Max(thisDiff, cumulativeDiff, cumulativeDiff)
    cv.Smooth(cumulativeDiff, cumulativeDiff, smoothtype=cv.CV_MEDIAN)
    percentDiff = cv.CountNonZero(cumulativeDiff) / float(max(cv.CountNonZero(image), 1))
#    print "Percent Diff : %03f)" % (percentDiff)
#    showResized("HistoryDiff", cumulativeDiff, 0.4)
    return percentDiff
    
        
    
def showResized(name, image, scale):
    image = resizeImage(image, scale)
    cv.ShowImage(name, image)
    
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

def resizeImage(img, scale=None, dims=None):
    """Return a resized copy of the image for either relative
    scale, or that matches the dimensions given"""
    if scale is not None:
        retImg = cv.CreateMat(int(img.rows * scale), int(img.cols * scale), img.type)
    elif dims is not None:
        retImg = cv.CreateMat(dims[0], dims[1], img.type)
    else:
        retImg = cv.CloneMat(img)
    cv.Resize(img, retImg)
    return retImg

if __name__ == "__main__":
    from Utils.CamArea import warpFrame
    main()
