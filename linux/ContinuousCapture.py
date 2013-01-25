#!/usr/bin/env python
from Image import Image
from cv2 import cv
from sketchvision import ImageStrokeConverter as ISC

def main():
    capture, _ = initializeCapture(dims = (1280, 1024))
    baseImage = cv.CloneMat(captureImage(capture))
    while True:
        image = captureImage(capture)
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

def initializeCapture(dims=(1280, 1024,)):
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
    cv.ShowImage("Channel1", ch1)
    cv.ShowImage("Channel2", ch2)
    cv.ShowImage("Channel3", ch3)
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
    
    granularity = 50 
    cv.ShowImage("Difference", diffImage)
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
                print "Brightest: %s, Sum: %s (%s)" % (brightest, int(valueSum), step_w * step_h * 5)
                baseTile = cv.GetSubRect(baseImage, tileRect)
                cv.Copy(baseTile, retTile)
            else:
                newTile = cv.GetSubRect(newImage, tileRect)
                cv.Copy(newTile, retTile)
    
    retImage, _ = ISC.removeBackground(retImage)
    return retImage

if __name__ == "__main__":
    main()
