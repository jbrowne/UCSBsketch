#!/usr/bin/env python
from ImageShow import show
from SketchFramework.Point import Point
from SketchFramework.Stroke import Stroke
from Utils import ForegroundFilter as ff
from Utils.BoardChangeWatcher import BoardChangeWatcher
from Utils.ForegroundFilter import ForegroundFilter
from Utils.ForegroundFilter import max_allChannel
from cv2 import cv
from gtkStandalone import GTKGui
from sketchvision import ImageStrokeConverter as ISC
import gtk
import multiprocessing
import random
import threading
import time
MAXCAPSIZE = (2592, 1944)
HD1080 = (1920, 1080)
HD720 = (1280, 720)

#class CaptureProcess(threading.Thread):
class CaptureProcess(multiprocessing.Process):
    """This class watches a whiteboard, and bundles up
    changes of the board's contents as discreet "diff" events"""
    def __init__(self, capture, warpCorners, sketchGui):
#        threading.Thread.__init__(self)
        multiprocessing.Process.__init__(self)
        self.daemon = True
        self.capture = capture
        self.board = sketchGui
        self.boardWatcher = BoardChangeWatcher()
        self.warpCorners = warpCorners
        w = cv.GetCaptureProperty(self.capture, cv.CV_CAP_PROP_FRAME_WIDTH)
        h = cv.GetCaptureProperty(self.capture, cv.CV_CAP_PROP_FRAME_HEIGHT)
        dimensions = (w, h,)
        self.targetCorners = [ (0,0), (dimensions[0], 0), (dimensions[0], dimensions[1]), (0, dimensions[1])]
        
    def run(self):
        """Initialize the basic board model first, then continually
        update the image and add new ink to the board"""
        #Initialize stuff
#        import pydevd
#        pydevd.settrace(stdoutToServer=True, stderrToServer=True, suspend=False)
        rawImage = cv.GetMat(cv.QueryFrame(self.capture))
        ISC.saveimg(rawImage)
        warpImage = warpFrame(rawImage, self.warpCorners, self.targetCorners)
        ISC.saveimg(warpImage)
        self.boardWatcher.setBoardImage(warpImage)
        strokeList = ISC.cvimgToStrokes(warpImage)['strokes']
        for stk in strokeList:
            self.board.addStroke(stk)
        while True:
            time.sleep(0.25)
            rawImage = cv.GetMat(cv.QueryFrame(self.capture))
            warpImage = warpFrame(rawImage, self.warpCorners, self.targetCorners)
            self.boardWatcher.updateBoardImage(warpImage)
            if self.boardWatcher.isCaptureReady:
                ISC.saveimg(warpImage)
                ISC.saveimg(self.boardWatcher._fgFilter.getBackgroundImage())
                (newInk, newErase) = self.boardWatcher.captureBoardDifferences()
                cv.AddWeighted(newInk, -1, newInk, 0, 255, newInk)
                ISC.saveimg(newInk)
                ISC.saveimg(newErase)
                self.boardWatcher.setBoardImage(self.boardWatcher._fgFilter.getBackgroundImage()) # TODO: Build this into the class
                strokeList = ISC.cvimgToStrokes(newInk)['strokes']
                print "Adding %s strokes to board from image." % (len(strokeList))
                for stk in strokeList:
                    self.board.addStroke(stk)

def main():
    dScale = 0.4 #consistent display scaling
    warpCorners = [(800.0, 892.5), (2017.5, 370.0), (2232.5, 1822.5), (557.5, 1790.0)]
    boardCapture = BoardChangeWatcher()
    capture, dimensions = initializeCapture(dims = MAXCAPSIZE)
    windowCorners = [ (0,0), (dimensions[0], 0), (dimensions[0], dimensions[1]), (0, dimensions[1])]
    cv.NamedWindow("Calibrate")
    cv.SetMouseCallback("Calibrate", lambda e, x, y, f, p: onMouseDown(warpCorners, e, x/dScale, y/dScale, f, p))

    while len(warpCorners) != 4:
        image = captureImage(capture)
        showResized("Calibrate", image, dScale)
        key = cv.WaitKey(50)
        if key != -1:
            key = chr(key % 256)
        if key == 'q':
            print "Quitting"
            return
    cv.DestroyAllWindows()
    
    print "Calibrated: %s" % (warpCorners)

    sketchSurface = GTKGui(dims = (1600, 900))
    sketchWindow = gtk.Window()
    sketchWindow.add(sketchSurface)
    sketchWindow.connect("destroy", gtk.main_quit)
    sketchWindow.show_all()
    capProc = CaptureProcess(capture, warpCorners, sketchSurface)
    capProc.start()
    sketchSurface.registerKeyCallback('q', lambda: capProc.stop())
    sketchWindow.grab_focus()
    gtk.main()
    capProc.join()
    return
    
    while True:
        image = captureImage(capture)
        if len(warpCorners) == 4:
            image = warpFrame(image, warpCorners, windowCorners)
   
#        fgFilter.updateBackground(image)
        boardCapture.updateBoardImage(image)
        displayImage = boardCapture._fgFilter.getBackgroundImage()
        displayImage = resizeImage(displayImage, scale=dScale)
        cv.ShowImage("Output", displayImage)

#        prevBGImage = boardCapture._fgFilter.getBackgroundImage()
        (darkerDiff, lighterDiff) = boardCapture.captureBoardDifferences()
        if boardCapture.isCaptureReady:
            ISC.saveimg(boardCapture._lastCaptureImage)
            cv.AddWeighted(darkerDiff, -1, darkerDiff, 0.0, 255, darkerDiff)
            cv.AddWeighted(lighterDiff, -1, lighterDiff, 0.0, 255, lighterDiff)
            ISC.saveimg(darkerDiff)
            ISC.saveimg(lighterDiff)
            boardCapture.setBoardImage(boardCapture._fgFilter.getBackgroundImage())
#        #Track the new strokes that are added
#        captureDiff = cv.CloneMat(fgFilter.getBackgroundImage())
#        cv.AbsDiff(captureDiff, lastCaptureImage, captureDiff)
#        captureDiff = max_allChannel(captureDiff)
#        cv.Threshold(captureDiff, captureDiff, 50, 255, cv.CV_THRESH_BINARY)
#
#        
#        #Initiate a new capture when the changes settle
#        captureChanges = trackChanges(captureDiff, diffHistory)
#        if captureChanges < 0.02 and captureChanges > 0.001:
#            print "CAPTURE"
#            lastCaptureImage = cv.CloneMat(fgFilter.getBackgroundImage())
#            fgFilter.setBackground(lastCaptureImage)
#            diffHistory = []            
##        showResized("LastDiff", captureDiff, dScale)
        key = cv.WaitKey(50)
        if key != -1:
            key = chr(key % 256)
        if key == 'r':
            boardCapture.setBoardImage(image)
        if key == 'c':
            boardCapture.reset()
            boardCapture.setBoardImage(image)
        if key == 'q':
            print "Quitting"
            break
    cv.DestroyAllWindows()
    

def trackChanges(image, history):
    if len(history) > 5:
        history.pop(0)
    history.append(image)
    prev = None
    cumulativeDiff = None
    thisDiff = None
    for frame in history:
        if prev is None:
            prev = frame
            cumulativeDiff = cv.CreateMat(prev.rows, prev.cols, prev.type)
            cv.Set(cumulativeDiff, (0,0,0))
            thisDiff = cv.CreateMat(prev.rows, prev.cols, prev.type)
        else:
            cv.AbsDiff(prev, frame, thisDiff)
            cv.Max(thisDiff, cumulativeDiff, cumulativeDiff)
    cv.Smooth(cumulativeDiff, cumulativeDiff, smoothtype=cv.CV_MEDIAN)
    percentDiff = cv.CountNonZero(cumulativeDiff) / float(max(cv.CountNonZero(image), 1))
#    print "Percent Diff : %03f)" % (percentDiff)
#    showResized("HistoryDiff", cumulativeDiff, 0.4)
    return percentDiff
    
        
    
def showResized(name, image, scale):
    image = resizeImage(image, scale)
    cv.ShowImage(name, image)
    
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

if __name__ == "__main__":
    from Utils.CamArea import warpFrame
    main()
