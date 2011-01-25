"""
Monitors all annotations and makes them visible on the board
for the purposes of debugging one's programs


>>> class myAnnotation(Annotation):  pass
... 
>>> d = DebugObserver()
>>> d.trackAnnotation(myAnnotation)

FIXME: need some way to actually trigger the proper events to 
       actually test that the visualizer is called correctly

"""

import time
from Utils import Logger
from Utils import GeomUtils
from SketchFramework.Point import Point
from SketchFramework.Board import BoardObserver, BoardSingleton
from SketchFramework.Annotation import Annotation, AnnotatableObject

logger = Logger.getLogger('DiGraphObserver', Logger.WARN )

#-------------------------------------
class DebugObserver( BoardObserver ):
    "Watches for all annotations, and draws them"

    def __init__(self):
        BoardSingleton().AddBoardObserver( self )
	self.watchSet = set([]) # set of annotation types to track
	self.seenBefore = {} # set of particular annotation that we have already drawn

    def trackAnnotation(self,annoType):
        logger.debug("debugObserver adding %s", annoType.__name__ );
        # add this annotation type to the list to track
        self.watchSet.add(annoType)

    def drawMyself( self ):
        # FIXME: does this tie us to the tk front-end?  If so, what should
        # we put into the GUI API to enable this sort of animation? is it mostly 
        # "update" that is needed?
        from SketchFramework import SketchGUI as gui
        canvas = gui.SketchGUISingleton()
        color_levels = { 0: "#FF6633", 1: "#FF00FF", 2: "#3366FF", 3: "#00CC00",}
        scale = 18  # pixels for text size

        # start with a list of all the annotations
        allAnnoSet = set([])
        for stroke in BoardSingleton().Strokes:
            for anno in stroke.findAnnotations(None):
                if anno.isType( list(self.watchSet) ):
                    allAnnoSet.add( anno )

        # now make a map from the sets of strokes to the annotations on them
        annoMap = {} # dictionary of {frozenset(strokes):[annotations]}
        for anno in allAnnoSet:
            strokeset = frozenset(anno.Strokes)
            if strokeset not in annoMap:
                annoMap[strokeset] = []
            annoMap[strokeset].append( anno )

        # now assign a unique size for each anno on a given set of strokes
        sizeDict = {}
        for strokeset in annoMap.keys():
            depth = 0
            for anno in annoMap[strokeset]:
                sizeDict[anno] = depth
                depth += 1

        # sort the annotations based on the time at which they were added
        annoList = list(allAnnoSet)
        annoList.sort(key= (lambda x: x.Time))
        for anno in annoList:
            nestlevel = sizeDict[anno] # get the nesting level for this annotation
            # for the set of stroke this anno is annotating, find the bounding box
            
            tl = anno.Strokes[0].BoundTopLeft
            br = anno.Strokes[0].BoundBottomRight
            tlx = tl.X
            tly = tl.Y
            brx = br.X
            bry = br.Y
            
            bottomright_list = [s.BoundBottomRight for s in anno.Strokes]
            topleft_list = [s.BoundTopLeft for s in anno.Strokes]
            br, tl = _nestingBox(bottomright_list, topleft_list, scale = nestlevel*3)
            br.Y -= nestlevel * scale # save some space for text on bottom of box

            # if this is a "new" anno, wait a little before drawing
            if anno not in self.seenBefore:
                #time.sleep(0.5)
                self.seenBefore[anno] = True

            # now draw the actual boxes
            labeltext = anno.classname() + " " + hex(id(anno))
            tlx = tl.X
            tly = tl.Y
            brx = br.X
            bry = br.Y
            
            gui.drawBox(tl,br,color=color_levels[nestlevel % len(color_levels)])
            gui.drawText(tl.X, br.Y+scale, size = 12, InText=labeltext)
#            SketchGUI.Singleton().Redraw() 

def _nestingBox(bottomright_list, topleft_list, scale = 0):
    topleft = Point(0,0,0)
    topleft.X = min([p.X for p in topleft_list]) - scale
    topleft.Y = max([p.Y for p in topleft_list]) + scale

    bottomright = Point(0,0,0)
    bottomright.X = max([p.X for p in bottomright_list]) + scale
    bottomright.Y = min([p.Y for p in bottomright_list]) - scale

    return bottomright, topleft


#-------------------------------------
# if executed by itself, run all the doc tests

if __name__ == "__main__":
    Logger.setDoctest(logger) 
    import doctest
    doctest.testmod()


