import cv

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
        showResized("Live processed frame", processedFrame, 0.4)
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
        #Generate a mask of where the processed frames have been consistent for a while
        frameDiffMask = max_allChannel(frameDiffSum)
        cv.Threshold(frameDiffMask, frameDiffMask, consistencyThresh, 255, cv.CV_THRESH_BINARY_INV)
        #Copy from the most recent processed frame to the background image
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
              

def showResized(name, image, scale):
    image = resizeImage(image, scale)
    cv.ShowImage(name, image)

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
    
def processImage(bgImage, newImage):
    retImage = cv.CloneMat(bgImage)
    diffImage = cv.CloneMat(bgImage)
    cv.AbsDiff(bgImage, newImage, diffImage)
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
