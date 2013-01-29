#!/usr/bin/env python
from Utils import ForegroundFilter as ff
from cv2 import cv
from sketchvision import ImageStrokeConverter as ISC
MAXCAPSIZE = (2592, 1944)
HD1080 = (1920, 1080)
HD720 = (1280, 720)


        

def main():
    warpCorners = [(337, 219), (929, 27), (957, 688), (240, 667)]
    fgFilter = ff.ForegroundFilter()
    capture, dimensions = initializeCapture(dims = HD720)
    windowCorners = [ (0,0), (dimensions[0], 0), (dimensions[0], dimensions[1]), (0, dimensions[1])]
    baseImage = cv.CloneMat(captureImage(capture))
    fgFilter.setBackground(baseImage)
    cv.NamedWindow("Output")
    cv.SetMouseCallback("Output", lambda e, x, y, f, p: onMouseDown(warpCorners, e, x, y, f, p))
    i = 0
    while True:
        image = captureImage(capture)
        if len(warpCorners) == 4:
            image = warpFrame(image, warpCorners, windowCorners)
   
        fgFilter.updateBackground(image)
#        displayImage = fgFilter.filterForeground(image)
        displayImage = fgFilter.getBackgroundImage()

        cv.ShowImage("Output", displayImage)

        key = cv.WaitKey(50)
        if key != -1:
            key = chr(key % 256)
        if key == 'r':
            fgFilter.setBackground(image)
        if key == 'q':
            print "Quitting"
            break
        i+=1
        
    cv.DestroyAllWindows()
    
def onMouseDown(warpCorners, event, x, y, flags, param):
    if event == cv.CV_EVENT_LBUTTONDOWN:
        if len(warpCorners) == 4:
            warpCorners.pop()
            warpCorners.pop()
            warpCorners.pop()
            warpCorners.pop()
        else:        
            warpCorners.append( (x,y) )
            if len(warpCorners) == 4:
                print "Corners: %s" % (warpCorners)

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


if __name__ == "__main__":
    from Utils.CamArea import warpFrame
    main()
