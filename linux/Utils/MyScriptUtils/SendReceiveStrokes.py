#!/usr/bin/env python
from SketchFramework.Stroke import Stroke
from Utils import Logger
from Utils.MyScriptUtils.Equations import MyScriptEqnRequest
from Utils.MyScriptUtils.Handwriting import MyScriptHwrParameter
from Utils.MyScriptUtils.Handwriting import MyScriptHwrProperties
from Utils.MyScriptUtils.Handwriting import MyScriptHwrRequest
from Utils.MyScriptUtils.MyScriptRequest import MyScriptInputUnit
from Utils.MyScriptUtils.MyScriptRequest import MyScriptStrokeComponent
from Utils.MyScriptUtils.MyScriptResponse import MyScriptResponse
try:
    from Utils.MyScriptUtils.MyScriptConfig import getMyScriptApiKey
except:
    print "Error importing configuration file: MyScriptConfig.py"
    exit(1)
import json
import requests
import sys
if __name__ == '__main__':
    sys.path.append('../../')


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Convenience functions and wrappers
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
msclogger = Logger.getLogger("MyScript", Logger.DEBUG)
def recognizeHandwriting(strokes):
    """Take in a list of strokes, send them to MyScript, 
    and return any recognized handwriting"""
    mscRequest = MyScriptHwrRequest(inputUnitList=[MyScriptInputUnit.fromStrokeList(strokes)])
    encoded = json.dumps(mscRequest, cls=MyScriptJsonEncoder)
    msclogger.debug("Requesting Handwriting recognition")
    rq = requests.post(mscRequest.getRequestUrl(),
                       data={'apiKey':getMyScriptApiKey(), 'hwrInput':encoded})
    try:
        response = MyScriptResponse.fromDict(json.loads(rq.text))
    except:
        msclogger.error(rq.text)
        raise
    msclogger.debug("Recognized as '%s'" % (response.result.textSegmentResult.candidates[0].label))
    return response

def recognizeEquation(strokes):
    """Take in a list of strokes, send them to MyScript, 
    and return any recognized equation"""
    mscRequest = MyScriptEqnRequest.fromInputUnit(MyScriptInputUnit.fromStrokeList(strokes))
    encoded = json.dumps(mscRequest, cls=MyScriptJsonEncoder)
    msclogger.debug("Requesting Equation recognition")
    rq = requests.post(mscRequest.getRequestUrl(),
                       data={'apiKey':getMyScriptApiKey(), 'equationInput':encoded})
    try:
        response = MyScriptResponse.fromDict(json.loads(rq.text))
    except:
        msclogger.error(rq.text)
        raise
    msclogger.debug("Recognized as '%s'" % (response.result.results))
    return response

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
    

def flipStrokes(strokes):
    flipped = []
    for stroke in strokes:
        points = list(stroke.Points)
        for pt in points:
            pt.Y = 2000 - pt.Y
        flipped.append(Stroke(points))
    return flipped

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Encoding a recognition request
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def fields(obj):
    """Return fields of an object (not methods or "__" attributes)"""
    return [attr for attr in dir(obj) 
                if not attr.startswith("__")
                and not callable(getattr(obj, attr))]
    
class MyScriptJsonEncoder(json.JSONEncoder):
    def default(self, obj):
        """Handle the tree of JSON encoding for MyScript request objects"""
        if  isinstance(obj, (MyScriptEqnRequest,
                             MyScriptHwrRequest,
                             MyScriptHwrProperties, 
                             MyScriptHwrParameter, 
                             MyScriptInputUnit)):
            retDict = {}
            for attr in fields(obj):
                retDict[attr] = self.default(getattr(obj, attr))
            return retDict
        elif isinstance(obj, MyScriptStrokeComponent):
            retDict = {'type' : obj.c_type}
            retDict['x'] = obj.x
            retDict['y'] = obj.y
            return retDict
        else:
            return obj


 
def main(args):
#    testResponse = """{"instanceId":"a6ec1b9a-3499-41a8-a991-c0c853b8e62a","result":{"textSegmentResult":{"selectedCandidateIdx":0,"candidates":[{"label":"eo","normalizedScore":1.0,"resemblanceScore":0.57856077,"spellingDistortionRatio":0.0,"children":[{"inkRanges":"0-0-0:0-1-74","selectedCandidateIdx":0}]}]},"wordCandidates":[{"inkRanges":"0-0-0:0-1-74","candidates":[{"label":"eo","normalizedScore":1.0,"resemblanceScore":0.57856077,"spellingDistortionRatio":0.0,"children":[{"inkRanges":"0-0-0:0-0-80","selectedCandidateIdx":0},{"inkRanges":"0-1-0:0-1-74","selectedCandidateIdx":0}]}]}],"charCandidates":[{"inkRanges":"0-0-0:0-0-80","candidates":[{"label":"e","normalizedScore":0.5019608,"resemblanceScore":0.61346376,"spellingDistortionRatio":0.0}]},{"inkRanges":"0-1-0:0-1-74","candidates":[{"label":"o","normalizedScore":0.4117647,"resemblanceScore":0.57856077,"spellingDistortionRatio":0.0}]}],"tagItems":[{"tagType":"TEXT_LINE","inkRanges":"0-0-0:0-1-74"},{"tagType":"TEXT_BLOCK","inkRanges":"0-0-0:0-1-74"}]}}"""
#    testEqnResponse = """{"instanceId":"e9830e67-fa05-420f-a955-e403d4aabf30","result":{"results":[{"type":"LATEX","value":"A=72"}]}}"""
#    print MyScriptResponse.fromDict(json.loads(testEqnResponse))       
    testCaptureAndRecognize()
if __name__ == "__main__":
    main(sys.argv)
