#!/usr/bin/env python
from Utils.StrokeStorage import StrokeStorage
from sketchvision.ImageStrokeConverter import show
import cv
import pdb
import sys


def main(args):
    """Load two lists of strokes and return a score for them"""
    if len(args) < 3:
        print "Usage: %s <strokes1.dat> <strokes2.dat>" % (args[0])
        exit(1)
    strokeLoader = StrokeStorage(args[1])
    strokeList1 = list(strokeLoader.loadStrokes())
    strokeLoader = StrokeStorage(args[2])
    strokeList2 = list(strokeLoader.loadStrokes())
    score = compareStrokeLists(strokeList1, strokeList2)
    print "Similarity score: %s" % (score)
    
def getStrokeMat(strokeList, dims):
    """Draw all of the strokes in white on a black background"""
    strokesMat = cv.CreateMat(dims[1]+10, dims[0]+10, cv.CV_8UC1)
    cv.Set(strokesMat, 0)
    for stk in strokeList:
        prevPt = None
        for pt in stk.Points:
            pt = (int(pt.X), int(pt.Y))
            if prevPt is not None:
                cv.Line(strokesMat, prevPt, pt, 255)
            prevPt = pt
    return strokesMat

def compareStrokeLists(strokeList1, strokeList2):
    """Return a score (0-1) for how similar two lists of strokes
    look"""
    allStrokes = list(strokeList1) + list(strokeList2)
    xmax = int(max([pt.X for stk in allStrokes for pt in stk.Points]))
    ymax = int(max([pt.Y for stk in allStrokes for pt in stk.Points]))
    
    strokesMat1 = getStrokeMat(strokeList1, (xmax, ymax))
    iterations = 4 #How far to dilate the strokes
    dropSpeed = 3 #How fast to discount the surrounding area
    # Do a weighted dilation of the strokes for both lists
    tempMat = cv.CloneMat(strokesMat1)
    for i in range(iterations):
        cv.Dilate(tempMat, tempMat)
        cv.AddWeighted(strokesMat1, 1.0, tempMat, 1/float(dropSpeed * iterations), 0.0, strokesMat1)
    strokesMat2 = getStrokeMat(strokeList2, (xmax, ymax))
    tempMat = cv.CloneMat(strokesMat2)
    for i in range(iterations):
        cv.Dilate(tempMat, tempMat)
        cv.AddWeighted(strokesMat2, 1.0, tempMat, 1/float(dropSpeed * iterations), 0.0, strokesMat2)
    # Find the overlap by taking the min
    cv.Min(strokesMat1, strokesMat2, tempMat)
    maxSum = max(cv.Sum(strokesMat1)[0], cv.Sum(strokesMat2)[0])
    comboSum = cv.Sum(tempMat)[0]
    return comboSum / float(maxSum)

if __name__ == "__main__":
    main(sys.argv)