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
from Utils.ImageUtils import captureImage
from Utils.ImageUtils import flipMat
from Utils.ImageUtils import initializeCapture
from Utils.ImageUtils import resizeImage
from Utils.ImageUtils import warpFrame
from Utils.ImageUtils import findCalibrationChessboard
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
import os
import random
import sys
import threading
import time
#4:3 Capture sizes
CAPSIZE00 = (2592, 1944)
CAPSIZE01 = (2048,1536)
CAPSIZE02 = (1600,1200)
CAPSIZE02 = (1280, 960)
CAPSIZE03 = (960, 720)
CAPSIZE04 = (800, 600)
PROJECTORSIZE = (1024, 768)

HD1080 = (1920, 1080)
HD720 = (1280, 720)
SCREENSIZE = (1600,900)

class BoardWatchProcess(multiprocessing.Process):
    """This class watches a whiteboard, and bundles up
    changes of the board's contents as discreet "diff" events"""
    def __init__(self, imageQueue, dimensions, warpCorners, sketchGui, targetCorners = None):
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
        print "BoardWatcher pid: %s" % (self.pid,)
        try:
            import pydevd
            pydevd.settrace(stdoutToServer=True, stderrToServer=True, suspend=False)
        except:
            pass
        rawImage = None
        while self.keepGoing.is_set() and rawImage is None:
            try:
                rawImage = deserializeImage(self.imageQueue.get(True, 1))
            except EmptyException:
                pass
        if not self.keepGoing.is_set():
            print "Board watcher stopping"
            return

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
            rawImage = deserializeImage(self.imageQueue.get(block=True))
            warpImage = warpFrame(rawImage, self.warpCorners, self.targetCorners)
            self.boardWatcher.updateBoardImage(warpImage)
            if self.boardWatcher.isCaptureReady:
                ISC.saveimg(warpImage)
                (newInk, newErase) = self.boardWatcher.captureBoardDifferences()
                ISC.saveimg(newInk)
                ISC.saveimg(newErase)
                cv.AddWeighted(newInk, -1, newInk, 0, 255, newInk)

                ISC.saveimg(self.boardWatcher.acceptCurrentImage())
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
        Process.__init__(self, name="Capture")
        self.imageQueue = imageQueue
        self.capture = capture
        self.keepGoing = Event()
        self.keepGoing.set()
        self.daemon = True

    def run(self):
        print "CaptureProcess pid: %s" % (self.pid,)
        while self.keepGoing.is_set():
            image = captureImage(self.capture)
#            sys.stdout.write(".")
            try:
                self.imageQueue.put(serializeImage(image), block=False)
            except FullException as e:
                try:
                    _ = self.imageQueue.get_nowait()
                except:
                    pass #Try to clear the queue, but don't worry if someone snatches it first
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
        self.keepGoing = True        
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
        key = chr(event.keyval % 256)
        if key == 'q':
            self.get_toplevel().destroy()
        elif key == 'c':
            warpCorners = findCalibrationChessboard(self.rawImage)
            #warpCorners = [(766.7376708984375, 656.48828125), (1059.5025634765625, 604.4216918945312), (1048.0185546875, 837.3212280273438), (733.5200805664062, 880.5441284179688)]
            if len(warpCorners) == 4:
                print "Warp Corners: %s" % (warpCorners)
                self.warpCorners = warpCorners
                self.get_toplevel().destroy()

                capProc = BoardWatchProcess(self.imageQueue, self.dimensions, 
                                            warpCorners, self.sketchSurface, 
                                            targetCorners=CalibrationArea.CHESSBOARDCORNERS)
                self.sketchSurface.registerKeyCallback('v', lambda: capProc.start())
                self.disable()

    def disable(self):
        self.keepGoing = False
        
    def enable(self):
        self.keepGoing = True
        gobject.idle_add(self.idleUpdate)        
        
    def idleUpdate(self):
        try:
            self.rawImage = deserializeImage(self.imageQueue.get_nowait())
            if len(self.warpCorners) == 4:
                dispImage = warpFrame(self.rawImage, self.warpCorners, CalibrationArea.CHESSBOARDCORNERS)
            else:
                dispImage = self.rawImage
            self.setCvMat(resizeImage(dispImage, self.dScale))
        except EmptyException as e:
            pass
        return self.keepGoing

    def destroy(self, *args, **kwargs):
        print "Destroy Called"
        self.captureProc.terminate()
        return ImageArea.destroy(self, *args, **kwargs)
        



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
    box = (points[2], points[1])

    fillWithChessBoard( box, 2, boxes)
    for tl, br in boxes:
        gui.drawBox(Point(*tl), Point(*br), 
                    color="#FFFFFF", fill="#FFFFFF", width = 0)
    gui.doPaint()



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

    
def serializeImage(image):
    """Returns a serialized version of an image to put in a Queue"""
    return (cv.GetSize(image), image.tostring())


def deserializeImage(serializedImage):
    """Turn a serialized image structure into a cvMat"""
    (imageSize, imageData) = serializedImage
    rawImage = cv.CreateMatHeader(imageSize[1], imageSize[0], cv.CV_8UC3)
    cv.SetData(rawImage, imageData, cv.CV_AUTOSTEP)
    return rawImage



def main(args):
    if len(args) > 1:
        camNum = int(args[1])
        print "Using cam %s" % (camNum,)
    else:
        camNum = 0
    capture, dims = initializeCapture(cam = camNum, dims=CAPSIZE01)    

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
    
if __name__ == "__main__":
    main(sys.argv)
