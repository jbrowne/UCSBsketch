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
MAXWINCORNERS = [
                (247, 176), 
                (602, 180), 
                (577, 406), 
                (260, 398),
                ]
PROJCORNERS = [(251, 63), 
                (822, 75), 
                (791, 477), 
                (260, 467),]
PROJCORNERS_1024 = [(256, 75), 
                    (824, 87), 
                    (792, 480), 
                    (263, 468),]

def getModeFrames(frameCap, window = 5):
    if window > 0:
        scale = 1 / float(window)
        colorframe = frameCap.next()
        frame = cv.CreateMat(colorframe.rows, 
                            colorframe.cols, 
                            cv.CV_8UC1)
        cv.CvtColor(colorframe, frame, cv.CV_RGB2GRAY)
        frame = threshold(frame)
        endFrame = copyFrame(frame)
        cv.AddWeighted(frame, 0.0, frame, scale ,0.0,endFrame)
        for i in range(window - 1):
            colorframe = frameCap.next()
            cv.CvtColor(colorframe, frame, cv.CV_RGB2GRAY)
            frame = threshold(frame)
            cv.AddWeighted(endFrame, 1.0, frame, scale ,0.0,endFrame)
        return endFrame

def getMedianFrames(window = 5, transform = (lambda x: x)):
    if window > 0:
        midIdx = (window + 1) / 2
        frameCap = getFrames()
        while True:
            frameList = [ transform(frameCap.next())
                            for i in range(window) ]
            resFrame = copyFrame(frameList[0])
            for x in range(resFrame.cols):
                for y in range(resFrame.rows):
                    vals = sorted([f[y,x] for f in frameList]) 
                    val = vals[midIdx]
                    resFrame[y,x] = val
            yield resFrame
            
def copyFrame(frame):
    """Create an empty image of the same size/type as frame"""
    return cv.CreateMat(frame.rows, frame.cols, cv.GetElemType(frame))

def getFrames (fps = 0):
    capture = cv.CaptureFromCAM(-1)
    #w,h = 1920, 1080
    w,h = 2592,1944
    cv.SetCaptureProperty(capture, cv.CV_CAP_PROP_FRAME_HEIGHT, h)
    cv.SetCaptureProperty(capture, cv.CV_CAP_PROP_FRAME_WIDTH, w)
    fps = float(fps)
    while True:
        if fps != 0:
            time.sleep(1 / fps )
        cv.GrabFrame(capture)
        frame = cv.CloneMat(cv.GetMat(cv.RetrieveFrame(capture), allowND=0))
        #frame = cv.CreateMat(tempCap.rows, tempCap.cols, cv.CV_8UC1)
        #cv.CvtColor(tempCap, frame, cv.CV_RGB2GRAY)
        yield frame

def threshold(img):
    """A fast adaptive threshold using OpenCV's implementation"""
    w, h = img.cols, img.rows
    s = 0.05
    region = (int(s * w), int(s * h), int( (1-2*s) * w), int( (1-2*s) * h))
    subImg = cv.GetSubRect(img, region)
    minVal, maxVal, _, _ = cv.MinMaxLoc(subImg)
    cv.AdaptiveThreshold(img, img, 255, 
        adaptive_method=cv.CV_ADAPTIVE_THRESH_GAUSSIAN_C, 
        blockSize=21)
    return img

def warpFrame(frame, corners):
    """Transforms the frame such that the four corners (nw, ne, se, sw)
    are in the corner"""
    w,h = 1280, 1024
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


class CamProcessor(threading.Thread):
    def __init__(self, gui):
        threading.Thread.__init__(self)
        self.gui = gui
        
        if self.gui is not None:
            self.daemon = True

        self.warpData = {'corners' : MAXWINCORNERS }
        cv.NamedWindow("Raw", 1)
        cv.SetMouseCallback("Raw", self.onMouseEvent, None)

        
    def onMouseEvent(self, event, x, y, flags, param):
        if event == cv.CV_EVENT_LBUTTONDOWN:
            print "(%s, %s), " % (x,y)
            if len(self.warpData['corners']) == 4:
                print "Reset Warp"
                self.warpData['corners'] = []
            else:
                self.warpData['corners'].append((x, y))
                
        
    def run(self):
        #cv.NamedWindow("Warp", 1)
        scale = 0.30
        try:
            frameCapture = getFrames()
            while True:
                frame = frameCapture.next()
                tempFrame = ISC.resizeImage(frame, scale)
                #tempFrame = ISC.resizeImage(tempFrame, scale =0.5)
                #tempFrame = cv.CreateMat(small_img.rows, 
                #            small_img.cols, 
                #            cv.CV_8UC1)
                #
                #cv.CvtColor(small_img, tempFrame, cv.CV_RGB2GRAY)
                #cv.AdaptiveThreshold(tempFrame, tempFrame, 255, blockSize=39)

                corners = self.warpData['corners']
                if len(corners) == 4:
                    tempFrame = warpFrame(tempFrame, corners) 
                    tempFrame = ISC.resizeImage(tempFrame, scale)
                else:
                    cv.PolyLine(tempFrame, 
                            (corners,), False, (255,0,0), 
                            thickness=5, lineType=8, 
                            shift=0)
                    for pt in corners:
                        cv.Circle(tempFrame, pt, 2, (0,255,0), thickness=-3)
                cv.ShowImage("Raw", tempFrame )
                    

                if cv.WaitKey(10) != -1:
                    frame = getModeFrames(frameCapture)

                    procFrame = warpFrame(frame, 
                        [(x/scale, y / scale) for x,y in corners] )
                    #procFrame = ISC.resizeImage(procFrame, targetWidth = 1024)
                    ISC.saveimg(tempFrame)
                    ISC.saveimg(frame)
                    ISC.saveimg(procFrame)
                    self.processFrame(procFrame)
                time.sleep(0.500)
        except:
            raise
        finally:
            print "\nDone!"
            cv.DestroyWindow("w1")

    def processFrame(self, frame):
        """Send a frame to the GUI and let it process all the way"""
        if self.gui is not None:
            op = partial(self.gui.ResetBoard)
            self.gui.post(op)
            op = partial(self.gui.LoadStrokesFromImage, frame)
            self.gui.post(op)

def main(args):
    gui = Standalone.TkSketchFrame()
    capture = CamProcessor(gui)
    capture.start()
    gui.run()

if __name__ == "__main__":
    main(sys.argv)
