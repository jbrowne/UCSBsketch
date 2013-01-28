#!/usr/bin/env python
from Image import Image
from Utils.CamArea import warpFrame
from cv2 import cv
from sketchvision import ImageStrokeConverter as ISC

def main():
    warpCorners = []
    capture, dimensions = initializeCapture(dims = (1600, 1050))
    windowCorners = [ (0,0), (dimensions[0], 0), (dimensions[0], dimensions[1]), (0, dimensions[1])]
    baseImage = cv.CloneMat(captureImage(capture))
    cv.NamedWindow("Output")
    cv.SetMouseCallback("Output", lambda e, x, y, f, p: onMouseDown(warpCorners, e, x, y, f,p))
    while True:
        image = captureImage(capture)
        image = cleanEdges(image)
        if len(warpCorners) == 4:
            image = warpFrame(image, warpCorners, windowCorners)

        displayImage = processImage(baseImage, image)
        cv.ShowImage("Output", displayImage)

        key = cv.WaitKey(50)
        if key != -1:
            key = chr(key % 256)
        if key == 'r':
            print "Reset Base Image"
            baseImage = cv.CloneMat(image)
        if key == 'q':
            print "Quitting"
            break
        
    cv.DestroyAllWindows()
    
    
def cleanEdges(image):
    """Emphasize the edges around ink strokes"""
    erodedImage = cv.CloneMat(image)
    cv.Erode(image, erodedImage)
#    cv.ShowImage("Eroded", erodedImage)
#    cv.Smooth(erodedImage, erodedImage)
    edgeMask = cv.CreateMat(image.rows, image.cols, cv.CV_8UC1)
    cv.Canny(max_allChannel(image), edgeMask, 50, 100)
    cv.Threshold(edgeMask, edgeMask, 1, 255, cv.CV_THRESH_BINARY_INV)
    cv.Copy(image, erodedImage, edgeMask)
    return erodedImage

def onMouseDown(warpCorners, event, x, y, flags, param):
    if event == cv.CV_EVENT_LBUTTONDOWN:
        if len(warpCorners) == 4:
            warpCorners.pop()
            warpCorners.pop()
            warpCorners.pop()
            warpCorners.pop()
        else:        
            print "Adding Corner %s" % ( (x,y,), )
            warpCorners.append( (x,y) )

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

def processImage(baseImage, newImage):
    retImage = cv.CloneMat(baseImage)

    diffImage = cv.CloneMat(baseImage)
    cv.AbsDiff(baseImage, newImage, diffImage)
    diffImage = max_allChannel(diffImage)

    edges = cv.CreateMat(newImage.rows, newImage.cols, cv.CV_8UC1)
    cv.Canny(diffImage, edges, 50, 100)
    cv.Dilate(edges, edges, iterations=3)
    cv.Sub(diffImage, edges, diffImage)
    
    granularity = 20 
    step_w = baseImage.cols / granularity
    step_h = baseImage.rows / granularity
    for i in range(granularity):
        for j in range(granularity):
            left = i * step_w
            top = j * step_h
            tileRect = (left, top, step_w, step_h) 
            bwDifftile = cv.GetSubRect(diffImage, tileRect)
            retTile = cv.GetSubRect(retImage, tileRect)
            valueSum = cv.Sum(bwDifftile)[0]
            brightest = 255
            _, brightest, _, _ = cv.MinMaxLoc(bwDifftile)
            if valueSum > step_w * step_h * 5 or brightest > 60:
#                print "Brightest: %s, Sum: %s (%s)" % (brightest, int(valueSum), step_w * step_h * 5)
                baseTile = cv.GetSubRect(baseImage, tileRect)
                cv.Copy(baseTile, retTile)
            else:
                newTile = cv.GetSubRect(newImage, tileRect)
                cv.Copy(newTile, retTile)
    
#    retImage, _ = ISC.removeBackground(retImage)
    return retImage

if __name__ == "__main__":
    main()
