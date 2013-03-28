from sketchvision.ImageStrokeConverter import saveimg
from multiprocessing.queues import Queue
import multiprocessing
import commands
import cv
import numpy
import os
import threading
import time

######################################
# Image Manipulation
######################################
def getFillPoints(image):
    """Generate points from which iterative flood fill would cover all non-zero pixels
    in image."""
    image = cv.CloneMat(image)
    retList = []
    _, maxVal, _ , maxLoc = cv.MinMaxLoc(image)
    while maxVal > 0:
        retList.append(maxLoc)
        cv.FloodFill(image, maxLoc, 0)
        _, maxVal, _, maxLoc = cv.MinMaxLoc(image)
    return retList
        

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


def warpFrame(frame, corners, targetCorners):
    """Transforms the frame such that the four corners (nw, ne, se, sw)
    match the targetCorners
    """
    outImg = cv.CreateMat(frame.rows, frame.cols, frame.type)
    if len(corners) == 4:
        #w,h = outImg.cols, outImg.rows #frame.cols, frame.rows
        warpMat = cv.CreateMat(3, 3, cv.CV_32FC1)  #Perspective warp matrix
        cv.GetPerspectiveTransform(corners,
            targetCorners,
            warpMat)
        #outImg = cv.CloneMat(frame)
        cv.WarpPerspective(frame, outImg, warpMat,
            (cv.CV_INTER_CUBIC | cv.CV_WARP_FILL_OUTLIERS), 255)
        return outImg
    else:
        return frame


def flipMat(image):
    """Flip an image vertically (top -> bottom)"""
    retImage = cv.CreateMat(image.rows, image.cols, image.type)
    height = image.rows
    transMatrix = cv.CreateMatHeader(2, 3, cv.CV_32FC1)
    narr = numpy.array([[1,0,0],[0,-1,height]], numpy.float32)
    cv.SetData(transMatrix, narr, cv.CV_AUTOSTEP)
    cv.WarpAffine(image, retImage, transMatrix)
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

    
def printMat(image):
    """Print out a text representation of an image"""
    for row in range(image.rows):
        print "[", 
        for col in range(image.cols):
            print cv.mGet(image, row, col), 
        print "]"
    print ""
        
        
######################################
# Video Capture Utils
######################################

def initializeCapture(cam = 0, dims=(1280, 1024,), disableAutoExposure = True, disableAutoFocus = True):
    """Try to initialize the capture to the requested dimensions,
    and disable auto-exposure. 
    Returns the capture and the actual dimensions"""
    capture = cv.CaptureFromCAM(cam)
    w, h = dims
    cv.SetCaptureProperty(capture, cv.CV_CAP_PROP_FRAME_HEIGHT, h) 
    cv.SetCaptureProperty(capture, cv.CV_CAP_PROP_FRAME_WIDTH, w)
    reth = int(cv.GetCaptureProperty(capture, cv.CV_CAP_PROP_FRAME_HEIGHT))
    retw = int(cv.GetCaptureProperty(capture, cv.CV_CAP_PROP_FRAME_WIDTH))
    if disableAutoExposure:
        setAutoExposure(cam, False)
    else:
        setAutoExposure(cam, True)
    if disableAutoFocus:
        setAutoFocus(cam, False)
    else:
        setAutoFocus(cam, True)
    return capture, (retw, reth,)

def setAutoExposure(cam, shouldAuto):
    if shouldAuto:
        value = 3
    else:
        value = 1
    os.system("v4l2-ctl -d {} --set-ctrl exposure_auto={}".format(cam,value))

def setAutoFocus(cam, shouldAuto):
    os.system("v4l2-ctl -d {} --set-ctrl focus_auto={}".format(cam,int(shouldAuto)))

def changeExposure(cam=0, increment=0):
    """Increase/Decrease the exposure of cam"""
    try:
        exposure = commands.getoutput("v4l2-ctl -d {} --get-ctrl exposure_absolute".format(cam)).split()[1]
        exposure = int(exposure)
        exposure = max(0, exposure+increment)
        commands.getoutput("v4l2-ctl -d {} --set-ctrl exposure_absolute={}".format(cam, exposure))
        print "Exposure {}".format(exposure)
    except Exception as e:
        print "Failed to change exposure: {}".format(e)


def captureImage(capture):
    """Capture a new image from capture, then set it as the data
    of gtkImage.
    Returns cv Image of the capture"""
    cvImg = cv.QueryFrame(capture)
    #cv.CvtColor(cvImg, cvImg, cv.CV_BGR2RGB)
    cvMat = cv.GetMat(cvImg)
    return cv.CloneMat(cvMat)

        
######################################
# Misc User Interaction Methods
######################################

def showResized(name, image, scale):
    """Combine resize and cv.ShowImage"""
    image = resizeImage(image, scale)
    cv.ShowImage(name, image)
    
    
def findCalibrationChessboard(image):
    patternSize = (7, 7)  #Internal corners of 8x8 chessboard
    grayImg = cv.CreateMat(image.rows, image.cols, cv.CV_8UC1)
    cv.CvtColor(image, grayImg, cv.CV_RGB2GRAY)
    cv.AddWeighted(grayImg, -1, grayImg, 0, 255, grayImg)
    saveimg(grayImg)
    cornerListQueue = Queue()
    
    def getCorners(idx, inImg, cornersQueue):
        """Search for corners in image and put them in the queue"""
        print "{} Searching".format(idx)
        _, corners = cv.FindChessboardCorners(inImg,
                                        patternSize,
                                        flags=cv.CV_CALIB_CB_ADAPTIVE_THRESH | 
                                               cv.CV_CALIB_CB_NORMALIZE_IMAGE)
        print "{} found {} corners".format(idx, len(corners))
        if len(corners) == 49:            
            cornersQueue.put(corners)

    for i in range(10):
        img = cv.CloneMat(grayImg)
        cv.Erode(img, img, iterations=i)
        cv.Dilate(img, img, iterations=i)
        saveimg(img, name=str(i))
        
        p = multiprocessing.Process(target=lambda: getCorners(i, img,cornerListQueue))
        p.daemon = True
        p.start()
    try:
        corners = cornerListQueue.get(True, timeout=5)
        #Debug Image
        debugImg = cv.CreateMat(grayImg.rows, grayImg.cols, cv.CV_8UC3)
        cv.CvtColor(grayImg, debugImg, cv.CV_GRAY2RGB)
        for pt in corners:
            pt = (int(pt[0]), int(pt[1]))
            cv.Circle(debugImg, pt, 4, (255,0,0))
        saveimg(debugImg)                        
        #//Debug Image
        #Figure out the correct corner mapping
        points = sorted([corners[42], corners[0], corners[6], corners[48]], key = lambda pt: pt[0] + pt[1])
        if points[1][0] < points[2][0]:
            points[1], points[2] = points[2], points[1] #swap tr/bl as needed
        (tl, tr, bl, br) = points
        warpCorners = [tl, tr, br, bl]
    except Exception as e:
        print "Could not find corners: {}".format(e)
        warpCorners = []

    return warpCorners
