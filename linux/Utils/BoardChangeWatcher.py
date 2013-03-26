from Utils.ImageUtils import changeExposure
if __name__ == "__main__":
    import sys
    sys.path.append("./")
from Utils.ForegroundFilter import ForegroundFilter
from Utils.ImageUtils import captureImage
from Utils.ImageUtils import initializeCapture
from Utils.ImageUtils import max_allChannel
from Utils.ImageUtils import showResized
from Utils.ImageUtils import warpFrame
import cv
import os
import threading
import time

CAPSIZE00 = (2592, 1944)
CAPSIZE01 = (2048,1536)
CAPSIZE02 = (1600,1200)
CAPSIZE02 = (1280, 960)
CAPSIZE03 = (960, 720)
CAPSIZE04 = (800, 600)
PROJECTORSIZE = (1024, 768)

class BoardChangeWatcher(object):
    """This class watches a whiteboard, and bundles up
    changes of the board's contents as discreet "diff" events"""
    def __init__(self):
        self._fgFilter = ForegroundFilter()
        self._boardDiffHist = []
        self._lastCaptureImage = None
        self.isCaptureReady = False
        self._isBoardUpdated = False #Used to track if we've seen changes since last accept

    
    def reset(self):
        self._fgFilter = ForegroundFilter()
        self._boardDiffHist = []
        self._lastCaptureImage = None
        self.isCaptureReady = False
        self._isBoardUpdated = False
        

        
    def setBoardImage(self, image):
        """Force the current background board image to be image"""
        print "Setting board image"
        self._lastCaptureImage = cv.CloneMat(image)
        self._fgFilter.setBackground(image)
        self._boardDiffHist = []
        self.isCaptureReady = False
        self._isBoardUpdated = False
        


    def acceptCurrentImage(self):
        """Confirm the current view of the whiteboard as correct (commit it)"""
        image = self._fgFilter.getBackgroundImage()
        self.setBoardImage(image)
        self.isCaptureReady = False
        self._isBoardUpdated = False        
        return image
        
    
    def updateBoardImage(self, image):
        precentDiffThresh = 0.2
        diffMaskThresh = 50
        windowLen = 2
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
        cv.Threshold(captureDiffMask, captureDiffMask, diffMaskThresh, 255, cv.CV_THRESH_BINARY)

        if len(self._boardDiffHist) > windowLen:
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
        if percentDiff < precentDiffThresh: 
            if self._isBoardUpdated:
                self.isCaptureReady = True
        else:
            #Only set unready if the difference is large
            self.isCaptureReady = False
            self._isBoardUpdated = True




    def captureBoardDifferences(self):
        """Returns a tuple of binary images: (darkerDiff, lighterDiff)
        where the non-zero mask in darkerDiff is the board contents that 
        is darker than the last capture, and lighterDiff is the contents
        that is lighter. 
        Should check isCaptureReady field before using the results"""
        differenceThresh = 10
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
        
        retImage = cv.CreateMat(darkerDiff.rows, darkerDiff.cols, cv.CV_8UC1)
        cv.Set(retImage, 128)
        cv.Sub(retImage, darkerDiff, retImage)
        cv.Add(retImage, lighterDiff, retImage)
#        showResized("BoardDiffs", retImage, 0.3)
#        showResized("Darker", darkerDiff, 0.25)
#        showResized("Lighter", lighterDiff, 0.25)       
        return (darkerDiff, lighterDiff)
    
    
def main(args):
    if len(args) > 1:
        camNum = int(args[1])
        print "Using cam %s" % (camNum,)
    else:
        camNum = 0
    capture, dims = initializeCapture(cam = camNum, dims=CAPSIZE01)    

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
    cv.NamedWindow("Output")
    cv.SetMouseCallback("Output", onMouseClick)
    bcWatcher = BoardChangeWatcher()
    dispImage = captureImage(capture)
    #dispImage = warpFrame(dispImage, warpCorners, targetCorners)

    while True:
        image = captureImage(capture)
        if len(warpCorners) == 4: 
            image = warpFrame(image, warpCorners, targetCorners)
        bcWatcher.updateBoardImage(image)
        showResized("FGFilter", bcWatcher._fgFilter.getBackgroundImage(), 0.4)

        if bcWatcher.isCaptureReady:
            (darker, lighter) = bcWatcher.captureBoardDifferences()
            showResized("Darker", darker, 0.3)
            showResized("Lighter", lighter, 0.3)
            dispImage = bcWatcher.acceptCurrentImage()
        
        showResized("Output", dispImage, dispScale)
        key = cv.WaitKey(50)
        if key != -1:
            key = chr(key%256)
            if key == 'q':
                break
            if key == 'r':
                bcWatcher.setBoardImage(image)
                dispImage = image
            if key in ('+', '='):
                changeExposure(camNum, 100)
            elif key in ('-', '_'):
                changeExposure(camNum, -100)

    cv.DestroyAllWindows()
                
        
    
if __name__ == "__main__":
    main(sys.argv)    
