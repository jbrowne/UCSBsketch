from Utils.ForegroundFilter import ForegroundFilter
from Utils.ForegroundFilter import max_allChannel, showResized
import cv

class BoardChangeWatcher(object):
    """This class watches a whiteboard, and bundles up
    changes of the board's contents as discreet "diff" events"""
    def __init__(self):
        self._fgFilter = ForegroundFilter()
        self._boardDiffHist = []
        self._lastCaptureImage = None
        self.isCaptureReady = False

    
    def reset(self):
        self._fgFilter = ForegroundFilter()
        self._boardDiffHist = []
        self._lastCaptureImage = None
        self.isCaptureReady = False

        
    def setBoardImage(self, image):
        print "Setting board image"
        self._lastCaptureImage = cv.CloneMat(image)
        self._fgFilter.setBackground(image)
        self._boardDiffHist = []
        self.isCaptureReady = False

    
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
        
        retImage = cv.CreateMat(darkerDiff.rows, darkerDiff.cols, cv.CV_8UC1)
        cv.Set(retImage, 128)
        cv.Sub(retImage, darkerDiff, retImage)
        cv.Add(retImage, lighterDiff, retImage)
#        showResized("BoardDiffs", retImage, 0.3)
#        showResized("Darker", darkerDiff, 0.25)
#        showResized("Lighter", lighterDiff, 0.25)       
        return (darkerDiff, lighterDiff)