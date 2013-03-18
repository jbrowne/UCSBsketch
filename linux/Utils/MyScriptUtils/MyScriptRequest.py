# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# MyScript request objects shared between tasks
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
from SketchFramework.Stroke import Stroke


class MyScriptInputUnit(object):
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
        
class MyScriptComponent(object):
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