"""
filename: TemplateObserver.py

description:


Doctest Examples:

"""

#-------------------------------------
import os
from Utils import GeomUtils
from Utils.Template import TemplateDict
from Utils import Logger

from SketchFramework import Point
from SketchFramework import Stroke
from SketchFramework import SketchGUI

from SketchFramework.Annotation import Annotation
from SketchFramework.Board import BoardObserver, BoardSingleton


logger = Logger.getLogger('TemplateObserver', Logger.DEBUG )

#-------------------------------------

class TemplateAnnotation(Annotation):
    "Annotation for strokes matching templates. Fields: name - the template's tag/name, template - the list of points making up the template"
    def __init__(self, tag, template):
        Annotation.__init__(self)
        self.template = template
        self.name = tag
        
#-------------------------------------

class TemplateMarker( BoardObserver ):
    "Compares all strokes with templates and annotates strokes with any template within some threshold."
    def __init__(self):
        
        BoardSingleton().AddBoardObserver( self )
        BoardSingleton().RegisterForStroke( self )
        self.templateRecognizers = list()
        for filename in os.listdir('./'):
            if filename.endswith('.templ'):
                self.templateRecognizers.append( TemplateDict(filename) )
        
       
    def onStrokeAdded( self, stroke ):
        "Compare this stroke to all templates, and annotate those matching within some threshold."
        logger.debug("Scoring templates")
        for templates in self.templateRecognizers:
            score_dict = templates.Score([stroke])
            logger.debug("   '%s' ... %s" % (score_dict['name'], score_dict['score']))
            if score_dict is not None and score_dict['score'] < 0.2:
                anno = TemplateAnnotation(score_dict['name'], score_dict['template'])
                BoardSingleton().AnnotateStrokes( [stroke], anno )


    def onStrokeRemoved(self, stroke):
        "When a stroke is removed, remove circle annotation if found"
        for anno in stroke.findAnnotations(TemplateAnnotation, True):
            BoardSingleton().RemoveAnnotation(anno)

#-------------------------------------

def scoreStroke(stroke, template, sample_size):
    sNorm = GeomUtils.strokeNormalizeSpacing(stroke, sample_size)
    centr = GeomUtils.centroid(sNorm.Points)
    point_vect = []
    templ_vect = []
    for q in template:
       templ_vect.append(q.X)
       templ_vect.append(q.Y)
    for p in sNorm.Points:
       point_vect.append(p.X - centr.X)
       point_vect.append(p.Y - centr.Y)
    angularDist = GeomUtils.vectorDistance(point_vect, templ_vect)
    return angularDist

#-------------------------------------

class TemplateVisualizer( BoardObserver ):
    "Watches for Template annotations, draws them"
    def __init__(self):
        BoardSingleton().AddBoardObserver( self )
        BoardSingleton().RegisterForAnnotation( TemplateAnnotation, self )
        self.annotation_list = []

    def onAnnotationAdded( self, strokes, annotation ):
        "Watches for annotations of Templates and draws the idealized template" 
        logger.debug( "A stroke was annotated as matching template: %s" % annotation.name )
        self.annotation_list.append(annotation)

    def onAnnotationRemoved(self, annotation):
        "Watches for annotations to be removed" 
        logger.debug( "A template matching %s was removed" % (annotation.name))
        self.annotation_list.remove(annotation)

    def drawMyself( self ):
        for a in self.annotation_list:
            center = GeomUtils.centroid(a.Strokes[0].Points) #Ugly hack to get the center of the annotation!
            templ_stroke = Stroke.Stroke(a.template)
            templ_stroke = templ_stroke.translate(center.X, center.Y)

            SketchGUI.drawText(center.X, center.Y, InText=a.name)
            SketchGUI.drawStroke(templ_stroke, color="#F050F0")

#-------------------------------------
# if executed by itself, run all the doc tests

if __name__ == "__main__":
    Logger.setDoctest(logger) 
    import doctest
    doctest.testmod()
