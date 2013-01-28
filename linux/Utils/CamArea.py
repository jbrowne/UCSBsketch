#!/usr/bin/env python
import sys
if __name__ == "__main__":
    sys.path.append("./")
    print sys.path

from Utils import Logger
from Utils.ImageArea import ImageArea
from sketchvision import ImageStrokeConverter as ISC
import cv
import gobject
import gtk
import pdb
import pygtk
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
class CamArea (ImageArea):
    RAWIMAGECORNERS = None
    CHESSBOARDCORNERS = None
    def __init__(self, dims=MAXCAPSIZE, displayDims = HD720):
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

        #Camera Data
        self.currentCamera = 0
        self.dimensions = dims
        self.warpCorners = []  #DEFAULT_CORNERS
        self.targetWarpCorners = CamArea.RAWIMAGECORNERS
        self.capture, self.captureDims =  \
                initializeCapture(self.currentCamera, dims)
        self.displayDims = None
        self.imageScale = None
        self.setDisplayDims(displayDims)

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
        self.callBacks = {}
        
    def idleUpdateImage(self):
        """An idle process to update the image data, and
        the cvImage field"""
        if len(self.warpCorners) == 4:
            cvImage = captureImage(self.capture)
            cvImage = warpFrame(cvImage, self.warpCorners, self.targetWarpCorners)
        else:
            cvImage = captureImage(self.capture)
        self.prevImage = cvImage
        
        #Do the displaying
        displayImg = resizeImage(self.prevImage, scale = self.imageScale)
        self.setCvMat(displayImg)
        
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
        img = cv.CreateMat(self.prevImage.rows, self.prevImage.cols, cv.CV_8UC1)
        cv.CvtColor(self.prevImage, img, cv.CV_RGB2GRAY)
        cv.AddWeighted(img, -1.0, img, 0, 255, img)
        ISC.saveimg(img)
        #cv.AdaptiveThreshold(img, img, 255, blockSize=39)
        #ISC.saveimg(img)
        
        _, corners = cv.FindChessboardCorners(img,
                                        patternSize,
                                        flags=cv.CV_CALIB_CB_ADAPTIVE_THRESH | 
                                               cv.CV_CALIB_CB_NORMALIZE_IMAGE)
        if len(corners) == 49:
            self.targetWarpCorners = CamArea.CHESSBOARDCORNERS
            self.warpCorners = [corners[0], corners[6], corners[48], corners[42]]
        return corners
        
    def findCalibrationCorner(self, x, y, window=10):
        """find the most likely pixel-precise calibration corner in the 
        neighborhood of (x,y), range is the number of pixels radius to check"""
        #print ""
        def asciiVal(val):
            retlist = (" ", ".", "-", "!", "x", "#")
            idx = int(val / 42)
            return retlist[idx]

        curMaxPt = (x, y)
        curMaxVal = -1
        for ySpan in range(1, window):
            for xSpan in range(1, window):
                try:
                    for dx, dy in ((xSpan, ySpan),
                                    (-xSpan, ySpan),
                                    (-xSpan, -ySpan),
                                    (xSpan, -ySpan)):
                        pt = (x + dx, y + dy)
                        value = sum(self.prevImage[pt[1], pt[0]])
                        #log.debug("Value: %s at %s" % (value, pt))
                        if curMaxVal < value:
                            curMaxVal = value
                            curMaxPt = (x + dx, y + dy)
                            #log.debug("Max Val update %s at %s" % (curMaxVal, curMaxPt))
                except Exception as e:
                    print e
        return curMaxPt

       

    def onMouseUp(self, widget, e):
        """Respond to the mouse being released"""
        self.targetWarpCorners = CamArea.RAWIMAGECORNERS #Make sure that we're aligning to manually selected corners
        if len(self.warpCorners) >= 4:
            #self.warpCorners = getNewCorners(self.warpCorners)
            log.debug("Reset Corners")
            self.warpCorners = []
        else:
#            x, y = self.findCalibrationCorner(e.x / self.imageScale,
#                                             e.y / self.imageScale,
#                                             window=int(4 / self.imageScale))
            (x, y) = (e.x / self.imageScale, e.y / self.imageScale)
            self.warpCorners.append((x, y))
            if len(self.warpCorners) == 4:
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
        """Get the full-size image from this cam"""
        return self.prevImage
        
#~~~~~~~~~~~~~~~~~~~~~~~`
#Helper Functions for CamArea
#~~~~~~~~~~~~~~~~~~~~~~~`
def findChessboard(img, patternSize):
    """Take an 8bit image and return corners found for
    a chessboard pattern with (w,h) number of internal corners"""
    corners = cv.FindChessboardCorners(img,
                                    patternSize,
                                    flags=cv.CV_CALIB_CB_NORMALIZE_IMAGE)
    return corners

def getNewCorners(corners):
    nw, ne, se, sw = corners
    print "1: %s\t2: %s\n\n3: %s\t4: %s" % (nw, ne, sw, se)
    print "0: Reset"
    try:
        choice = int(raw_input("Edit Corner No.> "))
        if choice == 0:
            return []
        else:
            if choice == 1:
                idx = 0
            elif choice == 2:
                idx = 1
            elif choice == 3:
                idx = 3
            elif choice == 4:
                idx = 2
            print corners[idx]
            newCorn = tuple([int(num) for num in raw_input("New corner> ").split()])
            corners[idx] = newCorn

            print "\n".join([str(c) for c in corners])
            return corners
    except Exception as e:
        print "Input error %s" % (e)
        return corners



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

def initializeCapture(camera = 0, dims=(1280, 1024,)):
    capture = cv.CaptureFromCAM(camera)
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





def main():
    camWindow = gtk.Window()

    cam = CamArea( (1600, 1050,) )
    camWindow.add(cam)

    camWindow.connect("destroy", gtk.main_quit)

    camWindow.show_all()

    gtk.main()
if __name__ == "__main__":
    main()
