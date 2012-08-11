#!/usr/bin/env python

import Utils.ImageStrokeConverter as ISC
import Standalone
import threading
import cv
import time
import sys
import Image
import pdb
from functools import partial

CVKEY_ENTER = 1048586
def getFrames (fps = 0):
    capture = cv.CaptureFromCAM(-1)
    cv.SetCaptureProperty(capture, cv.CV_CAP_PROP_FRAME_HEIGHT, 800)
    cv.SetCaptureProperty(capture, cv.CV_CAP_PROP_FRAME_WIDTH, 1280)
    fps = float(fps)
    while True:
        if fps != 0:
            time.sleep(1 / fps )
        cv.GrabFrame(capture)
        frame = cv.CloneMat(cv.GetMat(cv.RetrieveFrame(capture), allowND=1))
        for i in range(5):
            cv.GrabFrame(capture)
            tempFrame = cv.GetMat(cv.RetrieveFrame(capture), allowND=1)
            #cv.AddWeighted(frame, 0.5, tempFrame, 0.5, 0.0, frame)
            cv.Min(frame, tempFrame, frame)
        #frame = cv.CreateMat(tempCap.rows, tempCap.cols, cv.CV_8UC1)
        #cv.CvtColor(tempCap, frame, cv.CV_RGB2GRAY)
        yield frame

def warpFrame(frame, corners):
    """Transforms the frame such that the four corners (nw, ne, se, sw)
    are in the corner"""
    w,h = frame.cols, frame.rows
    targetCorners = ((0,0), (w,0), (w,h), (0,h))
    warpMat = cv.CreateMat(3,3,cv.CV_32FC1) #Perspective warp matrix
    cv.GetPerspectiveTransform( corners, 
        targetCorners,
        warpMat)
    outImg = cv.CloneMat(frame)
    cv.WarpPerspective(frame, outImg, warpMat, 
        (cv.CV_INTER_CUBIC | cv.CV_WARP_FILL_OUTLIERS), 255)
    return outImg


class CamProcessor(threading.Thread):
    def __init__(self, gui):
        threading.Thread.__init__(self)
        self.daemon = True
        self.gui = gui
        
    def run(self):
        cv.NamedWindow("Raw", 1)
        #cv.NamedWindow("Warp", 1)
        corners = ((87, 66), (1010, 45), (1045, 750), (130, 790))
        try:
            frameCapture = getFrames(fps = 0)
            while True:
                frame = frameCapture.next()
                tempFrame = cv.CloneMat(frame)
                cv.PolyLine(tempFrame, 
                        (corners,), True, (255,0,0), 
                        thickness=5, lineType=8, 
                        shift=0)
                small_img = ISC.resizeImage(tempFrame, scale =0.5)
                tempFrame = cv.CreateMat(small_img.rows, 
                            small_img.cols, 
                            cv.CV_8UC1)
                
                cv.CvtColor(small_img, tempFrame, cv.CV_RGB2GRAY)
                cv.AdaptiveThreshold(tempFrame, tempFrame, 255, blockSize=39)

                cv.ShowImage("Raw", frame)
                #cv.ShowImage("Warp", warpFrame(frame, corners) )
                if cv.WaitKey(10) == CVKEY_ENTER:
                    procFrame = warpFrame(frame, corners)
                    ISC.saveimg(frame)
                    #ISC.saveimg(procFrame)
                    self.processFrame(procFrame)
                time.sleep(0.500)
        except:
            raise
        finally:
            print "\nDone!"
            cv.DestroyWindow("w1")

    def processFrame(self, frame):
        """Send a frame to the GUI and let it process all the way"""
        op = partial(self.gui.ResetBoard)
        self.gui.post(op)
        op = partial(self.gui.LoadStrokesFromImage, frame)
        self.gui.post(op)

def main(args):
    gui = Standalone.TkSketchFrame()
    #capture = CamProcessor(gui)
    #capture.start()
    gui.run()

if __name__ == "__main__":
    main(sys.argv)
