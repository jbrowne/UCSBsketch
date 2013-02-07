#!/usr/bin/env python
from ImageShow import show
from Queue import Full as FullException, Empty as EmptyException
from SketchFramework.Point import Point
from SketchFramework.Stroke import Stroke
from Utils import ForegroundFilter as ff
from Utils.BoardChangeWatcher import BoardChangeWatcher
from Utils.ForegroundFilter import ForegroundFilter
from Utils.ForegroundFilter import max_allChannel
from Utils.ImageArea import ImageArea
from cv2 import cv
from gtkStandalone import GTKGui
from multiprocessing import Event
from multiprocessing import Process
from multiprocessing import Queue
from sketchvision import ImageStrokeConverter as ISC
from threading import Lock
import gobject
import gtk
import math
import multiprocessing
import numpy
import random
import threading
import time
MAXCAPSIZE = (2592, 1944)
HD1080 = (1920, 1080)
HD720 = (1280, 720)
PROJECTORSIZE = (1024, 768)
SCREENSIZE = (1600,900)

#class BoardWatchProcess(threading.Thread):
class BoardWatchProcess(multiprocessing.Process):
    """This class watches a whiteboard, and bundles up
    changes of the board's contents as discreet "diff" events"""
    def __init__(self, imageQueue, dimensions, warpCorners, sketchGui, targetCorners = None):
#        threading.Thread.__init__(self)
        multiprocessing.Process.__init__(self)
        self.daemon = True
        self.imageQueue = imageQueue
        self.board = sketchGui
        self.boardWatcher = BoardChangeWatcher()
        self.warpCorners = warpCorners
        self.keepGoing = Event()
        self.keepGoing.set()
        if targetCorners is None:
            self.targetCorners = [ (0,0), (dimensions[0], 0), (dimensions[0], dimensions[1]), (0, dimensions[1])]
        else:
            self.targetCorners = targetCorners
        
    def run(self):
        """Initialize the basic board model first, then continually
        update the image and add new ink to the board"""
        #Initialize stuff
        try:
            import pydevd
            pydevd.settrace(stdoutToServer=True, stderrToServer=True, suspend=False)
        except:
            pass
        while self.keepGoing.is_set():
            try:
                imageSize, imageData = self.imageQueue.get(True, 2)
            except EmptyException:
                pass
        rawImage = cv.CreateMatHeader(imageSize[1], imageSize[0], cv.CV_8UC3)
        cv.SetData(rawImage, imageData, cv.CV_AUTOSTEP)
        ISC.saveimg(rawImage)
        warpImage = warpFrame(rawImage, self.warpCorners, self.targetCorners)
        ISC.saveimg(warpImage)
        self.boardWatcher.setBoardImage(warpImage)

        ISC.DEBUG = True
        boardWidth = self.board.getDimensions()[0]
        strokeList = ISC.cvimgToStrokes(flipMat(warpImage), targetWidth = boardWidth)['strokes']
        ISC.DEBUG = False

        for stk in strokeList:
            self.board.addStroke(stk)
        while self.keepGoing.is_set():
#            time.sleep(0.25)
            imageSize, imageData = self.imageQueue.get()
            rawImage = cv.CreateMatHeader(imageSize[1], imageSize[0], cv.CV_8UC3)
            cv.SetData(rawImage, imageData, cv.CV_AUTOSTEP)
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
                strokeList = ISC.cvimgToStrokes(flipMat(newInk), targetWidth = boardWidth)['strokes']
                for stk in strokeList:
                    self.board.addStroke(stk)
        print "Board watcher stopping"
                    
    def stop(self):
        self.keepGoing.clear()

class CaptureProcess(Process):
    """A process that fills a queue with images as captured from 
    a camera feed"""
    def __init__(self, capture, imageQueue):
        Process.__init__(self)
        self.imageQueue = imageQueue
        self.capture = capture
        self.keepGoing = Event()
        self.keepGoing.set()
        self.daemon = True
        print "CaptureProcess: %s" % (self.capture,)

    def run(self):
        while self.keepGoing.is_set():
            image = captureImage(self.capture)
            try:
                self.imageQueue.put((cv.GetSize(image), image.tostring()), block=True, timeout=0.5)
            except FullException as e:
#                print "Cannot add this image, queue is full"
                pass
    def stop(self):
        self.keepGoing.clear()
            
        
class CalibrationArea(ImageArea):
    CHESSBOARDCORNERS = None 
    def __init__(self, capture, dimensions, sketchSurface):
        """Constructor: capture is initialized, with dimensions (w, h), and 
        sketchSurface is ready to have strokes added to it"""
        dims = dimensions
        CalibrationArea.CHESSBOARDCORNERS = [(5*dims[0]/16.0, 5*dims[1]/16.0),
                         (11*dims[0]/16.0, 5*dims[1]/16.0),
                         (11*dims[0]/16.0, 11*dims[1]/16.0),
                         (5*dims[0]/16.0, 11*dims[1]/16.0),]    
        
        ImageArea.__init__(self)
        self.lock = Lock()
        #Associate the video capture and the sketching surface

        self.dimensions = dimensions
        self.rawImage = cv.CreateMatHeader(self.dimensions[1], self.dimensions[0], cv.CV_8UC3)
        self.sketchSurface = sketchSurface
        
        #Capture logic
        self.capture = capture
        self.imageQueue = Queue(1)
        self.captureProc = CaptureProcess(self.capture, self.imageQueue)
        self.captureProc.start()
        
        #GUI configuration stuff
        self.dScale = 0.4
        self.warpCorners = []
        gobject.idle_add(self.idleUpdate)
        self.set_property("can-focus", True)  #So we can capture keyboard events
        self.connect("key_press_event", self.onKeyPress)
        self.set_events(gtk.gdk.BUTTON_RELEASE_MASK
                       | gtk.gdk.BUTTON_PRESS_MASK
                       | gtk.gdk.KEY_PRESS_MASK
                       | gtk.gdk.VISIBILITY_NOTIFY_MASK
                       | gtk.gdk.POINTER_MOTION_MASK 
                       )
        
    def onKeyPress(self, widget, event, data=None):
        """Respond to a key being pressed"""
        dims = self.dimensions

        key = chr(event.keyval % 256)
        if key == 'q':
            self.get_toplevel().destroy()
        elif key == 'c':
            warpCorners = findCalibrationChessboard(self.rawImage)
            if len(warpCorners) == 4:
                self.warpCorners = warpCorners
#                self.get_toplevel().destroy()

                capProc = BoardWatchProcess(self.imageQueue, self.dimensions, 
                                            warpCorners, self.sketchSurface, 
                                            targetCorners=CalibrationArea.CHESSBOARDCORNERS)
                self.sketchSurface.registerKeyCallback('v', lambda: capProc.start())
                self.sketchSurface.registerKeyCallback('r', lambda: capProc.stop())
                

    def idleUpdate(self):
        try:
            imageSize, imageData = self.imageQueue.get_nowait()
            self.rawImage = cv.CreateMatHeader(imageSize[1], imageSize[0], cv.CV_8UC3)
            cv.SetData(self.rawImage, imageData, cv.CV_AUTOSTEP)
            if len(self.warpCorners) == 4:
                dispImage = warpFrame(self.rawImage, self.warpCorners, CalibrationArea.CHESSBOARDCORNERS)
            else:
                dispImage = self.rawImage
            self.setCvMat(resizeImage(dispImage, self.dScale))
        except EmptyException as e:
            pass
        return True

    def destroy(self, *args, **kwargs):
        print "Destroy Called"
        self.captureProc.terminate()
        return ImageArea.destroy(self, *args, **kwargs)
        

def main():
    capture, dims = initializeCapture(dims = MAXCAPSIZE)

    sketchSurface = GTKGui(dims = PROJECTORSIZE)
    sketchWindow = gtk.Window(type=gtk.WINDOW_TOPLEVEL)
    sketchWindow.add(sketchSurface)
    sketchWindow.connect("destroy", gtk.main_quit)
    sketchWindow.show_all()
    sketchSurface.registerKeyCallback('C', lambda: displayCalibrationPattern(sketchSurface))
    
    calibArea = CalibrationArea(capture, dims, sketchSurface)
    calibWindow = gtk.Window(type=gtk.WINDOW_TOPLEVEL)
    calibWindow.add(calibArea)
    calibWindow.connect("destroy", lambda x: calibWindow.destroy())
    calibWindow.show_all()

    sketchSurface.grab_focus()
    gtk.main()
    print "gtkMain exits"

def fillWithChessBoard(box, thisLvl, ptList):
    """A Recursive helper to display a chessboard pattern
    within a box (tl, br)"""
    tl, br = box
    midPt = ( (tl[0] + br[0]) / 2.0,  (tl[1] + br[1]) / 2.0 )
    midLeft = ( tl[0],  midPt[1] )
    midRight = ( br[0], midPt[1] )
    midTop = ( midPt[0], tl[1] )
    midBot = ( midPt[0], br[1] )
    topLeftBox = (tl, midPt)
    topRightBox = (midTop, midRight)
    botRightBox = (midPt, br)
    botLeftBox = (midLeft, midBot )
    if thisLvl == 0:
        ptList.append(topLeftBox)
        ptList.append(botRightBox)
    else:
        fillWithChessBoard( topLeftBox , thisLvl - 1, ptList)
        fillWithChessBoard( topRightBox, thisLvl - 1, ptList)
        fillWithChessBoard( botLeftBox, thisLvl - 1, ptList)
        fillWithChessBoard( botRightBox, thisLvl - 1, ptList)
    
 
def displayCalibrationPattern(gui):
    """Display a series of circles at the points listed, or at 1/4 of the way
    in from each corner, if no points are provided"""
    w,h = gui.getDimensions()
    deltaX = w / 4.0
    deltaY = h / 4.0
    points = []
    points.append((deltaX, deltaY,)) #SW
    points.append((w - deltaX, deltaY,)) #SE
    points.append((deltaX, h - deltaY,)) #NW
    points.append((w - deltaX, h - deltaY,)) #NE

    boxes = []
    scale = min(w,h) / 4.0
#    box = ((scale, scale), (3 * scale, 3 * scale))
    box = (points[2], points[1])

    fillWithChessBoard( box, 2, boxes)
    for tl, br in boxes:
        gui.drawBox(Point(*tl), Point(*br), 
                    color="#FFFFFF", fill="#FFFFFF", width = 0)
    gui.doPaint()

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

    ISC.saveimg(grayImage)
    debugImg = cv.CreateMat(image.rows, image.cols, image.type)
    cv.CvtColor(grayImage, debugImg, cv.CV_GRAY2RGB)
    for pt in warpCorners:
        pt = (int(pt[0]), int(pt[1]))
        cv.Circle(debugImg, pt, 4, (255,0,0))
    ISC.saveimg(debugImg)     
           
    return warpCorners

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
    capture = cv.CaptureFromCAM(0)
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
    cvMat = cv.CloneMat(cv.GetMat(cvImg))
    return cvMat

def flipMat(image):
    """Flip an image vertically (top -> bottom)"""
    retImage = cv.CreateMat(image.rows, image.cols, image.type)
    height = image.rows
    transMatrix = cv.CreateMatHeader(2, 3, cv.CV_32FC1)
    narr = numpy.array([[1,0,0],[0,-1,height]], numpy.float32)
    cv.SetData(transMatrix, narr, cv.CV_AUTOSTEP)
    cv.WarpAffine(image, retImage, transMatrix)
    return retImage
    
    
def printMat(image):
    for row in range(image.rows):
        print "[", 
        for col in range(image.cols):
            print cv.mGet(image, row, col), 
        print "]"
    print ""
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
