"""
filename: ObserverBase.py

description:


Doctest Examples:

>>> class MyVisualizer(Visualizer):
...   def drawAnno(self,anno):
...     pass
...
>>> m = MyVisualizer(Annotation)
  
>>> class MyCollector(Collector):
...   def mergeCollections(self,anno):
...     pass
...
>>> class Annotation2(Annotation):
...   pass
>>> m = MyCollector([Annotation],Annotation2)


"""

#-------------------------------------

import pdb
import math
import time
from Utils import Logger
from Utils import GeomUtils
from SketchFramework.Point import Point
from SketchFramework.Stroke import Stroke
from SketchFramework.Board import BoardObserver, BoardSingleton
from SketchFramework.Annotation import Annotation, AnnotatableObject

logger = Logger.getLogger('ObserverBase', Logger.WARN )
#-------------------------------------

class Visualizer( BoardObserver ):
    "Watches for annotations, draws them"
    def __init__(self, anno_type):
        BoardSingleton().AddBoardObserver( self )
        BoardSingleton().RegisterForAnnotation( anno_type, self )
        self.annotation_list = []

    def onAnnotationAdded( self, strokes, annotation ):
        logger.debug("anno added   %s", annotation )
        self.annotation_list.append(annotation)
  
 
    def onAnnotationRemoved(self, annotation):
        logger.debug("anno removed %s", annotation )
        if annotation in self.annotation_list:
            self.annotation_list.remove(annotation)
        

    def drawMyself( self ):
        for a in self.annotation_list:
            self.drawAnno( a )

    def drawAnno( self, anno ):
        logger.error("failure to implement virtual method 'drawAnno'")
        raise NotImplementedError

#-------------------------------------

anim_logger = Logger.getLogger('Animator', Logger.WARN )
class Animator( Visualizer ):
    "Watches for annotations, animates them at about the specified fps. The annotation must "
    CALLTIMES = {} #Maps an annotation to the last time it was "stepped"

    def __init__(self, anno_type = None, fps = 1):
        anim_logger.debug("Initializing: Watch for %s" % (anno_type))
        if not hasattr(anno_type, "step"):
            anim_logger.error("%s must implement 'step'" % (anno_type.__name__))
            raise NotImplementedError

        Visualizer.__init__(self, anno_type)

        self.fps = fps

    def drawMyself( self ):
        "Calls each observed annotation with a step of however many ms since its last call, and then draws the anno"
        for a in self.annotation_list:
            lastcall = Animator.CALLTIMES.get(a, 1000 * time.time())
            anim_logger.debug("Calling %s anno %s ms later" % (a, 1000 * time.time() - lastcall))
            a.step( time.time() - lastcall) 
            anim_logger.debug("Drawing frame for %s" % (a))
            self.drawAnno( a )
            Animator.CALLTIMES[a] =  1000 * time.time()

    def drawAnno( self, anno ):
        anim_logger.error("failure to implement virtual method 'drawAnno'")
        raise NotImplementedError

#-------------------------------------

class Collector( BoardObserver ):
    "Watches for annotations, collects them together into new annotations"
    # this assumes that you have some base annotations called "items" (e.g. arrow and circle annotations)
    # and that you want to find collections of these items (e.g. directed graphs) and mark them with a big annotation
    # according to some rules (e.g. graphs must be "connected" with arrows pointing to circles).
    # It also assumes that each item is a valid collection of it's own (e.g. an circle is a graph).
    # If this is the case, you just need to implement two functions, collectionFromItem and mergeCollections.
    # collectionFromItem builds a new collection of size 1 from one of the base items (or returns None).
    # mergeCollections takes two collections and merges them into one if possible.

    def __init__(self, item_annotype_list, collection_annotype):
        BoardSingleton().AddBoardObserver( self )
        for annotype in item_annotype_list:
            BoardSingleton().RegisterForAnnotation( annotype, self )
        BoardSingleton().RegisterForAnnotation( collection_annotype, self )
        self.all_collections = set([])   
        self.item_annotype_list = item_annotype_list      # types of the "items"  (e.g. CircleAnnotation, ArrowAnnotation)
        self.collection_annotype = collection_annotype    # type of the "collection" (e.g. DiGraphAnnotation)

    def onAnnotationAdded( self, strokes, annotation ):
        if type(annotation) is self.collection_annotype:
            self.all_collections.add(annotation)
        else:
            for annotype in self.item_annotype_list:
                if annotation.isType( annotype ):
                    collection = self.collectionFromItem( strokes, annotation )
                    if collection is not None:
                        self.all_collections.add( collection )
                        BoardSingleton().AnnotateStrokes( strokes, collection )
        self._merge_all_collections()

    def onAnnotationRemoved( self, annotation ):
        """Unique to collections, removing an annotation that was used to build a collection 
        results in every dependent collection being removed and rebuilt from scratch.
        ** Ordering is NOT necessarily preserved! **"""

        if( annotation in self.all_collections ):
            self.all_collections.remove( annotation )

        if type(annotation) in self.item_annotype_list:
            logger.debug("Removing collection item: rebuilding collections")
            all_item_annos = set([])
            all_collection_annos = set([])
            for s in annotation.Strokes:
                all_collection_annos.update(set(s.findAnnotations(self.collection_annotype)) )

            #For all of the collections that might depend on this annotation
            #   Get all of the item annotations that those collections might also depend on
            for col in all_collection_annos:
                for s in col.Strokes:
                    for t in self.item_annotype_list:
                        all_item_annos.update(set(s.findAnnotations(t)) )
                  

            #Remove any collections that may depend on this annotation
            for anno in all_collection_annos:
                BoardSingleton().RemoveAnnotation(anno)

            #Rebuild the annotations as needed from the remaining parts
            for anno in all_item_annos:
                if anno is not annotation:
                    self.onAnnotationAdded(anno.Strokes, anno)

            

    def _merge_all_collections( self ):
        "walk through all of the collections and merge any that should be"
        check_set = set(self.all_collections) # make a copy of the set
        while len(check_set)>0:
            from_anno = check_set.pop()
            # now iterate over the rest of the sets to find overlaps
            for to_anno in check_set:
                didmerge = self.mergeCollections( from_anno, to_anno )
                if didmerge:
                    # calculate the new set of strokes for the collection
                    new_strokes = list( set(from_anno.Strokes).union( set(to_anno.Strokes) ) )
                    # now tell the board about what is happening
                    BoardSingleton().UpdateAnnotation( to_anno, new_strokes )
                    BoardSingleton().RemoveAnnotation( from_anno )
                    # we just removed the "from" anno so we don't need to try and merge 
                    # it any more. Just pop out of this inner loop and get a new "from"
                    break

    def mergeCollections( self, from_anno, to_anno ):
        "Input: two collection anotations.  Return false if they should not be merged, otherwise merge them"
        # this should merge everything from "from_anno" into "to_anno".  to_anno will be removed from the
        # board if this function returns true.
        logger.error("failure to implement virtual method 'mergeCollections'")
        raise NotImplementedError

    def collectionFromItem( self, strokes, annotation ):
        "Input: strokes and source annotation.  Return a new collection anno from this single base item annotation"
        logger.error("failure to implement virtual method 'newCollectionAnno'")
        raise NotImplementedError

#-------------------------------------
# if executed by itself, run all the doc tests

if __name__ == "__main__":
    Logger.setDoctest(logger) 
    import doctest
    doctest.testmod()

