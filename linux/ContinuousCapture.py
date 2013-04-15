#!/usr/bin/env python
from ImageShow import show
from Queue import Full as FullException, Empty as EmptyException
from SketchFramework.Point import Point
from SketchFramework.Stroke import Stroke
from Utils import ForegroundFilter as ff
from Utils import Logger
from Utils.BoardChangeWatcher import BoardChangeWatcher
from Utils.ForegroundFilter import ForegroundFilter
from Utils.ForegroundFilter import max_allChannel
from Utils.ImageArea import ImageArea
from Utils.ImageUtils import captureImage
from Utils.ImageUtils import changeExposure
from Utils.ImageUtils import findCalibrationChessboard
from Utils.ImageUtils import flipMat
from Utils.ImageUtils import initializeCapture
from Utils.ImageUtils import resizeImage
from Utils.ImageUtils import saveimg
from Utils.ImageUtils import warpFrame
from cv2 import cv
from gtkStandalone import GTKGui
from gtkStandalone import GTKGui
from multiprocessing import Event
from multiprocessing import Process
from multiprocessing import Queue
from sketchvision import ImageStrokeConverter as ISC
from threading import Lock, Thread
import gobject
import gtk
import math
import multiprocessing
import numpy
import os
import random
import sys
import time
# 4:3 Capture sizes
CAPSIZE00 = (2592, 1944)
CAPSIZE01 = (2048, 1536)
CAPSIZE02 = (1600, 1200)
CAPSIZE02 = (1280, 960)
CAPSIZE03 = (960, 720)
CAPSIZE04 = (800, 600)
PROJECTORSIZE = (1024, 768)

HD1080 = (1920, 1080)
HD720 = (1280, 720)
SCREENSIZE = (1600, 900)
GTKGUISIZE = (1020, 650)

DEBUGBG_SCALE = 0.27
DEBUGDIFF_SCALE = 0.65
LIVECAP_SCALE = 0.45
BLOBFILTER_SCALE = 0.3

bwpLog = Logger.getLogger("BWP", Logger.WARN)
class BoardWatchProcess(multiprocessing.Process):
    """This class watches a whiteboard, and bundles up
    changes of the board's contents as discreet "diff" events"""
    def __init__(self, imageQueue, dimensions, warpCorners,
                 sketchGui, targetCorners=None):
        multiprocessing.Process.__init__(self)
        self.daemon = True
        self.imageQueue = imageQueue
        self.board = sketchGui
        self.boardWatcher = BoardChangeWatcher()
        self.boardWatcher.setBoardCorners(warpCorners, targetCorners)
        self.warpCorners = warpCorners
        self.keepGoing = Event()
        self.keepGoing.set()
        if targetCorners is None:
            self.targetCorners = [(0, 0),
                                  (dimensions[0], 0),
                                  (dimensions[0], dimensions[1]),
                                  (0, dimensions[1])]
        else:
            self.targetCorners = targetCorners
        bwpLog.debug("Board Watcher Calibrated")

    def run(self):
        """Initialize the basic board model first, then continually
        update the image and add new ink to the board"""
        global debugBgSurface, debugInkSurface, debugFilterSurface
        bwpLog.debug("Board Watcher Started: pid %s" % (self.pid,))
        try:
            import pydevd
            pydevd.settrace(stdoutToServer=True, stderrToServer=True,
                            suspend=False)
        except:
            pass
        rawImage = None
        while self.keepGoing.is_set() and rawImage is None:
            try:
                rawImage = deserializeImage(self.imageQueue.get(True, 1))
            except EmptyException:
                pass
        if not self.keepGoing.is_set():
            bwpLog.debug("Board watcher stopping")
            return

        saveimg(rawImage, name="Initial_Board_Image")
        self.boardWatcher.setBoardImage(rawImage)
        self.boardWatcher.setBoardCorners(self.warpCorners, self.targetCorners)
        boardWidth = self.board.getDimensions()[0]
        warpImage = warpFrame(rawImage, self.warpCorners, self.targetCorners)
        warpImage = resizeImage(warpImage, dims=GTKGUISIZE)
        # DEBUG
        bgImage = resizeImage(self.boardWatcher._fgFilter.getBackgroundImage(), scale=DEBUGBG_SCALE)
        debugBgSurface.setImage(bgImage)
        debugInkSurface.setImage(resizeImage(warpImage, scale=DEBUGDIFF_SCALE))
        # /DEBUG

        strokeList = ISC.cvimgToStrokes(flipMat(warpImage),
                                targetWidth=boardWidth)['strokes']

        for stk in strokeList:
            self.board.addStroke(stk)
        framesSinceAccept = 0
        while self.keepGoing.is_set():
            framesSinceAccept += 1
            try:
                rawImage = deserializeImage(self.imageQueue.get(block=True, timeout=1))
            except EmptyException:
                continue
            self.boardWatcher.updateBoardImage(rawImage)
            # DEBUG
            bgImage = self.boardWatcher._fgFilter.getBackgroundImage()
            debugBgSurface.setImage(resizeImage(bgImage, scale=DEBUGBG_SCALE))
            bgMask = self.boardWatcher._fgFilter.latestMask
            debugFilterSurface.setImage(resizeImage(bgMask, scale=DEBUGBG_SCALE))
            # /DEBUG
            if self.boardWatcher.isCaptureReady:
                saveimg(rawImage, name="Raw Image")
                saveimg(self.boardWatcher._fgFilter.getBackgroundImage(),
                        name="BG_Image")
                newInk, newErase = self.boardWatcher.captureBoardDifferences()
                newInk = warpFrame(newInk, self.warpCorners,
                                   self.targetCorners)
                newInk = resizeImage(newInk, dims=GTKGUISIZE)
                newErase = warpFrame(newErase, self.warpCorners,
                                     self.targetCorners)
                newErase = resizeImage(newErase, dims=GTKGUISIZE)
                #saveimg(newInk, name="NewInk")
                #saveimg(newErase, name="NewErase")

                acceptedImage = self.boardWatcher.acceptCurrentImage()
                saveimg(acceptedImage, name="AcceptedImage")
                framesSinceAccept = 0

                cv.AddWeighted(newInk, -1, newInk, 0, 255, newInk)
                strokeList = ISC.cvimgToStrokes(flipMat(newInk),
                                        targetWidth=boardWidth)['strokes']
                # DEBUG
                # Generate and display the context difference image
                warpBgImage = warpFrame(bgImage, self.warpCorners, self.targetCorners)
                warpBgImage = resizeImage(warpBgImage, dims=GTKGUISIZE)

                cv.Threshold(newInk, newInk, 255-20, 100, cv.CV_THRESH_BINARY_INV)
                cv.Threshold(newErase, newErase, 20, 128, cv.CV_THRESH_BINARY)
                debugDiffImage = cv.CloneMat(warpBgImage)
                redChannel = cv.CreateMat(warpBgImage.rows, warpBgImage.cols, cv.CV_8UC1)
                greenChannel = cv.CreateMat(warpBgImage.rows, warpBgImage.cols, cv.CV_8UC1)
                blueChannel = cv.CreateMat(warpBgImage.rows, warpBgImage.cols, cv.CV_8UC1)
                cv.Split(debugDiffImage, blueChannel, greenChannel, redChannel, None)
                cv.Add(newInk, blueChannel, blueChannel)
                cv.Add(newErase, redChannel, redChannel)

                cv.Sub(greenChannel, newInk, greenChannel)
                cv.Sub(redChannel, newInk, redChannel)

                cv.Sub(greenChannel, newErase, greenChannel)
                cv.Sub(blueChannel, newErase, blueChannel)

                cv.Merge(blueChannel, greenChannel, redChannel, None, debugDiffImage)

                debugInkSurface.setImage(resizeImage(debugDiffImage, scale=DEBUGDIFF_SCALE))
                # /DEBUG

                for stk in strokeList:
                    self.board.addStroke(stk)
        # DEBUG
        if framesSinceAccept == 9 :
                warpBgImage = warpFrame(bgImage, self.warpCorners, self.targetCorners)
                warpBgImage = resizeImage(warpBgImage, dims=GTKGUISIZE)
                debugInkSurface.setImage(resizeImage(warpBgImage, scale=DEBUGDIFF_SCALE))
        # /DEBUG

        bwpLog.debug("Board watcher stopping")

    def stop(self):
        self.keepGoing.clear()


capLog = Logger.getLogger("Capture", Logger.WARN)
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
        capLog.debug("CaptureProcess pid: {}".format(self.pid))
        while self.keepGoing.is_set():
            image = captureImage(self.capture)
#            sys.stdout.write(".")
            try:
                self.imageQueue.put(serializeImage(image),
                                    block=True, timeout=0.25)
            except FullException:
                try:
                    _ = self.imageQueue.get_nowait()
                except:
                    pass  # Try to clear the queue, but don't worry if someone snatches it first

    def stop(self):
        self.keepGoing.clear()


class CalibrationArea(ImageArea):
    CHESSBOARDCORNERS = None
    RAWBOARDCORNERS = None

    def __init__(self, capture, dimensions, sketchSurface):
        """Constructor: capture is initialized, with dimensions (w, h), and 
        sketchSurface is ready to have strokes added to it"""
        dims = dimensions
        CalibrationArea.CHESSBOARDCORNERS = [(5 * dims[0] / 16.0, 5 * dims[1] / 16.0),
                         (11 * dims[0] / 16.0, 5 * dims[1] / 16.0),
                         (11 * dims[0] / 16.0, 11 * dims[1] / 16.0),
                         (5 * dims[0] / 16.0, 11 * dims[1] / 16.0), ]
        CalibrationArea.RAWBOARDCORNERS = [(0, 0),
                                           (dims[0], 0),
                                           (dims[0], dims[1]),
                                           (0, dims[1])]

        ImageArea.__init__(self)
        self.lock = Lock()
        # Associate the video capture and the sketching surface

        self.dimensions = dimensions
        self.rawImage = cv.CreateMatHeader(self.dimensions[1],
                                           self.dimensions[0], cv.CV_8UC3)
        self.sketchSurface = sketchSurface

        # Capture logic
        self.capture = capture
        self.imageQueue = Queue(1)
        self.captureProc = CaptureProcess(self.capture, self.imageQueue)
        self.captureProc.start()

        # GUI configuration stuff
        self.registeredCallbacks = {}
        self.keepGoing = True
        self.dScale = LIVECAP_SCALE
        self.warpCorners = []
        gobject.idle_add(self.idleUpdate)
        self.set_property("can-focus", True)  # So we can capture keyboard
        self.connect("key_press_event", self.onKeyPress)
        self.connect("button_release_event", self.onMouseUp)
        self.set_events(gtk.gdk.BUTTON_RELEASE_MASK
                       | gtk.gdk.BUTTON_PRESS_MASK
                       | gtk.gdk.KEY_PRESS_MASK
                       | gtk.gdk.VISIBILITY_NOTIFY_MASK
                       | gtk.gdk.POINTER_MOTION_MASK
                       )

    def registerKeyCallback(self, key, callback):
        """Register a callback that takes key as an argument for a key"""
        self.registeredCallbacks.setdefault(key, []).append(callback)

    def onKeyPress(self, widget, event, data=None):
        """Respond to a key being pressed"""
        key = chr(event.keyval % 256)
        if key == 'q':
            self.get_toplevel().destroy()
        elif key == 'c':
            if len(self.warpCorners) == 4:
                print "Using pre-defined calibration"
                capProc = BoardWatchProcess(self.imageQueue, self.dimensions,
                                self.warpCorners, self.sketchSurface,
                                targetCorners=CalibrationArea.RAWBOARDCORNERS)
                self.sketchSurface.registerKeyCallback('v',
                                                       lambda: capProc.start())
#                self.disable()
#                self.get_toplevel().destroy()
            else:
                print "Searching for Chessboard..."
                warpCorners = findCalibrationChessboard(self.rawImage)
                if len(warpCorners) == 4:
                    print "Warp Corners: %s" % (warpCorners)
                    self.warpCorners = warpCorners
                    capProc = BoardWatchProcess(self.imageQueue,
                                self.dimensions,
                                warpCorners, self.sketchSurface,
                                targetCorners=CalibrationArea.CHESSBOARDCORNERS)
                    self.sketchSurface.registerKeyCallback('v',
                                                lambda: capProc.start())
#                    self.disable()
#                    self.get_toplevel().destroy()
                else:
                    print "No chessboard found!"
        for callback in self.registeredCallbacks.get(key, []):
            callback(key)


    def onMouseUp(self, widget, e):
        """Respond to the mouse being released"""
        if len(self.warpCorners) >= 4:
            self.warpCorners = []
        else:
            (x, y) = (e.x / self.dScale, e.y / self.dScale)
            self.warpCorners.append((x, y))

    def disable(self):
        self.keepGoing = False

    def enable(self):
        self.keepGoing = True
        gobject.idle_add(self.idleUpdate)

    def idleUpdate(self):
        try:
            serializedImage = self.imageQueue.get_nowait()
            self.rawImage = deserializeImage(serializedImage)
            dispImage = self.rawImage
            """
            for x, y in self.warpCorners:
                cv.Circle(dispImage, (int(x), int(y)), 5,
                          (200, 0, 200), thickness= -1)
            """
            smallImage = resizeImage(dispImage, self.dScale)
            self.setCvMat(smallImage)
        except EmptyException:
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
    midPt = ((tl[0] + br[0]) / 2.0, (tl[1] + br[1]) / 2.0)
    midLeft = (tl[0], midPt[1])
    midRight = (br[0], midPt[1])
    midTop = (midPt[0], tl[1])
    midBot = (midPt[0], br[1])
    topLeftBox = (tl, midPt)
    topRightBox = (midTop, midRight)
    botRightBox = (midPt, br)
    botLeftBox = (midLeft, midBot)
    if thisLvl == 0:
        ptList.append(topLeftBox)
        ptList.append(botRightBox)
    else:
        fillWithChessBoard(topLeftBox, thisLvl - 1, ptList)
        fillWithChessBoard(topRightBox, thisLvl - 1, ptList)
        fillWithChessBoard(botLeftBox, thisLvl - 1, ptList)
        fillWithChessBoard(botRightBox, thisLvl - 1, ptList)


def displayCalibrationPattern(gui):
    """Display a series of circles at the points listed, or at 1/4 of the way
    in from each corner, if no points are provided"""
    w, h = gui.getDimensions()
    deltaX = w / 4.0
    deltaY = h / 4.0
    points = []
    points.append((deltaX, deltaY,))  # SW
    points.append((w - deltaX, deltaY,))  # SE
    points.append((deltaX, h - deltaY,))  # NW
    points.append((w - deltaX, h - deltaY,))  # NE

    boxes = []
    box = (points[2], points[1])

    fillWithChessBoard(box, 2, boxes)
    for tl, br in boxes:
        gui.drawBox(Point(*tl), Point(*br),
                    color="#FFFFFF", fill="#FFFFFF", width=0)
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
            cv.Set(cumulativeDiff, (0, 0, 0))
            thisDiff = cv.CreateMat(prev.rows, prev.cols, prev.type)
        else:
            cv.AbsDiff(prev, frame, thisDiff)
            cv.Max(thisDiff, cumulativeDiff, cumulativeDiff)
    cv.Smooth(cumulativeDiff, cumulativeDiff, smoothtype=cv.CV_MEDIAN)
    percentDiff = (cv.CountNonZero(cumulativeDiff)
                   / float(max(cv.CountNonZero(image), 1)))
#    print "Percent Diff : %03f)" % (percentDiff)
#    showResized("HistoryDiff", cumulativeDiff, 0.4)
    return percentDiff


def serializeImage(image):
    """Returns a serialized version of an image to put in a Queue"""
    return (cv.GetSize(image), image.type, image.tostring())


def deserializeImage(serializedImage):
    """Turn a serialized image structure into a cvMat"""
    (imageSize, imageType, imageData) = serializedImage
    rawImage = cv.CreateMatHeader(imageSize[1], imageSize[0], imageType)
    cv.SetData(rawImage, imageData, cv.CV_AUTOSTEP)
    return rawImage


class DebugWindow(ImageArea):
    def __init__(self):
        ImageArea.__init__(self)
        self.imageQueue = Queue(1)
        gobject.timeout_add(200, self._updateImage)
        self._lock = Lock()
        self._thread = None

    def setImage(self, image):
        try:
            if self.imageQueue.empty():
                self.imageQueue.put(serializeImage(image))
        except FullException:
            pass
        except Exception as e:
            print "Cannot display image: {}".format(e)

    def _updateImage(self):
        def getAndSetImage(surface, queue):
            try:
                img = deserializeImage(queue.get(True, 3))
                with surface._lock:
                    surface.setCvMat(img)
                time.sleep(0.3)
            except EmptyException as e:
                pass
            except Exception as e:
                print "Error getting image! {}".format(e)

        with self._lock:
            if self._thread is None or not self._thread.is_alive():
                self._thread = Thread(target=getAndSetImage,
                                                args=(self, self.imageQueue))
                self._thread.daemon = True
                self._thread.start()
        return True


def main(args):
    global debugBgSurface, debugInkSurface, debugFilterSurface
    if len(args) > 1:
        camNum = int(args[1])
        print "Using cam %s" % (camNum,)
    else:
        camNum = 0
    capture, dims = initializeCapture(cam=camNum, dims=CAPSIZE01)
    changeExposure(camNum, value=300)

    sketchSurface = GTKGui(dims=GTKGUISIZE)
    sketchWindow = gtk.Window(type=gtk.WINDOW_TOPLEVEL)
    sketchWindow.set_title("Sketch Surface")
    sketchWindow.add(sketchSurface)
    sketchWindow.connect("destroy", gtk.main_quit)
    sketchWindow.show_all()
    sketchWindow.move(1600, 90)
    sketchSurface.registerKeyCallback('C',
                        lambda: displayCalibrationPattern(sketchSurface))

    calibArea = CalibrationArea(capture, dims, sketchSurface)
    calibArea.registerKeyCallback('+', lambda _: changeExposure(camNum, 100))
    calibArea.registerKeyCallback('-', lambda _: changeExposure(camNum, -100))
    calibWindow = gtk.Window(type=gtk.WINDOW_TOPLEVEL)
    calibWindow.set_title("Live View")
    calibWindow.add(calibArea)
    calibWindow.connect("destroy", lambda _: calibWindow.destroy())
    calibWindow.show_all()
    calibWindow.move(670,0)

    debugFilterSurface = DebugWindow()
    debugFilterSurface.setImage(
        resizeImage(cv.CreateMat(dims[1], dims[0], cv.CV_8UC1), scale=DEBUGBG_SCALE))
    debugFilterWindow = gtk.Window(type=gtk.WINDOW_TOPLEVEL)
    debugFilterWindow.set_title("Foreground Filter")
    debugFilterWindow.add(debugFilterSurface)
    debugFilterWindow.connect("destroy", gtk.main_quit)
    debugFilterWindow.show_all()
    debugFilterWindow.move(0,0)
    #debugFilterWindow.move(1600,90)

    debugBgSurface = DebugWindow()
    debugBgSurface.setImage(
        resizeImage(cv.CreateMat(dims[1], dims[0], cv.CV_8UC1), scale=DEBUGBG_SCALE))
    debugBgWindow = gtk.Window(type=gtk.WINDOW_TOPLEVEL)
    debugBgWindow.set_title("Filtered Board View")
    debugBgWindow.add(debugBgSurface)
    debugBgWindow.connect("destroy", gtk.main_quit)
    #debugBgWindow.show_all()

    debugInkSurface = DebugWindow()
    guiDims = sketchSurface.getDimensions()
    dummyInkImage = cv.CreateMat(guiDims[1], guiDims[0], cv.CV_8UC1)
    cv.Set(dummyInkImage, 128)
    debugInkSurface.setImage(resizeImage(dummyInkImage, scale=DEBUGDIFF_SCALE))
    debugInkWindow = gtk.Window(type=gtk.WINDOW_TOPLEVEL)
    debugInkWindow.set_title("Transformed Board View")
    debugInkWindow.add(debugInkSurface)
    debugInkWindow.connect("destroy", gtk.main_quit)
    debugInkWindow.show_all()
    debugInkWindow.move(0, 460)

    sketchSurface.grab_focus()
    gtk.main()
    print "gtkMain exits"

if __name__ == "__main__":
    main(sys.argv)
