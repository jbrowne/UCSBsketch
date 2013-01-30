import cv

class ForegroundFilter(object):
    def __init__(self):
        #Complete model of board contents
        self._bgImage = None
        self._lastFrames = []
        
    def reset(self):
        self._bgImage = None
        self._lastFrames = []
        
    def setBackground(self, image):
        self._bgImage = cv.CloneMat(image)
        self._lastFrames = []
        
    def updateBackground(self, newImage):
        """Given a new image (possibly containing occluding objects)
        update the model of the background board"""
        if self._bgImage is None:
            self._bgImage = cv.CloneMat(newImage)
            return
        
        if len(self._lastFrames) >= 5:
            self._lastFrames.pop(0)
        self._lastFrames.append(processImage(self._bgImage, newImage))
        
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
#            cv.AddWeighted(frame, 0.5, blendFrame, 0.5, 0.0, blendFrame)
            diffImage = cv.CloneMat(prevFrame)
            cv.AbsDiff(prevFrame, frame, diffImage)
#            cv.AddWeighted(diffImage, blendRatio, frameDiffSum, 1.0, 0.0, frameDiffSum)
            cv.Max(diffImage, frameDiffSum, frameDiffSum)
        frameDiffMask = max_allChannel(frameDiffSum)
        cv.Threshold(frameDiffMask, frameDiffMask, 20, 255, cv.CV_THRESH_BINARY_INV)
        cv.Copy(blendFrame, self._bgImage, mask=frameDiffMask)

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
