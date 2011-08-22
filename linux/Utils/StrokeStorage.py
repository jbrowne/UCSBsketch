from  SketchFramework.Stroke import Stroke
from  SketchFramework.Point import Point
from Utils import Logger

logger = Logger.getLogger('StrokeStorage', Logger.DEBUG)


class StrokeStorage(object):
   def __init__(self, filename = "strokes.dat"):
      self._fname = filename
   def saveStrokes(self, strokelist):
      fd = open(self._fname, "w")
      for strk in strokelist:
         print >> fd, "#STROKE"
         for p in strk.Points:
            print >> fd, "  %s %s %s" % ( p.X, p.Y, p.T)
         print >> fd, "#ENDSTROKE"
         logger.debug("Saved Stroke with %s points" % (len(strk.Points)) )
      fd.close()
   def loadStrokes(self):
      fd = open(self._fname, "r")
      curStroke = None
      for line in fd.readlines():
         if line.startswith("#STROKE"):
            curStroke = Stroke()
         elif line.startswith("#ENDSTROKE"):
            logger.debug("Loaded Stroke with %s points" % (len(curStroke.Points)) )
            yield curStroke
            curStroke = None
         else:
            fields = line.split()
            assert len(fields) <= 3 and len(fields) > 1, "Error: ill-formed point"
            if len(fields) == 2:
               x, y = fields
               t = 0.0
            elif len(fields) == 3:
               x, y, t = fields
               
            curStroke.addPoint ( Point(float(x), float(y), float(t)) )
      fd.close()

         
