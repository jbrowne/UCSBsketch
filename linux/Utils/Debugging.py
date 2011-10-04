from  Utils import GeomUtils
from SketchFramework import Stroke

def strokeCurvatureHistogram(stroke, norm_len = None, gran = 10):
    #points = GeomUtils.strokeNormalizeSpacing( stroke, numpoints=50).Points
    rad2deg = 57.295
    if norm_len == None:
        norm_len = len(stroke.Points)

    norm_stroke = GeomUtils.strokeNormalizeSpacing( stroke, numpoints=norm_len)

    # find the first 90 degree turn in the stroke
    curvatures = GeomUtils.strokeGetPointsCurvature( norm_stroke)

    for idx, ori in enumerate(curvatures):
        print "%s:\t|" % (idx),
        quantity = ori * rad2deg
        while quantity > 0:
            quantity -= gran
            print "X",
        print "\t\t%s" % (ori * rad2deg)
    print "_______________________________"
    print "Max:%s, Avg%s" % (max(curvatures), sum(curvatures)/float(len(curvatures)))
    print "_______________________________"


