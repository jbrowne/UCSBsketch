# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Handwriting recognition request structures
# http://download.visionobjects.eu/downloads/online-info/MyScriptWebServices/
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
from Utils.MyScriptUtils import MyScriptRequest
from Utils.MyScriptUtils.MyScriptRequest import MyScriptComponent
from Utils.MyScriptUtils.MyScriptRequest import MyScriptInputUnit
class MyScriptHwrProperties(object):
    """A hwrProperties object for sending strokes to MyScript"""
    def __init__(self, numTextCandidates=1, 
                       numWordCandidates=1, 
                       numCharCandidates=1):
        self.textCandidateListSize = numTextCandidates
        self.wordCandidateListSize = numWordCandidates
        self.characterCandidateListSize = numCharCandidates

class MyScriptHwrParameter(object):
    """A hwrParameter object for sending stroke requests 
    to MyScript"""
    def __init__(self, hwrProperties = MyScriptHwrProperties(), subsetKnowledges = []):
        self.hwrInputMode = 'CURSIVE' #CURSIVE or ISOLATED
        self.resultDetail = 'CHARACTER' #TEXT, WORD, CHARACTER
        self.language = "en_US"
        self.contentTypes = ['text'] #The lexicons used for language model
        self.hwrProperties = hwrProperties
        if len(subsetKnowledges) > 0:
            self.subsetKnowledges = subsetKnowledges
            
class MyScriptHwrInputUnit(MyScriptInputUnit):
    def __init__(self, hwrInputType = ['SINGLE_LINE_TEXT', 'CHAR', 'WORD'][0], **kwargs):
        MyScriptInputUnit.__init__(self, **kwargs)
        self.hwrInputType = hwrInputType
            
class MyScriptStringComponent(MyScriptComponent):
    """A class for representing a string object as a MyScript component"""
    def __init__(self, string = ""):
        MyScriptComponent.__init__(self, 'string')        
        self.string = string

class MyScriptHwrRequest(object):
    def __init__(self, inputUnitList=[], hwrParameter=MyScriptHwrParameter()):
        """Constructs a request to be sent to MyScript for 
        interpretation. Takes as input a MyScriptHwrParameter and
        a list of MyScriptHwrInputUnit"""
        self.hwrParameter = hwrParameter
        assert type(inputUnitList) is list
        self.inputUnits = inputUnitList        
    @staticmethod
    def getRequestUrl():
        """Implemented as a method to not break JSON encoding"""
        return "https://myscript-webservices.visionobjects.com" +\
                "/api/myscript/v2.0/hwr/doSimpleRecognition.json"
            