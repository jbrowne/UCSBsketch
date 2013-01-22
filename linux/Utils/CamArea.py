#!/usr/bin/env python

# example helloworld2.py

import sys
if __name__ == "__main__":
    sys.path.append("./")
    print sys.path
from Utils import Logger
from sketchvision import ImageStrokeConverter as ISC
import pangocairo
import pdb
import pygtk
import math
pygtk.require('2.0')
import gtk
import gobject
import cv

log = Logger.getLogger("CamArea", Logger.DEBUG)
    
MAXCAPSIZE = (2592, 1944)
HDSIZE = (1920, 1080)
DEFAULT_CORNERS = [
                    (777.6, 239.76000000000002),
                    (2080, 533),
                    (2235.6, 1506.6000000000001),
                    (625.32, 1441.8000000000002),
                  ]
class CamArea (gtk.EventBox):
    def __init__(self, dims = (1280, 1024,) ):
        # Create a new window
        gtk.EventBox.__init__(self)

        #GUI Data
        self.gtkImage = gtk.Image()
        self.add(self.gtkImage)
        self.shouldUpdate = True
        self.imageScale = 0.5

        #Camera Data

        self.cvImage = None
        self.warpCorners = []#DEFAULT_CORNERS
        self.capture, self.captureDims = initializeCapture(dims = MAXCAPSIZE)
        self.setDisplayDims(dims)

        #Event hooks
        gobject.idle_add(self.idleUpdateImage)
        self.set_property("can-focus", True) #So we can capture keyboard events
        self.connect("button_press_event", self.onMouseDown)
        #self.connect("visibility_notify_event", self.onVisibilityChange)
        #self.connect("motion_notify_event", self.onMouseMove)
        self.connect("button_release_event", self.onMouseUp)
        self.connect("key_press_event", self.onKeyPress)
        self.set_events( gtk.gdk.BUTTON_RELEASE_MASK
                       | gtk.gdk.BUTTON_PRESS_MASK
                       | gtk.gdk.KEY_PRESS_MASK
                       | gtk.gdk.VISIBILITY_NOTIFY_MASK
                       | gtk.gdk.POINTER_MOTION_MASK 
                       )
        self.callBacks = {}
    
    def onMouseDown(self, widget, e):
        """Respond to a mouse being pressed"""
        return
    def onMouseMove(self, widget, e):
        """Respond to the mouse moving"""
        return
    

    def findCalibrationChessboard(self):
        patternSize = (7,7) #Internal corners of 8x8 chessboard
        img = cv.CreateMat(self.cvImage.rows, self.cvImage.cols, cv.CV_8UC1)
        cv.CvtColor(self.cvImage, img, cv.CV_RGB2GRAY)
        cv.AddWeighted(img, -1.0, img, 0, 255,img )
        ISC.saveimg(img)
        #cv.AdaptiveThreshold(img, img, 255, blockSize=39)
        #ISC.saveimg(img)
        numFound, corners = cv.FindChessboardCorners(img, 
                                        patternSize,
                                        flags= cv.CV_CALIB_CB_ADAPTIVE_THRESH | 
                                               cv.CV_CALIB_CB_NORMALIZE_IMAGE)
        if len(corners) == 49:
            self.warpCorners = [corners[0], corners[6], corners[48], corners[42]]
        return corners
        
    def findCalibrationCorner(self, x, y, window = 10):
        """find the most likely pixel-precise calibration corner in the 
        neighborhood of (x,y), range is the number of pixels radius to check"""
        #print ""
        def asciiVal(val):
            retlist = (" ", ".", "-", "!", "x", "#")
            idx = int(val / 42)
            return retlist[idx]

        curMaxPt = (x,y)
        curMaxVal = -1
        for ySpan in range(1,window):
            for xSpan in range(1,window):
                try:
                    for dx, dy in ( (xSpan, ySpan), 
                                    (-xSpan, ySpan), 
                                    (-xSpan, -ySpan), 
                                    (xSpan, -ySpan) ):
                        pt = (x+dx, y+dy)
                        value = sum(self.cvImage[pt[1], pt[0]])
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
        if len(self.warpCorners) >= 4:
            #self.warpCorners = getNewCorners(self.warpCorners)
            log.debug("Reset Corners")
            self.warpCorners = []
        else:
            x,y = self.findCalibrationCorner(e.x / self.imageScale, 
                                             e.y / self.imageScale,
                                             window = int(4 / self.imageScale))
            self.warpCorners.append( (x,y) )
            if len(self.warpCorners) == 4:
                self.resume()
            log.debug("Corner %s, %s" % (x,y))

    def onKeyPress(self, widget, event, data=None):
        """Respond to a key being pressed"""
        key = chr(event.keyval % 256)
        if key == 'q':
            exit(0)
        elif key == 'c':
            log.debug("Searching for chessboard...")
            corners = self.findCalibrationChessboard()
            log.debug("%s Corners found" % (len(corners)))

        #Go through all the registered callbacks
        for func in self.callBacks.get(key, []):
            func()

    def getCvImage(self):
        return self.cvImage

    def registerKeyCallback(self, keyVal, function):
        """Register a function to be called when
        a certain keyVal is pressed"""
        self.callBacks.setdefault(keyVal, []).append(function)

    def idleUpdateImage(self):
        """An idle process to update the image data, and
        the cvImage field"""
        #if self.flags() & gtk.HAS_FOCUS:
        cvImage = captureImage(self.capture)
        if len(self.warpCorners) == 4:
            cvImage = warpFrame(cvImage, self.warpCorners, self.captureDims)
        self.cvImage = cvImage
        displayImg = resizeImage(self.cvImage, self.imageScale)
        self.setCvMat(displayImg)
        return self.shouldUpdate

    def pause(self):
        log.debug("Paused...")
        self.shouldUpdate = False

    def resume(self):
        log.debug("...Resumed")
        self.shouldUpdate = True
        gobject.idle_add(self.idleUpdateImage)

    def setCvMat(self, cvMat):
        iplImg = cv.GetImage(cvMat)
        img_pixbuf = gtk.gdk.pixbuf_new_from_data(iplImg.tostring(),
                                                  gtk.gdk.COLORSPACE_RGB,
                                                  False,
                                                  iplImg.depth,
                                                  iplImg.width,
                                                  iplImg.height,
                                                  iplImg.width*iplImg.nChannels)
        self.gtkImage.set_from_pixbuf(img_pixbuf)

    def setDisplayDims(self, dims):
        curDims = self.captureDims
        wscale = dims[0] / float(curDims[0])
        hscale = dims[1] / float(curDims[1])
        self.imageScale = min(hscale, wscale)
        log.debug("Scaling image to %s x %s" % (self.imageScale * curDims[0], 
                                                self.imageScale * curDims[1]) )


        
        
#~~~~~~~~~~~~~~~~~~~~~~~`
#Helper Functions for CamArea
#~~~~~~~~~~~~~~~~~~~~~~~`

def findChessboard(img, patternSize):
    """Take an 8bit image and return corners found for
    a chessboard pattern with (w,h) number of internal corners"""
    corners = cv.FindChessboardCorners(img, 
                                    patternSize,
                                    flags= cv.CV_CALIB_CB_NORMALIZE_IMAGE)
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
        print "Input error"
        return corners



def resizeImage(img, scale):
   retImg = cv.CreateMat(int(img.rows * scale), int(img.cols * scale), img.type)
   cv.Resize(img, retImg)
   return retImg

def warpFrame(frame, corners, dimensions):
    """Transforms the frame such that the four corners (nw, ne, se, sw)
    are dx in from the left/right sides and dy from top/bottom. dx and dy
    are calculated given a standard 8x8 chessboard pattern
    """
    (w,h) = dimensions
    #targetCorners = ( (0,0),
    #                   (w,0),
    #                   (w,h),
    #                   (0,h),
    #                 )
    #dx = w/4.0
    #dy = h/4.0
    dx = 5 * w / 16.0
    dy = 5 * h / 16.0
    targetCorners = ( (int(dx)    , int(dy)),
                      (int(w - dx), int(dy)),
                      (int(w - dx), int(h - dy)),
                      (int(dx)    , int(h - dy)),
                    )
    outImg = cv.CreateMat(h, w, frame.type)
    if len(corners) == 4:
        #w,h = outImg.cols, outImg.rows #frame.cols, frame.rows
        warpMat = cv.CreateMat(3,3,cv.CV_32FC1) #Perspective warp matrix
        cv.GetPerspectiveTransform( corners, 
            targetCorners,
            warpMat)
        #outImg = cv.CloneMat(frame)
        cv.WarpPerspective(frame, outImg, warpMat, 
            (cv.CV_INTER_CUBIC | cv.CV_WARP_FILL_OUTLIERS), 255)
        return outImg
    else:
        return frame

def initializeCapture(dims = (1280, 1024,) ):
    capture = cv.CaptureFromCAM(-1)
    w,h = dims
    cv.SetCaptureProperty(capture, cv.CV_CAP_PROP_FRAME_HEIGHT,h ) 
    cv.SetCaptureProperty(capture, cv.CV_CAP_PROP_FRAME_WIDTH, w)
    reth = int(cv.GetCaptureProperty(capture, cv.CV_CAP_PROP_FRAME_HEIGHT))
    retw = int(cv.GetCaptureProperty(capture, cv.CV_CAP_PROP_FRAME_WIDTH))
    return capture, (retw, reth,)

def captureImage(capture):
    """Capture a new image from capture, then set it as the data
    of gtkImage.
    Returns cv Image of the capture"""
    cvImg=cv.QueryFrame(capture)
    #cv.CvtColor(cvImg, cvImg, cv.CV_BGR2RGB)
    cvMat = cv.GetMat(cvImg)
    return cvMat





def main():
    camWindow = gtk.Window()

    cam = CamArea((800,600))
    camWindow.add(cam)

    camWindow.connect("destroy", gtk.main_quit)

    camWindow.show_all()

    gtk.main()
if __name__ == "__main__":
    main()
