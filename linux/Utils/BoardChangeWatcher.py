if __name__ == "__main__":
    import sys
    sys.path.append("./")
"""This module supports watching for ink-changes on a whiteboard."""
from Utils import Logger
from Utils.ForegroundFilter import ForegroundFilter
from Utils.ImageUtils import captureImage
from Utils.ImageUtils import changeExposure
from Utils.ImageUtils import initializeCapture
from Utils.ImageUtils import max_allChannel
from Utils.ImageUtils import saveimg
from Utils.ImageUtils import showResized
from Utils.ImageUtils import warpFrame
import cv

CAPSIZE00 = (2592, 1944)
CAPSIZE01 = (2048, 1536)
CAPSIZE02 = (1600, 1200)
CAPSIZE02 = (1280, 960)
CAPSIZE03 = (960, 720)
CAPSIZE04 = (800, 600)
PROJECTORSIZE = (1024, 768)

DEBUG = False

logger = Logger.getLogger("BC_Watcher", Logger.DEBUG)
class BoardChangeWatcher(object):
    """This class watches a whiteboard, and bundles up
    changes of the board's contents as discreet "diff" events"""
    def __init__(self):
        self._fgFilter = ForegroundFilter()
        self._boardDiffHist = []
        self._lastCaptureImage = None
        self.isCaptureReady = False
        # Used to track if we've seen changes since last accept
        self._boardMask = None

    def reset(self):
        self._fgFilter = ForegroundFilter()
        self._boardDiffHist = []
        self._lastCaptureImage = None
        self.isCaptureReady = False

    def setBoardCorners(self, corners, targetCorners=[]):
        """Set the region of the image that covers the board. Used
        to set up a mask for the filters."""
        if self._lastCaptureImage is not None:
            if len(corners) == 4:
                (w, h) = cv.GetSize(self._lastCaptureImage)
                if len(targetCorners) == 0:
                    self._boardMask = cv.CreateMat(h, w, cv.CV_8UC1)
                    cv.Set(self._boardMask, 0)
                    cv.FillConvexPoly(self._boardMask, corners, 255)
                else:
                    print targetCorners, len(targetCorners)
                    self._boardMask = cv.CreateMat(h, w, cv.CV_8UC1)
                    cv.Set(self._boardMask, 255)
                    self._boardMask = warpFrame(self._boardMask, targetCorners,
                                                corners)
                saveimg(self._boardMask, name="BoardMask")
        else:
            logger.warn("Not setting corners. Unknown image size!")

    def setBoardImage(self, image):
        """Force the current background board image to be image"""
        print "Setting board image"
        self._lastCaptureImage = cv.CloneMat(image)
        self._fgFilter.setBackground(image)
        self._boardDiffHist = []
        # logger.debug("Capture is not ready")
        # self.isCaptureReady = False

    def acceptCurrentImage(self):
        """Confirm the current view of the whiteboard as correct (commit it)"""
        image = self._fgFilter.getBackgroundImage()
        self.setBoardImage(image)
        return image

    def updateBoardImage(self, image):
        global DEBUG
        precentDiffThresh = 0.1
        # Lower limit of how many pixels must be different to count
        #   as a change
        totalPixelDiffThresh = 20
        diffMaskThresh = 20
        windowLen = 2
        if self._lastCaptureImage is None:
            self.setBoardImage(image)
            return
        self._fgFilter.updateBackground(image)
        # Now that we've updated the background a little bit, analyze the
        #    difference from the previous backgrounds for consistency
        #    background images for consistency

        # What is the difference between our model of the board and the
        #    current view of the board:
        captureDiffMask = cv.CloneMat(self._fgFilter.getBackgroundImage())
        cv.AbsDiff(captureDiffMask, self._lastCaptureImage, captureDiffMask)
        captureDiffMask = max_allChannel(captureDiffMask)
        cv.Threshold(captureDiffMask, captureDiffMask,
                     diffMaskThresh, 255, cv.CV_THRESH_BINARY)
        # Mask the information according to where the board is
        if self._boardMask is not None:
            cv.And(captureDiffMask, self._boardMask, captureDiffMask)
        else:
            logger.warn("Watching with no board area set!")

        if len(self._boardDiffHist) > windowLen:
            self._boardDiffHist.pop(0)
        self._boardDiffHist.append(captureDiffMask)

        prev = None
        cumulativeDiff = None
        thisDiff = None

        for frame in self._boardDiffHist:
            if prev is None:
                cumulativeDiff = cv.CreateMat(frame.rows, frame.cols, frame.type)
                cv.Set(cumulativeDiff, (0, 0, 0))
                thisDiff = cv.CreateMat(frame.rows, frame.cols, frame.type)
            else:
                cv.AbsDiff(prev, frame, thisDiff)
                cv.Max(thisDiff, cumulativeDiff, cumulativeDiff)
            prev = frame
        # Now that we have the max sequential difference between frames,
        #    smooth out the edge artifacts due to noise
        cv.Smooth(cumulativeDiff, cumulativeDiff, smoothtype=cv.CV_MEDIAN)

        # Mask the information according to where the board is
        if self._boardMask is not None:
            cv.And(cumulativeDiff, self._boardMask, cumulativeDiff)
        else:
            logger.warn("Watching with no board area set!")

        # The difference percentage is in terms of the size of
        #    the changed component from the background
        totalCurrentDiff = cv.CountNonZero(captureDiffMask)
        percentDiff = (cv.CountNonZero(cumulativeDiff) /
                        float(max(totalCurrentDiff, 1)))
        if totalCurrentDiff > totalPixelDiffThresh:
            if percentDiff < precentDiffThresh:
                    logger.debug("Capture is READY!")
                    self.isCaptureReady = True
            else:
                # Only set unready if the difference is large
                logger.debug("Difference found, but capture is not ready")
                self.isCaptureReady = False
        else:
            self.isCaptureReady = False

        if DEBUG:
            showResized("Live Model Difference", captureDiffMask, 0.25)
            showResized("Change of model difference over window", cumulativeDiff, 0.25)

    def captureBoardDifferences(self):
        """Returns a tuple of binary images: (darkerDiff, lighterDiff)
        where the non-zero mask in darkerDiff is the board contents that
        is darker than the last capture, and lighterDiff is the contents
        that is lighter.
        Should check isCaptureReady field before using the results"""
        global DEBUG
        differenceThresh = 10
        curBackground = self._fgFilter.getBackgroundImage()

        darkerDiff = cv.CreateMat(self._lastCaptureImage.rows,
                                  self._lastCaptureImage.cols, cv.CV_8UC1)
        lighterDiff = cv.CloneMat(darkerDiff)
        subtractedImage = cv.CloneMat(curBackground)

        # Get all the points that are lighter in the previous capture,
        #    cleaned up slightly.
        cv.Sub(self._lastCaptureImage, curBackground, subtractedImage)
        cv.Threshold(max_allChannel(subtractedImage), darkerDiff,
                     differenceThresh, 255, cv.CV_THRESH_TOZERO)
        cv.Smooth(darkerDiff, darkerDiff, smoothtype=cv.CV_MEDIAN)

        # Get all the points that are lighter in the current capture,
        #    cleaned up slightly.
        cv.Sub(curBackground, self._lastCaptureImage, subtractedImage)
        cv.Threshold(max_allChannel(subtractedImage), lighterDiff,
                     differenceThresh, 255, cv.CV_THRESH_TOZERO)
        cv.Smooth(lighterDiff, lighterDiff, smoothtype=cv.CV_MEDIAN)

        # Light spots (projector augmented) in the previous image
        lightSpotMask_Prev = findLightSpots(self._lastCaptureImage)

        # Light spots (projector augmented) in the current image
        lightSpotMask_Current = findLightSpots(curBackground)

        # Filter out the spots that were projected before and are now darker
        cv.And(lightSpotMask_Prev, darkerDiff, darkerDiff)
        # Filter out the spots that are now lighter due to projection
        cv.And(lightSpotMask_Current, lighterDiff, lighterDiff)

        # Filter out artifacts along harsh edges from digitization process
        edges = cv.CreateMat(curBackground.rows, curBackground.cols,
                             cv.CV_8UC1)
        edges_temp = cv.CloneMat(edges)
        grayImage = cv.CloneMat(edges)
        cv.CvtColor(self._lastCaptureImage, grayImage, cv.CV_RGB2GRAY)
        cv.Canny(grayImage, edges, 50, 100)

        cv.CvtColor(curBackground, grayImage, cv.CV_RGB2GRAY)
        cv.Canny(grayImage, edges_temp, 50, 100)
        cv.Max(edges, edges_temp, edges)

        # "Opening" the edge images
        # Remove the edge information from the differences
        cv.Sub(darkerDiff, edges, darkerDiff)
        cv.Sub(lighterDiff, edges, lighterDiff)
        # Dilate the differences to finish the "opening"
        cv.Dilate(darkerDiff, darkerDiff)
        cv.Dilate(lighterDiff, lighterDiff)

        # Mask the information according to where the board is
        if self._boardMask is not None:
            cv.And(self._boardMask, darkerDiff, darkerDiff)
            cv.And(self._boardMask, lighterDiff, lighterDiff)
        else:
            logger.warn("Watching with no board area set!")

        if DEBUG:
            saveimg(darkerDiff, name="Darker")
            saveimg(lighterDiff, name="Lighter")
            saveimg(lightSpotMask_Prev, "LightSpotPrev")
            saveimg(lightSpotMask_Current, "LightSpotCurrent")
#            showResized("Darker", darkerDiff, 0.25)
#            showResized("Lighter", lighterDiff, 0.25)
#            showResized("Previous Projection", lightSpotMask_Prev, 0.25)
#            showResized("Current Projection", lightSpotMask_Prev, 0.25)
        return (darkerDiff, lighterDiff)


def findLightSpots(image):
    """Light spots (projector augmented) in the previous image"""
    lightSpot_threshold = 10
    lightSpot_size = 10
    lightSpotsImage = cv.CloneMat(image)

    cv.Smooth(lightSpotsImage, lightSpotsImage, smoothtype=cv.CV_MEDIAN,
              param1=5, param2=5)
    # Find the light spots
    cv.Erode(lightSpotsImage, lightSpotsImage, iterations=lightSpot_size)
    cv.Dilate(lightSpotsImage, lightSpotsImage, iterations=lightSpot_size)
    cv.Sub(image, lightSpotsImage, lightSpotsImage)
    # Threshold on what counts as "light enough"
    lightSpotMask = cv.CreateMat(image.rows, image.cols, cv.CV_8UC1)
    # cv.CvtColor(lightSpotsImage, lightSpotMask, cv.CV_RGB2GRAY)
    lightSpotMask = max_allChannel(lightSpotsImage)
    cv.Threshold(lightSpotMask, lightSpotMask, lightSpot_threshold, 255,
                 cv.CV_THRESH_BINARY_INV)

    cv.Erode(lightSpotMask, lightSpotMask, iterations=3)

    if DEBUG:
#        showResized("Lights Image", lightSpotsImage, 0.25)
#        showResized("Lights Mask", lightSpotMask, 0.25)
        showResized("Lights Mask (filtered)", lightSpotMask, 0.25)
    return lightSpotMask

def main(args):
    global DEBUG
    DEBUG = True
    if len(args) > 1:
        camNum = int(args[1])
        print "Using cam %s" % (camNum,)
    else:
        camNum = 0
    capture, dims = initializeCapture(cam=camNum, dims=CAPSIZE00)
    changeExposure(camNum, value=100)

    dispScale = 0.5
    warpCorners = []
    targetCorners = [(0, 0), (dims[0], 0), (dims[0], dims[1]), (0, dims[1])]

    def onMouseClick(event, x, y, flags, param):
        if event == cv.CV_EVENT_LBUTTONUP:
            if len(warpCorners) != 4:
                warpCorners.append((int(x / dispScale), int(y / dispScale),))
            if len(warpCorners) == 4:
                print warpCorners
    cv.NamedWindow("Output")
    cv.SetMouseCallback("Output", onMouseClick)
    bcWatcher = BoardChangeWatcher()
    dispImage = captureImage(capture)
    # dispImage = warpFrame(dispImage, warpCorners, targetCorners)

    isPaused = False
    while True:
        image = captureImage(capture)
        if not isPaused:
            if len(warpCorners) == 4 and bcWatcher._boardMask is None:
                bcWatcher.setBoardCorners(warpCorners)
            bcWatcher.updateBoardImage(image)
            showResized("FGFilter",
                        bcWatcher._fgFilter.getBackgroundImage(), 0.2)

            if bcWatcher.isCaptureReady:
                (darker, lighter) = bcWatcher.captureBoardDifferences()
                saveimg(darker, "DebugNewInk")
                saveimg(lighter, "DebugNewErase")
                saveimg(bcWatcher._fgFilter.getBackgroundImage(),
                        "DebugBG")
                showResized("Darker", darker, 0.3)
                showResized("Lighter", lighter, 0.3)
                dispImage = bcWatcher.acceptCurrentImage()

            for corner in warpCorners:
                cv.Circle(dispImage, corner, 3, (255, 200, 0))
            showResized("Output", dispImage, dispScale)
        key = cv.WaitKey(50)
        if key != -1:
            key = chr(key % 256)
            if key == 'q':
                break
            if key == 'p':
                isPaused = not isPaused
                if isPaused:
                    print "Paused"
                else:
                    print "Unpaused"
            if key == 'r':
                bcWatcher.setBoardImage(image)
                dispImage = image
            if key == 'R':
                warpCorners = []
            if key in ('+', '='):
                changeExposure(camNum, 100)
            elif key in ('-', '_'):
                changeExposure(camNum, -100)

    cv.DestroyAllWindows()

if __name__ == "__main__":
    main(sys.argv)
