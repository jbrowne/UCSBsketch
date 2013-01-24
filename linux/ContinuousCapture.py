#!/usr/bin/env python
import cv2
import numpy as np
from cv2 import cv
from Image import Image
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
            print key
        if key == 'r':
            baseImage = cv.CloneMat(image)
        if key == 'q':
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

def processImage(baseImage, newImage):
    retImage = cv.CloneMat(baseImage)
    bwBaseImage = cv.CreateMat(baseImage.rows, baseImage.cols, cv.CV_8UC1)
    cv.CvtColor(baseImage, bwBaseImage, cv.CV_RGB2GRAY)
    bwImage = cv.CreateMat(newImage.rows, newImage.cols, cv.CV_8UC1)
    cv.CvtColor(newImage, bwImage, cv.CV_RGB2GRAY)
    edges = cv.CreateMat(newImage.rows, newImage.cols, cv.CV_8UC1)
    diffImage = cv.CloneMat(bwBaseImage)
    cv.AbsDiff(bwImage, bwBaseImage, diffImage)
    cv.Canny(diffImage, edges, 50, 100)
    cv.Dilate(edges, edges, iterations=3)
#    cv.Erode(edges, edges, iterations=3)
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
            sum = cv.Sum(bwDifftile)[0]
            brightest = 255
            _, brightest, _, _ = cv.MinMaxLoc(bwDifftile)
#            print "TileDiff: %s" % (value,)
            if sum > step_w * step_h * 5 or brightest > 60:
                
                print "Brightest: %s, Sum: %s (%s)" % (brightest, int(sum), step_w * step_h * 5)
                baseTile = cv.GetSubRect(baseImage, tileRect)
                cv.Copy(baseTile, retTile)
            else:
                newTile = cv.GetSubRect(newImage, tileRect)
                cv.Copy(newTile, retTile)
    return retImage
#    
#
#def initializeCapture(dims=(1280, 1024,)):
#    capture = cv2.VideoCapture(-1)
#    capture.set(cv2.cv.CV_CAP_PROP_FRAME_WIDTH, dims[0])
#    capture.set(cv2.cv.CV_CAP_PROP_FRAME_HEIGHT, dims[1])
#    w = capture.get(cv2.cv.CV_CAP_PROP_FRAME_WIDTH)
#    h = capture.get(cv2.cv.CV_CAP_PROP_FRAME_HEIGHT)
#    
#    print "Dimensions: %s" % ((w,h,),)
#    return capture, (w,h,) 
#    
#def captureImage(capture):
#    """Capture a new image from capture, then set it as the data
#    of gtkImage.
#    Returns cv Image of the capture"""
#    _, cvMat = capture.read()
#    return cvMat


if __name__ == "__main__":
    main()
