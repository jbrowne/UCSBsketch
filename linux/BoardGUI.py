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
TEMPCORNERS = [ 
                (608, 340), 
                (2028, 651), 
                (2188, 1605), 
                (371, 1482), 
                ]

MAXWINCORNERS = [
                (411, 292), 
                (1006, 303), 
                (962, 679), 
                (433, 664),
                ]
PROJCORNERS = [(251, 63), 
                (822, 75), 
                (791, 477), 
                (260, 467),]
PROJCORNERS_1024 = [(256, 75), 
                    (824, 87), 
                    (792, 480), 
                    (263, 468),]

def imageDiff(img1, img2):
    """Return an image of the board containing only the difference between the
    two frames"""
    sanityThresh = img1.rows * img1.cols * 0.20 #No more than XX percent change 

    diffImg = copyFrame(img1)
    _, bg_img = ISC.removeBackground(img2)
    retImg = cv.CloneMat(img2)

    #Get the difference mask
    cv.AddWeighted(img2, 1.0, img1, -1.0 ,255, diffImg)
    cv.Smooth(diffImg, diffImg)
    cv.Threshold(diffImg, diffImg, 245, 255, cv.CV_THRESH_BINARY)
    cv.Erode(diffImg, diffImg, iterations=1)

    #If there is a reasonable difference from the last frame
    if cv.CountNonZero(diffImg) > sanityThresh:
        cv.Copy(bg_img, retImg, mask = diffImg)
        return retImg
    else:   
        return bg_img


def getModeFrames(frameCap, window = 5):
    if window > 0:
        scale = 1 / float(window)
        colorframe = frameCap.next()
        frame = cv.CreateMat(colorframe.rows, 
                            colorframe.cols, 
                            cv.CV_8UC1)
        cv.CvtColor(colorframe, frame, cv.CV_RGB2GRAY)
        #frame = threshold(frame)
        endFrame = copyFrame(frame)
        #cv.AddWeighted(frame, 0.0, frame, 1/window ,0.0,endFrame)
        for i in range(window - 1):
            colorframe = frameCap.next()
            cv.CvtColor(colorframe, frame, cv.CV_RGB2GRAY)
            #frame = threshold(frame)
            cv.Smooth(frame, frame, smoothtype= cv.CV_MEDIAN, param1=3)
            cv.Min(frame, endFrame, endFrame)
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
        grayFrame = cv.CreateMat(frame.rows, frame.cols, cv.CV_8UC1)
        cv.CvtColor(frame, grayFrame, cv.CV_RGB2GRAY)
        yield grayFrame

def threshold(img):
    """A fast adaptive threshold using OpenCV's implementation"""
    w, h = img.cols, img.rows
    s = 0.05
    region = (int(s * w), int(s * h), int( (1-2*s) * w), int( (1-2*s) * h))
    subImg = cv.GetSubRect(img, region)
    minVal, maxVal, _, _ = cv.MinMaxLoc(subImg)
    cv.AdaptiveThreshold(img, img, 130, 
        adaptive_method=cv.CV_ADAPTIVE_THRESH_GAUSSIAN_C, 
        blockSize=21)
    return img

def warpFrame(frame, corners, dimensions = None):
    """Transforms the frame such that the four corners (nw, ne, se, sw)
    are in the corner"""
    if dimensions is None:
        w,h = 1280, 1024
    else:
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


class CamProcessor(threading.Thread):
    def __init__(self, gui):
        threading.Thread.__init__(self)
        self.gui = gui
        
        if self.gui is not None:
            self.daemon = True

        self.warpData = {'corners' : TEMPCORNERS}
        cv.NamedWindow("Raw", 1)
        cv.SetMouseCallback("Raw", self.onMouseEvent, None)

        self.rawResolution = (2593,1944) #w, h
        self.viewScale = 0.5

        
    def onMouseEvent(self, event, x, y, flags, param):
        scale = self.viewScale
        if event == cv.CV_EVENT_LBUTTONDOWN:
            newX = int(x / scale)
            newY = int(y / scale)
            print "(%s, %s), " % (newX, newY)
            if len(self.warpData['corners']) == 4:
                print "Reset Warp"
                self.warpData['corners'] = []
            else:
                self.warpData['corners'].append( (newX, newY) ) 
        
    def run(self):
        scale = self.viewScale
        key_sleep = 10
        boardDims = Standalone.WIDTH * 2, Standalone.HEIGHT * 2
        procFrame = None
        procTime = None
        try:
            frameCapture = getFrames()
            while True:
                tempFrame = frameCapture.next()

                corners = self.warpData['corners']
                if len(corners) == 4:
                    tempFrame = warpFrame(tempFrame, 
                            corners, 
                            dimensions = boardDims) 
                    #if procFrame is not None:
                    #    tempFrame = imageDiff(procFrame, tempFrame)
                else:
                    cv.PolyLine(tempFrame, 
                            (corners,), False, (255,0,0), 
                            thickness=5, lineType=8, 
                            shift=0)
                    for pt in corners:
                        cv.Circle(tempFrame, pt, 2, (0,255,0), thickness=-3)
                tempFrame = ISC.resizeImage(tempFrame, scale)
                cv.ShowImage("Raw", tempFrame )
                    

                capKey = cv.WaitKey(key_sleep)
                if capKey != -1:
                    if capKey == 1048603:
                        procFrame = None

                    print "Processing..."
                    key_sleep = 5000
                    #Clear the buffered frames
                    if procTime is not None and time.time() - procTime >= 1.0:
                        for i in range(3):
                            frame = frameCapture.next()
                    frame = frameCapture.next()

                    procTime = time.time()
                    thisFrame = warpFrame(frame, 
                                          corners,
                                          dimensions = boardDims)
                    if procFrame is not None:
                        diffFrame = imageDiff(procFrame, thisFrame)
                    else:
                        diffFrame = thisFrame
                    procFrame = thisFrame

                    ISC.saveimg(frame)
                    ISC.saveimg(procFrame)
                    ISC.saveimg(diffFrame)
                    self.processFrame(diffFrame)
        except:
            raise
        finally:
            print "\nDone!"
            cv.DestroyWindow("w1")

    def processFrame(self, frame):
        """Send a frame to the GUI and let it process all the way"""
        if self.gui is not None:
            #op = partial(self.gui.ResetBoard)
            #self.gui.post(op)
            op = partial(self.gui.LoadStrokesFromImage, frame)
            self.gui.post(op)

def main(args):
    gui = Standalone.TkSketchFrame()
    capture = CamProcessor(gui)
    capture.start()
    gui.run()

if __name__ == "__main__":
    main(sys.argv)
