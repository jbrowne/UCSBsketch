"""
filename: Template.py

description:


Doctest Examples:

"""

#-------------------------------------
import itertools #for permutations
import math

from Utils import GeomUtils
from Utils import Logger

from SketchFramework import Point
from SketchFramework import Stroke
from SketchFramework import SketchGUI
from SketchFramework.Annotation import Annotation
from SketchFramework.Board import BoardObserver, BoardSingleton


logger = Logger.getLogger('TemplateDict', Logger.WARN )

#-------------------------------------
        
class TemplateDict( object ):
    "Compares all strokes with templates and annotates strokes with any template within some threshold."
    def __init__(self, filename, resampleSize = 64):
        
        self._templates = {}
        self._loadTemplates(filename = filename)
        self._resampleSize = resampleSize
        

    def getTemplates(self):
        "Returns a dict of named templates: {'name':stroke}"
        return dict(self._templates)
        
    def _loadTemplates(self, filename):
        "Load templates from filename into self._templates"
        logger.debug("Loading templates: %s" % filename)
        try:
           fp = open(filename, "r")
        except:
           return
        
        self._templates = {}
        current_template = None 
        for line in fp.readlines():
           fields = line.split()
           if line.startswith("#TEMPLATE"):
               #assert len(fields) == 3
               template_name = fields[1]
               current_template_set = self._templates.setdefault(template_name, [])
               current_template = []
               current_template_set.append(current_template)
               
           elif line.startswith("#END"):
               assert len(fields) == 2
               assert fields[1] == template_name
               
               template_name = None
               current_template = None
               
               logger.debug('   "%s" loaded' % template_name)
           elif len(line.strip()) > 0:
               assert len(fields) == 2
               x = float(fields[0])
               y = float(fields[1])
               assert current_template is not None
               current_template.append(Point.Point(x, y))
        fp.close()
        logger.debug("Loaded %s templates" % len(self._templates))
        return self._templates

    def Score( self, strokelist, max_return = 1, interest = 0.2):
        "Compare these strokes to all templates, and return the best templates with their scores. "
        ROTATIONS = 16
        best_templ = None 
        for stroke_order in itertools.permutations(strokelist):
            pointlist = []
            for s in stroke_order:
                pointlist.extend(s.Points)
            new_stroke = Stroke.Stroke(points=pointlist)
            
            for name, template_set in self._templates.items():
                for template in template_set:
                    for angle in [2 * math.pi / ROTATIONS * i for i in range(ROTATIONS)]:
                        end_template = GeomUtils.rotateStroke(Stroke.Stroke(points=template), angle).Points
                        firstpass_score = _scoreStroke(new_stroke, end_template, 10)
                        if best_templ is not None and firstpass_score - 0.1 > best_templ['score']:
                            continue
                        score = _scoreStroke(new_stroke, end_template, len(end_template))
                        logger.debug("   '%s' ... %s" % (name, score))
                
                        if best_templ is None:
                            best_templ = {'score': score + 1}
                    
                        if score < best_templ['score']:
                            best_templ['name'] = name
                            best_templ['score'] = score
                            best_templ['template'] = end_template
        return best_templ

#-------------------------------------

def _scoreStroke(stroke, template, sample_size = None):
    
    if sample_size is None:
        sample_size = len(template)
        
    sNorm = GeomUtils.strokeNormalizeSpacing(stroke, len(template))
    centr = GeomUtils.centroid(sNorm.Points)
    numPoints = len(sNorm.Points)
    
    point_vect = []
    templ_vect = []

    numPoints = len(template)
    if len(template) == len(sNorm.Points):
        for idx in range(0, numPoints, numPoints/sample_size ):
       
           templ_vect.append(template[idx].X)
           templ_vect.append(template[idx].Y)
       
           p = sNorm.Points[idx]
           point_vect.append(p.X - centr.X)
           point_vect.append(p.Y - centr.Y)
       
        angularDist = GeomUtils.vectorDistance(point_vect, templ_vect)
    else:
        angularDist = math.pi
    return angularDist

#-------------------------------------


if __name__ == "__main__":
    Logger.setDoctest(logger) 
    import doctest
    doctest.testmod()
