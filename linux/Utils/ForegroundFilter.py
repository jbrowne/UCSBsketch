if __name__ == "__main__":
    import sys
    sys.path.append("./")
from Utils.ImageUtils import captureImage
from Utils.ImageUtils import initializeCapture
from Utils.ImageUtils import max_allChannel
from Utils.ImageUtils import showResized
from Utils.ImageUtils import warpFrame
from sketchvision.ImageStrokeConverter import saveimg
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

class ForegroundFilter(object):
    def __init__(self):
        #Complete model of board contents
        self._bgImage = None
        self._processedFramesHist = None
        self._bgImagesHist = None
        self.initialize()
        
        
    def initialize(self):
        self._bgImage = None
        self._processedFramesHist = []
        self._bgImagesHist = []
 
 
    def setBackground(self, image):
        self._bgImage = cv.CloneMat(image)
        self._processedFramesHist = [cv.CloneMat(image)]
        self._bgImagesHist = [cv.CloneMat(image)]
        
        
    def updateBackground(self, newImage):
        """Given a new image (possibly containing occluding objects)
        update the model of the background board"""
        if self._bgImage is None:
            self.setBackground(newImage)
            return
        historyLength = 5
        consistencyThresh = 10
        #Watch for the processed frames to settle,
        # and only update the background image
        # if a majority of the last N frames agree
        if len(self._processedFramesHist) >= historyLength:
            self._processedFramesHist.pop(0)
        processedFrame = processImage(self._bgImage, newImage)
        self._processedFramesHist.append(processedFrame)

        prevFrame = None
        frameDiffSum = None
        for frame in self._processedFramesHist:
            if prevFrame is None:
                prevFrame = frame
                frameDiffSum = cv.CloneMat(frame)
                cv.Set(frameDiffSum, (0,0,0))
                continue
            diffImage = cv.CloneMat(prevFrame)
            cv.AbsDiff(prevFrame, frame, diffImage)
#            cv.AddWeighted(diffImage, 0.5, frameDiffSum, 0.5, 0.0, frameDiffSum)
            cv.Max(diffImage, frameDiffSum, frameDiffSum)
        # Generate a mask of where the processed frames have been consistent for a while
        frameDiffMask = max_allChannel(frameDiffSum)
        cv.Threshold(frameDiffMask, frameDiffMask, consistencyThresh, 255, cv.CV_THRESH_BINARY_INV)
        # Copy from the most recent processed frame to the background image
        cv.Copy(processedFrame, self._bgImage, mask=frameDiffMask)


    def filterForeground(self, newImage):
        diffImage = cv.CloneMat(self._bgImage)
        retImage = cv.CloneMat(newImage)
        cv.AbsDiff(newImage, self._bgImage, diffImage)
#        cv.CvtColor(diffImage, diffImage, cv.CV_RGB2GRAY)
        cv.AddWeighted(retImage, 1.0, diffImage, 0.5, 0.0, retImage)
        return retImage
    
    def getBackgroundImage(self):
        if self._bgImage is not None:
            return cv.CloneMat(self._bgImage)
        else:
            return None
              


    
def processImage(bgImage, newImage):
    erodeIterations = max(bgImage.cols/256, bgImage.rows/256, 1)
    smoothKernel = max(bgImage.cols / 50, bgImage.rows / 50, 1)
    if smoothKernel % 2 == 0:
        smoothKernel += 1

    retImage = cv.CloneMat(bgImage)
    diffImage = cv.CloneMat(bgImage)
    cv.AbsDiff(bgImage, newImage, diffImage)
    diffImage = max_allChannel(diffImage)

    #Get the diff without "small" components (e.g. writing)
    diffImageEroded = cv.CloneMat(diffImage)
    cv.Erode(diffImageEroded, diffImageEroded, iterations = erodeIterations)
    cv.Dilate(diffImageEroded, diffImageEroded, iterations = erodeIterations)

    #Figure out if the thin change is due to something big covering
    # the writing, i.e. a large region of high difference surrounding it
    smoothDiff = cv.CloneMat(diffImage)
    cv.Smooth(smoothDiff, smoothDiff, smoothtype=cv.CV_MEDIAN, param1=smoothKernel, param2=smoothKernel)
    largeBlobMask = cv.CreateMat(diffImage.rows, diffImage.cols, diffImage.type)
    cv.AbsDiff(smoothDiff, diffImageEroded, largeBlobMask)
    
    cv.Threshold(largeBlobMask, largeBlobMask, 20, 255, cv.CV_THRESH_BINARY_INV)
    cv.Erode(largeBlobMask, largeBlobMask, iterations=4)

    #Get the parts that were completely erased due to the opening
    cv.AbsDiff(diffImage, diffImageEroded, diffImageEroded)
    cv.Threshold(diffImageEroded, diffImageEroded, 20, 255, cv.CV_THRESH_BINARY)
    cv.Dilate(diffImageEroded, diffImageEroded, iterations=2)

#    showResized("Interesting Differences", diffImageEroded, 0.4)
#    showResized("Differences to ignore", largeBlobMask, 0.4)
    
    cv.And(diffImageEroded, largeBlobMask, diffImageEroded)

    cv.Copy(newImage, retImage, diffImageEroded)

    return retImage


def main(args):
    if len(args) > 1:
        camNum = int(args[1])
        print "Using cam %s" % (camNum,)
    else:
        camNum = 0
    capture, dims = initializeCapture(cam = camNum, dims=CAPSIZE02)    
    warpCorners = [(766.7376708984375, 656.48828125), (1059.5025634765625, 604.4216918945312), (1048.0185546875, 837.3212280273438), (733.5200805664062, 880.5441284179688)]
    targetCorners_Chess = [(5*dims[0]/16.0, 5*dims[1]/16.0),
                         (11*dims[0]/16.0, 5*dims[1]/16.0),
                         (11*dims[0]/16.0, 11*dims[1]/16.0),
                         (5*dims[0]/16.0, 11*dims[1]/16.0),] 
    
    fgFilter = ForegroundFilter()
    while True:
        image = captureImage(capture)
#        image = warpFrame(image, warpCorners, targetCorners_Chess)
        
        fgFilter.updateBackground(image)
        dispImage = fgFilter.getBackgroundImage()
        
        showResized("Foreground Filter", dispImage, 0.5)
        key = cv.WaitKey(10)
        if key != -1:
            key = chr(key%256)
            if key == 'q':
                break
            if key == 'r':
                fgFilter.setBackground(image)
    cv.DestroyAllWindows()
                
        
    
if __name__ == "__main__":
    main(sys.argv)
