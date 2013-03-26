#!/usr/bin/env python
from ContinuousCapture import BoardChangeWatcher
from Utils import Logger
from Utils.ImageArea import ImageArea
from Utils.ImageUtils import captureImage
from Utils.ImageUtils import initializeCapture
from Utils.ImageUtils import resizeImage
from Utils.ImageUtils import warpFrame
from multiprocessing.queues import Queue
from sketchvision import ImageStrokeConverter as ISC
import cv
import gobject
import gtk
import multiprocessing
import pdb
import pygtk
import sys
import threading
if __name__ == "__main__":
    sys.path.append("./")
    print sys.path


pygtk.require('2.0')

log = Logger.getLogger("CamArea", Logger.DEBUG)
    
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
    def __init__(self, dims=MAXCAPSIZE, displayDims = (1366, 1024)):
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
        self.currentCamera = 0
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
        patternSize = (7, 7)  #Internal corners of 8x8 chessboard
        grayImg = cv.CreateMat(self.prevImage.rows, self.prevImage.cols, cv.CV_8UC1)
        cv.CvtColor(self.prevImage, grayImg, cv.CV_RGB2GRAY)
        cv.AddWeighted(grayImg, -1, grayImg, 0, 255, grayImg)
        ISC.saveimg(grayImg)
        cornerListQueue = Queue()
        
        def getCorners(idx, inImg, cornersQueue):
            """Search for corners in image and put them in the queue"""
            _, corners = cv.FindChessboardCorners(inImg,
                                            patternSize,
                                            flags=cv.CV_CALIB_CB_ADAPTIVE_THRESH | 
                                                   cv.CV_CALIB_CB_NORMALIZE_IMAGE)
            if len(corners) == 49:            
                cornersQueue.put(corners)

        for i in range(5):
            img = cv.CloneMat(grayImg)
            cv.Dilate(img, img, iterations=i)
            cv.Erode(img, img, iterations=i)
            ISC.saveimg(img)
            
            p = multiprocessing.Process(target=lambda: getCorners(i, img,cornerListQueue))
            p.daemon = True
            p.start()

        try:
            corners = cornerListQueue.get(True, timeout=4)
            self.targetWarpCorners = CamArea.CHESSBOARDCORNERS
            self.warpCorners = [corners[42], corners[0], corners[6], corners[48], ]
    
            debugImg = cv.CreateMat(grayImg.rows, grayImg.cols, cv.CV_8UC3)
            cv.CvtColor(grayImg, debugImg, cv.CV_GRAY2RGB)
            for pt in corners:
                pt = (int(pt[0]), int(pt[1]))
                cv.Circle(debugImg, pt, 4, (255,0,0))
            ISC.saveimg(debugImg)                        
            return corners
        except:
            print "Could not find corners"
            return []

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



def main():
    camWindow = gtk.Window()

    cam = CamArea()
    camWindow.add(cam)

    def toggleCalibrating(camArea):
        camArea.isCalibrating = not camArea.isCalibrating
        
    cam.registerKeyCallback('C', lambda: toggleCalibrating(cam))
    camWindow.connect("destroy", gtk.main_quit)

    camWindow.show_all()

    gtk.main()
if __name__ == "__main__":
    main()
