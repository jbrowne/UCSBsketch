#!/usr/bin/env python

# example helloworld2.py

import sys
if __name__ == "__main__":
    sys.path.append("./")
    print sys.path
from Utils import Logger
import pangocairo
import pdb
import pygtk
import math
pygtk.require('2.0')
import gtk
import gobject
import cv

log = Logger.getLogger("CamArea", Logger.DEBUG)
    
class CamArea (gtk.EventBox):
    def __init__(self, dims = (1280, 1024,) ):
        # Create a new window
        gtk.EventBox.__init__(self)

        #GUI Data
        self.gtkImage = gtk.Image()
        self.add(self.gtkImage)
        self.shouldUpdate = True

        #Camera Data
        self.capture, self.dims = initializeCapture(dims = dims)
        self.cvImage = None
        self.warpCorners = [
                            ]

        #Event hooks
        gobject.idle_add(self.idleUpdateImage)
        self.set_property("can-focus", True) #So we can capture keyboard events
        self.connect("button_press_event", self.onMouseDown)
        self.connect("visibility_notify_event", self.onVisibilityChange)
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
    
    def onVisibilityChange(self, widget, e):
        print e.state

    def onMouseDown(self, widget, e):
        """Respond to a mouse being pressed"""
        return
    def onMouseMove(self, widget, e):
        """Respond to the mouse moving"""
        return
    
    def onMouseUp(self, widget, e):
        """Respond to the mouse being released"""
        print e.x, e.y
        if len(self.warpCorners) >= 4:
            self.warpCorners = []
        else:
            self.warpCorners.append((e.x, e.y,))

    def onKeyPress(self, widget, event, data=None):
        """Respond to a key being pressed"""
        key = chr(event.keyval % 256).lower()
        if key == 'q':
            exit(0)

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
            cvImage = warpFrame(cvImage, self.warpCorners, self.dims)
        self.cvImage = cvImage
        self.setCvMat(self.cvImage)
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
        
#~~~~~~~~~~~~~~~~~~~~~~~`
#Helper Functions for CamArea
#~~~~~~~~~~~~~~~~~~~~~~~`
def warpFrame(frame, corners, dimensions):
    """Transforms the frame such that the four corners (nw, ne, se, sw)
    are in the corner"""
    (w,h) = dimensions
    outImg = cv.CreateMat(h, w, frame.type)
    if len(corners) == 4:
        #w,h = outImg.cols, outImg.rows #frame.cols, frame.rows
        targetCorners = ((0,0), (w,0), (w,h), (0,h))
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
    cv.CvtColor(cvImg, cvImg, cv.CV_BGR2RGB)
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
