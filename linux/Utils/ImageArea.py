#!/usr/bin/env python

# example helloworld2.py

from Utils import Logger
import cv
import gtk
    
log = Logger.getLogger("ImageArea", Logger.DEBUG)
    
class ImageArea (gtk.EventBox):
    def __init__(self):
        # Create a new window
        gtk.EventBox.__init__(self)

        #GUI Data
        self.gtkImage = gtk.Image()
        self.add(self.gtkImage)
                
        #Camera Data
        self.cvImage = None

    def getCvImage(self):
        return self.cvImage

    def setCvMat(self, cvMat):
        print "Setting CVMat"
        iplImg = cv.GetImage(cvMat)
        cv.CvtColor(iplImg, iplImg, cv.CV_BGR2RGB)
        img_pixbuf = gtk.gdk.pixbuf_new_from_data(iplImg.tostring(),
                                                  gtk.gdk.COLORSPACE_RGB,
                                                  False,
                                                  iplImg.depth,
                                                  iplImg.width,
                                                  iplImg.height,
                                                  iplImg.width * iplImg.nChannels)
        self.gtkImage.set_from_pixbuf(img_pixbuf)
        self.cvImage = cvMat




def main():
    imWindow = gtk.Window()

    imArea = ImageArea()
    imWindow.add(imArea)

    imWindow.connect("destroy", gtk.main_quit)

    imWindow.show_all()
    
    imArea.setCvMat(cv.LoadImageM("/home/jbrowne/src/whiteboard/photos/2012-07-06-12:53:05.jpg"))

    gtk.main()
if __name__ == "__main__":
    main()
