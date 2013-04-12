#!/usr/bin/env python
import sys
if __name__ == "__main__":
    sys.path.append("./")
    print sys.path
from ContinuousCapture import BoardChangeWatcher
from Utils import Logger
from Utils.ImageArea import ImageArea
from Utils.ImageUtils import captureImage
from Utils.ImageUtils import initializeCapture
from Utils.ImageUtils import resizeImage
from Utils.ImageUtils import warpFrame
from Utils.ImageUtils import findCalibrationChessboard

from multiprocessing.queues import Queue
from sketchvision import ImageStrokeConverter as ISC
import cv
import gobject
import gtk
import multiprocessing
import pdb
import pygtk
import threading


pygtk.require('2.0')

log = Logger.getLogger("CamArea", Logger.WARN)
    
MAXCAPSIZE = (2592, 1944)
HD1080 = (1920, 1080)
HD720 = (1280, 720)
DEFAULT_CORNERS = [
                    (777.6, 239.76000000000002),
                    (2080, 533),
                    (2235.6, 1506.6000000000001),
                    (625.32, 1441.8000000000002),
                  ]
if __name__ == "__main__":
    DEBUG = True
else:
    DEBUG = False
class CamArea (ImageArea):
    RAWIMAGECORNERS = None
    CHESSBOARDCORNERS = None
    def __init__(self, cam=0, dims=MAXCAPSIZE, displayDims = (1366, 1024)):
        # Create a new window
        CamArea.RAWIMAGECORNERS = [(0,0), (dims[0], 0), (dims[0], dims[1]), (0, dims[1])]
        CamArea.CHESSBOARDCORNERS = [(5*dims[0]/16.0, 5*dims[1]/16.0), 
                                     (11*dims[0]/16.0, 5*dims[1]/16.0),
                                     (11*dims[0]/16.0, 11*dims[1]/16.0),
                                     (5*dims[0]/16.0, 11*dims[1]/16.0),]
   
        ImageArea.__init__(self)

        #GUI Data
        self.shouldUpdate = True
        self.imageScale = 0.5
        self.prevImage = None
        self.isCalibrating = True

        #Camera Data
        self.currentCamera = cam
        self.dimensions = dims
        self.warpCorners = []  #DEFAULT_CORNERS
        self.targetWarpCorners = CamArea.RAWIMAGECORNERS
        self.capture, self.captureDims =  \
                initializeCapture(self.currentCamera, dims)
        self.displayDims = displayDims
        self.imageScale = None
        self.setDisplayDims(displayDims)
        self.boardCapture = BoardChangeWatcher()

        #Event hooks
        gobject.idle_add(self.idleUpdateImage)
        self.set_property("can-focus", True)  #So we can capture keyboard events
        self.connect("button_press_event", self.onMouseDown)
        #self.connect("visibility_notify_event", self.onVisibilityChange)
        #self.connect("motion_notify_event", self.onMouseMove)
        self.connect("button_release_event", self.onMouseUp)
        self.connect("key_press_event", self.onKeyPress)
        self.set_events(gtk.gdk.BUTTON_RELEASE_MASK
                       | gtk.gdk.BUTTON_PRESS_MASK
                       | gtk.gdk.KEY_PRESS_MASK
                       | gtk.gdk.VISIBILITY_NOTIFY_MASK
                       | gtk.gdk.POINTER_MOTION_MASK 
                       )
        if DEBUG:
            self.debugVideoWriter = None 
        self.callBacks = {}
        
    def idleUpdateImage(self):
        """An idle process to update the image data, and
        the cvImage field"""
        cvImage = self.prevImage = captureImage(self.capture)
        if len(self.warpCorners) == 4:
            cvImage = warpFrame(self.prevImage, self.warpCorners, self.targetWarpCorners)
            
        if not self.isCalibrating:
            self.boardCapture.updateBoardImage(cvImage)
            cvImage = self.boardCapture._fgFilter.getBackgroundImage()
        
        #Do the displaying
        self.displayImage = resizeImage(cvImage, scale = self.imageScale)
        self.setCvMat(self.displayImage)
        if DEBUG:            
            if self.debugVideoWriter is None:
                self.debugVideoWriter = cv.CreateVideoWriter("Debug.avi", 
                                                             cv.CV_FOURCC('D', 'I', 'V', 'X'), 
                                      
                          1, cv.GetSize(self.displayImage))
            cv.WriteFrame(self.debugVideoWriter, cv.GetImage(self.displayImage))

        
        return self.shouldUpdate
    
    def switchCamera(self, camNumber):
        """Switch the camera used to capture"""
        log.debug("Trying to use camera %s" % (camNumber,))
        self.currentCamera = camNumber 
        self.warpCorners = []  #DEFAULT_CORNERS
        self.targetWarpCorners = CamArea.RAWIMAGECORNERS
        self.capture, self.captureDims =  \
                initializeCapture(self.currentCamera, self.dimensions)
        self.setDisplayDims(self.displayDims)

    def onMouseDown(self, widget, e):
        """Respond to a mouse being pressed"""
        return
    def onMouseMove(self, widget, e):
        """Respond to the mouse moving"""
        return
    
    def findCalibrationChessboard(self):
        self.targetWarpCorners = CamArea.CHESSBOARDCORNERS
        self.warpCorners = findCalibrationChessboard(self.prevImage)

    def onMouseUp(self, widget, e):
        """Respond to the mouse being released"""
        self.targetWarpCorners = CamArea.RAWIMAGECORNERS #Make sure that we're aligning to manually selected corners
        if len(self.warpCorners) >= 4:
            #self.warpCorners = getNewCorners(self.warpCorners)
            log.debug("Reset Corners")
            self.warpCorners = []
            self.boardCapture.reset()
        else:
#            x, y = self.findCalibrationCorner(e.x / self.imageScale,
#                                             e.y / self.imageScale,
#                                             window=int(4 / self.imageScale))
            (x, y) = (e.x / self.imageScale, e.y / self.imageScale)
            self.warpCorners.append((x, y))
            if len(self.warpCorners) == 4:
                self.boardCapture.reset()
                self.resume()
            log.debug("Corner %s, %s" % (x, y))

    def onKeyPress(self, widget, event, data=None):
        """Respond to a key being pressed"""
        key = chr(event.keyval % 256)
        if key == 'q':
            exit(0)
        elif key == 'c':
            log.debug("Corners: %s" % (str(self.findCalibrationChessboard())))
        elif key == '<':
            log.debug("Previous Camera")
            self.switchCamera(self.currentCamera-1)
        elif key == '>':
            log.debug("Next Camera")
            self.switchCamera(self.currentCamera+1)
        #Go through all the registered callbacks
        for func in self.callBacks.get(key, []):
            func()

    def registerKeyCallback(self, keyVal, function):
        """Register a function to be called when
        a certain keyVal is pressed"""
        self.callBacks.setdefault(keyVal, []).append(function)



    def pause(self):
        log.debug("Paused...")
        self.shouldUpdate = False

    def resume(self):
        log.debug("...Resumed")
        self.shouldUpdate = True
        gobject.idle_add(self.idleUpdateImage)


    def setDisplayDims(self, dims):
        curDims = self.captureDims
        wscale = dims[0] / float(curDims[0])
        hscale = dims[1] / float(curDims[1])
        self.imageScale = min(hscale, wscale)
        log.debug("Scaling image to %s x %s" % (self.imageScale * curDims[0],
                                                self.imageScale * curDims[1]))

    def getRawImage(self):
        """Get the full-size, unaltered image from this cam"""
        return self.prevImage
    
    def getDisplayImage(self):
        """Get the image that is displayed on the view right now"""
        return self.displayImage
    

        
#~~~~~~~~~~~~~~~~~~~~~~~`
#Helper Functions for CamArea



def main(args):
    camNum = 0
    if len(args)>1:
        camNum = int(args[1])
    camWindow = gtk.Window()

    cam = CamArea(cam=camNum)
    camWindow.add(cam)

    def toggleCalibrating(camArea):
        camArea.isCalibrating = not camArea.isCalibrating
        
    cam.registerKeyCallback('C', lambda: toggleCalibrating(cam))
    camWindow.connect("destroy", gtk.main_quit)

    camWindow.show_all()

    gtk.main()
if __name__ == "__main__":
    main(sys.argv)
