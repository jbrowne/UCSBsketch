#!/usr/bin/env python

from SketchFramework.Point import Point
from Utils import Logger
from Utils.CamArea import CamArea
from Utils.ImageArea import ImageArea
from cv2 import cv
from gtkStandalone import GTKGui
import gtk
import pdb
import sketchvision.ImageStrokeConverter as ISC
import sys

log = Logger.getLogger("BoardGUI", Logger.DEBUG)

def captureAndProcessImage(cam, sketchGui):
    cam.isCalibrating = False
    cvImage = cam.getDisplayImage()
#    cam.pause()
    sketchGui.setFullscreen(True)
    sketchGui.grab_focus()
    sketchGui.loadStrokesFromImage(image=cvImage)

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
    
 
def displayCalibrationPattern(gui, points = None):
    """Display a series of circles at the points listed, or at 1/4 of the way
    in from each corner, if no points are provided"""
    if points is None:
        w,h = gui.getDimensions()
        deltaX = w / 4.0
        deltaY = h / 4.0
        points = []
        points.append((deltaX, deltaY,)) #SW
        points.append((w - deltaX, deltaY,)) #SE
        points.append((deltaX, h - deltaY,)) #NW
        points.append((w - deltaX, h - deltaY,)) #NE

    log.debug("Drawing calibration pattern %s" % (points))
    boxes = []
    scale = min(w,h) / 4.0
#    box = ((scale, scale), (3 * scale, 3 * scale))
    box = (points[2], points[1])

    fillWithChessBoard( box, 2, boxes)
    for tl, br in boxes:
        gui.drawBox(Point(*tl), Point(*br), 
                    color="#FFFFFF", fill="#FFFFFF", width = 0)
    #for x,y in points:
        #gui.drawCircle(x,y, color="#AFAFAF", fill = "#FFFFFF", radius=4, width=3)
        #gui.drawCircle(x,y, color="#FFFFFF", radius=1, width=3)
    gui.doPaint()
        
    
def main(args):
    dims = (2592, 1944)
    gui = GTKGui(dims = (1600, 1050))
    cam = CamArea( dims=dims)
#    diffImageArea = ImageArea()
#    lastImage = cv.CreateMat(cam.dimensions[1], cam.dimensions[0], cv.CV_8UC3)
#    cv.Set(lastImage, 0)
#    diffImageArea.setCvMat(lastImage)
    
    cam.pause()
    cam.registerKeyCallback('v', lambda : captureAndProcessImage(cam, gui) )
    cam.registerKeyCallback('P', lambda : cam.resume() )
    cam.registerKeyCallback('p', lambda : cam.pause() )
    gui.registerKeyCallback('v', lambda : captureAndProcessImage(cam, gui) )
    gui.registerKeyCallback('f', lambda : cam.pause() )
    gui.registerKeyCallback('c', lambda : displayCalibrationPattern(gui) )

    sketchWindow = gtk.Window()
    sketchWindow.add(gui)
    sketchWindow.connect("destroy", gtk.main_quit)
    sketchWindow.show_all()
    
#    diffWindow = gtk.Window()
#    diffWindow.add(diffImageArea)
#    diffWindow.connect("destroy", gtk.main_quit)
#    diffWindow.show_all()
    

    cameraWindow = gtk.Window()
    cameraWindow.add(cam)
    cameraWindow.connect("destroy", gtk.main_quit)
    cameraWindow.show_all()

    displayCalibrationPattern(gui)
    gtk.main()


if __name__ == "__main__":
    main(sys.argv)
