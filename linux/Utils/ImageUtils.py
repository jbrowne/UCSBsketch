from sketchvision.ImageStrokeConverter import saveimg
import cv
import numpy
import os
import threading
import time

######################################
# Image Manipulation
######################################
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

def initializeCapture(cam = 0, dims=(1280, 1024,), disableAutoExposure = True):
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
        os.system("v4l2-ctl -d %s --set-ctrl exposure_auto=3" % (cam,)) # Enable auto exposure
        def disableExposure():
            time.sleep(4)
            print "Disabling autoexposure"
            os.system("v4l2-ctl -d %s --set-ctrl exposure_auto=1" % (cam,)) # Disable auto exposure
        threading.Thread(target=disableExposure).start()
    return capture, (retw, reth,)


def captureImage(capture):
    """Capture a new image from capture, then set it as the data
    of gtkImage.
    Returns cv Image of the capture"""
    cvImg = cv.QueryFrame(capture)
    #cv.CvtColor(cvImg, cvImg, cv.CV_BGR2RGB)
    cvMat = cv.GetMat(cvImg)
    return cvMat

        
######################################
# Misc User Interaction Methods
######################################

def showResized(name, image, scale):
    """Combine resize and cv.ShowImage"""
    image = resizeImage(image, scale)
    cv.ShowImage(name, image)
    
    
def findCalibrationChessboard(image):
    """Search the image for a calibration chessboard pattern,
    and return four internal corners (tl, tr, br, bl) of the pattern""" 
    patternSize = (7, 7)  #Internal corners of 8x8 chessboard
    grayImage = cv.CreateMat(image.rows, image.cols, cv.CV_8UC1)
    cv.CvtColor(image, grayImage, cv.CV_RGB2GRAY)
    cv.AddWeighted(grayImage, -1, grayImage, 0, 255, grayImage) #Invert for checkerboard

    _, corners = cv.FindChessboardCorners(grayImage,
                                    patternSize,
                                    flags=cv.CV_CALIB_CB_ADAPTIVE_THRESH | 
                                           cv.CV_CALIB_CB_NORMALIZE_IMAGE)
    if len(corners) == 49:
        #Figure out the correct corner mapping
        points = sorted([corners[42], corners[0], corners[6], corners[48]], key = lambda pt: pt[0] + pt[1])
        if points[1][0] < points[2][0]:
            points[1], points[2] = points[2], points[1] #swap tr/bl as needed
        (tl, tr, bl, br) = points
        warpCorners = [tl, tr, br, bl]
    else:
        warpCorners = []
    saveimg(grayImage)
    debugImg = cv.CreateMat(image.rows, image.cols, image.type)
    cv.CvtColor(grayImage, debugImg, cv.CV_GRAY2RGB)
    for pt in warpCorners:
        pt = (int(pt[0]), int(pt[1]))
        cv.Circle(debugImg, pt, 4, (255,0,0))
    saveimg(debugImg)     
    return warpCorners