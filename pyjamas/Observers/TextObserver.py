"""
filename: TextObserver.py

description:
   This module implements 3 classes, TextAnnotation (which is applied to any 
   set of annotableObjects to describe it as a a block of text), TextMarker (which watches
   for strokes that looks like text and adds the text annotation), and
   TextVisualizer (that watches for text annotations and draws the appropriate
   text box to the screen)


Doctest Examples:

>>> t = TextMarker()

"""

#-------------------------------------

import math
from Utils import Logger
from Utils import GeomUtils

from Observers import CircleObserver
from Observers import LineObserver
from Observers import ObserverBase

from SketchFramework import SketchGUI
from SketchFramework.Point import Point
from SketchFramework.Stroke import Stroke
from SketchFramework.Board import BoardObserver, BoardSingleton
from SketchFramework.Annotation import Annotation, AnnotatableObject

logger = Logger.getLogger('TextObserver', Logger.WARN )

#-------------------------------------

class TextAnnotation(Annotation):
    def __init__(self, text, scale):
        "Create a Text annotation. text is the string, and scale is an appropriate size"
        Annotation.__init__(self)
        self.text = text # a string for the text
        self.scale = scale # an approximate "size" for the text
        self.alternates = [text]

#-------------------------------------

class TextMarker( ObserverBase.Collector ):
    "Watches for strokes that look like text"
    def __init__(self, circularity_threshold=0.90):
        # FIXME: this is for "binary" text right now
        ObserverBase.Collector.__init__( self, \
            [CircleObserver.CircleAnnotation, LineObserver.LineAnnotation], TextAnnotation  )

    def collectionFromItem( self, strokes, annotation ):
        text_anno = None # text_anno will be the return value
        if annotation.isType( CircleObserver.CircleAnnotation ):
            circle = annotation
            text_anno = TextAnnotation("0",circle.radius*2)
        if annotation.isType( LineObserver.LineAnnotation ):
            line = annotation
            # if the line is up/down then it is a one
            if GeomUtils.angleParallel( line.angle, 90 ) > 0.6:
                line_length = GeomUtils.pointDist( line.start_point, line.end_point )
                text_anno = TextAnnotation("1",line_length)
        return text_anno

    def mergeCollections( self, from_anno, to_anno ):
        "merge from_anno into to_anno if possible"
        # check that they have compatable scales
        scale_diff = to_anno.scale / from_anno.scale
        if scale_diff>2.5 or scale_diff<0.4:
            return False
        # check that they are not overlapping
        bb_from = GeomUtils.strokelistBoundingBox( from_anno.Strokes )
        bb_to = GeomUtils.strokelistBoundingBox( to_anno.Strokes )
        if GeomUtils.boundingboxOverlap( bb_from, bb_to ):
            return False

        #  bb[0]-------+
        #   |          |
        #   |          |
        #   | (0,0)    |
        #   +--------bb[1]

        # check that they are next to each other
        if    abs( bb_from[1].X - bb_to[0].X ) > to_anno.scale * 0.75 \
          and abs( bb_from[0].X - bb_to[1].X ) > to_anno.scale * 0.75 :
            return False
        # check y's overlap
        if   bb_from[0].Y - bb_to[1].Y < 0 \
          or bb_to[0].Y - bb_from[1].Y < 0 :
            return False

        # now we know that we want to merge these text annotations
        if bb_from[0].X - bb_to[0].X > 0 :
            to_anno.text = to_anno.text + from_anno.text 
        else :
            to_anno.text = from_anno.text + to_anno.text 
        to_anno.scale = max( to_anno.scale, from_anno.scale )
        return True

#-------------------------------------

class TextVisualizer( ObserverBase.Visualizer ):

    def __init__(self):
        ObserverBase.Visualizer.__init__( self, TextAnnotation )

    def drawAnno( self, a ):
        if len(a.text) >= 1:
            ul,br = GeomUtils.strokelistBoundingBox( a.Strokes )
            logger.debug(a.Strokes)
            height = ul.Y - br.Y
            left_x = ul.X# - height/3
            right_x = br.X + height/2
            midpoint = (ul.Y + br.Y) / 2
            SketchGUI.drawLine( left_x, midpoint, right_x, midpoint, color="#a0a0a0")
            y = br.Y + 5
            for idx, text in enumerate(a.alternates):
                SketchGUI.drawText( br.X, y, text, size=20, color="#a0a0a0" )
                y -= 20

#-------------------------------------
# if executed by itself, run all the doc tests

if __name__ == "__main__":
    Logger.setDoctest(logger) 
    import doctest
    doctest.testmod()
