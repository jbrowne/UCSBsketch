from Utils.MyScriptUtils.MyScriptRequest import MyScriptEncodable
from Utils.MyScriptUtils.MyScriptRequest import MyScriptInputUnit
from Utils.MyScriptUtils.MyScriptRequest import getRequestResponse



def recognizeEquation(strokes):
    """Take in a list of strokes, send them to MyScript, 
    and return any recognized equation"""
    mscRequest = MyScriptEqnRequest.fromInputUnit(MyScriptInputUnit.fromStrokeList(strokes))
    response = getRequestResponse('equationInput', mscRequest)
    return response

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Equation recognition request structures
# http://download.visionobjects.eu/downloads/online-info/MyScriptWebServices/
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
class MyScriptEqnRequest(MyScriptEncodable):
    def __init__(self, components = [], resultTypes=['LATEX']):
        """Constructs a request to be sent to MyScript for 
        interpretation. """
        self.resultTypes = resultTypes
        self.components = components

        
    @staticmethod
    def getRequestUrl():
        """Implemented as a method to not break JSON encoding"""
        return "https://myscript-webservices.visionobjects.com" + \
                 "/api/myscript/v2.0/equation/doSimpleRecognition.json"
     
    @staticmethod
    def fromInputUnit(inputUnit, resultTypes=None):
        if resultTypes is None:
            return MyScriptEqnRequest(inputUnit.components)
        else:
            return MyScriptEqnRequest(inputUnit.components, resultTypes)