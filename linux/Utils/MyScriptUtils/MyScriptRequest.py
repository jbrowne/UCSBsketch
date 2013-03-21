from SketchFramework.Stroke import Stroke
from Utils.MyScriptUtils.MyScriptConfig import getMyScriptApiKey
from Utils.MyScriptUtils.MyScriptResponse import MyScriptResponse
import json
import requests



def getRequestResponse(varName, mscRequest):
    """Send the request to the server, and return the response MyScript
    object. varName is the name of the encoded request (mscRequest) 
    as expected by MyScript, e.g. 'equationInput', 'hwrInput'"""
    encoded = json.dumps(mscRequest, cls=MyScriptJsonEncoder)
    rq = requests.post(mscRequest.getRequestUrl(),
                       data={'apiKey':getMyScriptApiKey(), varName:encoded})
    try:
        response = MyScriptResponse.fromDict(json.loads(rq.text))
    except:
        raise Exception(rq.text)
    return response


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
        if isinstance(obj, MyScriptStrokeComponent):
            retDict = {'type' : obj.c_type}
            retDict['x'] = obj.x
            retDict['y'] = obj.y
            return retDict
        elif  isinstance(obj, MyScriptEncodable):
            retDict = {}
            for attr in fields(obj):
                retDict[attr] = self.default(getattr(obj, attr))
            return retDict
        else:
            return obj


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# MyScript request objects shared between tasks
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
class MyScriptEncodable(object):
    """A dummy class that all MyScript classes inherit from,
    for encoding purposes."""
    def __init__(self):
        raise NotImplemented
    
class MyScriptInputUnit(MyScriptEncodable):
    @staticmethod
    def fromStrokeList(strokes):
        """Factory method to create a MyScriptInputUnit from
        a list of Stroke objects"""
        components = []
        for stk in strokes:
            components.append(MyScriptStrokeComponent(stroke=stk))
        return MyScriptInputUnit(components)
    def __init__(self, components=[]):
        assert type(components) is list
        self.components = components
        
class MyScriptComponent(MyScriptEncodable):
    def __init__(self, c_type):
        self.c_type = c_type

class MyScriptStrokeComponent(MyScriptComponent):
    """A class for representing a Stroke object as a MyScript component"""
    def __init__(self, stroke=Stroke()):
        MyScriptComponent.__init__(self, 'stroke')        
        self.x = []
        self.y = []
        for p in stroke.Points:
            self.x.append(p.X)
            self.y.append(p.Y)