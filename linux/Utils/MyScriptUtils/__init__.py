#!/usr/bin/env python
from SketchFramework.Stroke import Stroke
from SketchFramework.Point import Point 
from Utils.MyScriptUtils.Equations import recognizeEquation
from Utils.MyScriptUtils.Handwriting import recognizeHandwriting

    
def flipStrokes(strokes):
    """Invert the stroke vertically (for topleft origin approximation)"""
    flipped = []
    top = max([stk.BoundTopLeft.Y for stk in strokes])
    for stroke in strokes:
        points = []
        for pt in stroke.Points:
            ptCpy = Point(pt.X, top - pt.Y)
            points.append(ptCpy)
        flipped.append(Stroke(points))
    return flipped

if __name__ == '__main__':
    from Utils import Logger
    from Utils.MyScriptUtils.Equations import MyScriptEqnRequest
    from Utils.MyScriptUtils.Handwriting import MyScriptHwrParameter
    from Utils.MyScriptUtils.Handwriting import MyScriptHwrProperties
    from Utils.MyScriptUtils.Handwriting import MyScriptHwrRequest
    from Utils.MyScriptUtils.MyScriptRequest import MyScriptInputUnit
    from Utils.MyScriptUtils.MyScriptRequest import MyScriptJsonEncoder
    from Utils.MyScriptUtils.MyScriptRequest import MyScriptStrokeComponent
    from Utils.MyScriptUtils.MyScriptResponse import MyScriptResponse
    import json
    import requests
    import sys
    try:
        from Utils.MyScriptUtils.MyScriptConfig import getMyScriptApiKey
    except:
        print "Error importing configuration file: MyScriptConfig.py"
        exit(1)
    if __name__ == '__main__':
        sys.path.append('../../')
    
    
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Convenience functions and wrappers
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    msclogger = Logger.getLogger("MyScript", Logger.DEBUG)
    
    
    
    
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Testing Stuff
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def main(args):
        testCaptureAndRecognize()
        
    def testCaptureAndRecognize():
        """Open a GUI and perform recognition when the user hits 'p'"""
        from gtkStandalone import GTKGui
        import gtk
        def printBoardStrokes(board):
            flippedStrokes = flipStrokes(board.Strokes)
            equation = recognizeEquation(flippedStrokes)
            print "Equation: '%s'" % (equation)
            handwriting = recognizeHandwriting(flippedStrokes)
            print "Handwriting: %s" % (handwriting)
        win = gtk.Window()
        gui = GTKGui()
        gui.registerKeyCallback('p', lambda: printBoardStrokes(gui.board))
        win.add(gui)
        win.show_all()
        gtk.main()


    #CALL MAIN
    main(sys.argv)
