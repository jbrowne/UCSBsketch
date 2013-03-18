# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Parsing and converting a recognition response
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
class MyScriptResponse(object):
    @staticmethod
    def fromDict(response):
        instanceId = response.get('instanceId', None)
        result = MyScriptResult.fromDict(response['result'])
        return MyScriptResponse(instanceId, result)

    def __init__(self, instanceId="DEADBEEF", result=[]):
        self.instanceId = instanceId
        self.result = result
    
    def __repr__(self):
        return u"Id: %s: Result { %s }" % (self.instanceId, self.result)

class MyScriptResult(object):
    """A MyScript result object. These are returned for both Handwriting and
    Equation recognition responses."""
    def __init__(self, textSegmentResult=None, wordCandidates=[],
                  charCandidates=[], tagItems = [], results = [], error=None ):
        #Handwriting fields
        self.textSegmentResult = textSegmentResult
        self.wordCandidates = wordCandidates
        self.charCandidates = charCandidates
        self.tagItems = tagItems
        #Equation fields
        self.results = results
        #Errors and messages
        self.error = error
        
    @staticmethod
    def fromDict(result):
        wordCandidates = []
        for wcDict in result.get('wordCandidates', []):
            wordCandidates.append(MyScriptWordCandidateCollection.fromDict(wcDict))
        charCandidates = []
        for ccDict in result.get('charCandidates', []):
            charCandidates.append(MyScriptCharCandidateCollection.fromDict(ccDict))
        tagItems = []
        for tiDict in result.get('tagItems', []):
            tagItems.append(MyScriptTagItem.fromDict(tiDict))
        tsDict = result.get('textSegmentResult', None)
        if tsDict is not None:
            textSegmentResult = MyScriptTextSegmentResult.fromDict(tsDict)
        else:
            textSegmentResult = None
        errorDict = result.get('error', None)
        error = errorDict
        
        results = []
        for eqnResultDict in result.get('results', []):
            results.append(MyScriptEqnResult.fromDict(eqnResultDict))
            
        return MyScriptResult(textSegmentResult, wordCandidates, 
                              charCandidates, tagItems, results, error)
    
    def __repr__(self):
        return u"TSR: %s, Words: %s, Chars: %s, Tags: %s, Eqns: %s" % (self.textSegmentResult,
                                                             self.wordCandidates,
                                                             self.charCandidates,
                                                             self.tagItems,
                                                             self.results)
        
class MyScriptEqnResult(object):
    @staticmethod
    def fromDict(rDict):
        r_type = rDict['type']
        value = rDict['value']
        return MyScriptEqnResult(r_type, value)

    def __init__(self, r_type, value):
        self.type = r_type
        self.value = value    
        
    def __repr__(self):
        return u'type: %s, value: "%s"' % (self.type, self.value)
        
class MyScriptWordCandidateCollection(object):
    @staticmethod
    def fromDict(wccDict):
        inkRanges = wccDict['inkRanges']
        candidates = []
        for cDict in wccDict['candidates']:
            candidates.append(MyScriptTextCandidate.fromDict(cDict))
        candidates.sort(key=lambda x: x.normalizedScore)
        return MyScriptWordCandidateCollection(inkRanges, candidates)
    
    def __init__(self, inkRanges, candidates):
        self.inkRanges = inkRanges
        self.candidates = candidates
    
    def __repr__(self):
        return u"IRs: %s,Candidates: %s" % (self.inkRanges, self.candidates)
    
class MyScriptTextCandidate(object):
    @staticmethod
    def fromDict(wcDict):
        normalizedScore = float(wcDict['normalizedScore'])
        resemblanceScore = float(wcDict['resemblanceScore'])
        spellingDistortionRatio = float(wcDict['spellingDistortionRatio'])
        label = wcDict['label']
        children = []
        for cDict in wcDict['children']:
            children.append(MyScriptWordCandidateChild.fromDict(cDict))
        return MyScriptTextCandidate(normalizedScore, resemblanceScore, 
                                     spellingDistortionRatio, children, label)
        
    def __init__(self, normalizedScore, resemblanceScore, 
                 spellingDistortionRatio, children, label):
        self.normalizedScore = normalizedScore
        self.resemblanceScore = resemblanceScore
        self.spellingDistortionRatio = spellingDistortionRatio
        self.children = children
        self.label = label

    def __repr__(self):
        return u"nScore: %s,resScore: %s,SDR: %s, kids: %s, label: %s" % \
            (self.normalizedScore, self.resemblanceScore, self.spellingDistortionRatio,
             self.children, self.label)
            
class MyScriptWordCandidateChild(object):
    @staticmethod
    def fromDict(wccDict):
        inkRanges = wccDict['inkRanges']
        selectedCandidateIdx = int(wccDict['selectedCandidateIdx'])
        return MyScriptWordCandidateChild(inkRanges, selectedCandidateIdx)
    
    def __init__(self, inkRanges, selectedCandidateIdx):
        self.inkRanges = inkRanges
        self.selectedCandidateIdx = selectedCandidateIdx
        
    def __repr__(self):
        return u"IRs: %s, candidateIdx: %s" % (self.inkRanges, self.selectedCandidateIdx)
 
        
class MyScriptCharCandidateCollection(object):
    @staticmethod
    def fromDict(cccDict):
        inkRanges = cccDict['inkRanges']
        candidates = []
        for cDict in cccDict['candidates']:
            candidates.append(MyScriptCharCandidate.fromDict(cDict))
        candidates.sort(key=lambda x: x.normalizedScore)
        return MyScriptCharCandidateCollection(inkRanges, candidates)
            
    def __init__(self, inkRanges, candidates):
        self.inkRanges = inkRanges
        self.candidates = candidates

    def __repr__(self):
        return u"IRs: %s, candidates: %s" % (self.inkRanges, self.candidates)

class MyScriptCharCandidate(object):
    @staticmethod
    def fromDict(ccDict):
        normalizedScore = float(ccDict['normalizedScore'])
        resemblanceScore = float(ccDict['resemblanceScore'])
        spellingDistortionRatio = float(ccDict['spellingDistortionRatio'])
        label = ccDict['label']
        return MyScriptCharCandidate(normalizedScore, resemblanceScore, 
                                     spellingDistortionRatio, label)
    def __init__(self, normalizedScore, resemblanceScore, 
                  spellingDistortionRatio, label):
        self.normalizedScore = normalizedScore
        self.resemblanceScore = resemblanceScore
        self.spellingDistortionRatio = spellingDistortionRatio
        self.label = label
    
    def __repr__(self):
        return u"nScore: %s, resScore: %s, SDR: %s, label: %s" % \
            (self.normalizedScore, self.resemblanceScore, 
             self.spellingDistortionRatio, self.label)

class MyScriptTextSegmentResult(object):
    @staticmethod
    def fromDict(tsrDict):
        selectedCandidateIdx = tsrDict['selectedCandidateIdx']
        candidates = []
        for cDict in tsrDict['candidates']:
            candidates.append(MyScriptTextCandidate.fromDict(cDict))
        candidates.sort(key=lambda x: x.normalizedScore)
        return MyScriptTextSegmentResult(candidates, selectedCandidateIdx)
    
    def __init__(self, candidates=[], selectedCandidateIdx=-1):
        self.candidates = candidates
        self.selectedCandidateIdx = selectedCandidateIdx

    def __repr__(self):
        return u"candidates: %s, candidateIdx: %s" % (self.candidates,
                                                      self.selectedCandidateIdx)
       
class MyScriptTagItem(object):
    @staticmethod
    def fromDict(tiDict):
        inkRanges = tiDict['inkRanges']
        tagType = tiDict['tagType']
        return MyScriptTagItem(inkRanges, tagType)
    
    def __init__(self, inkRanges, tagType):
        self.inkRanges = inkRanges
        self.tagType = tagType

    def __repr__(self):
        return u"IRs: %s, tagType: %s" % (self.inkRanges, self.tagType)