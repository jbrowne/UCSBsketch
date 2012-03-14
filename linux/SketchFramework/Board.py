import datetime 
import pdb 
import threading
import sys 

from SketchFramework.Stroke import Stroke
from SketchFramework.SketchGUI import DummyGUI

from Utils import Logger
from Utils import GeomUtils
from xml.etree import ElementTree as ET

logger = Logger.getLogger('Board', Logger.DEBUG )

#--------------------------------------------
class BoardException (Exception):
    """A custom exception class to handle errors within the framework"""
    def __init__(self, message):
        """input: message for the error"""
        self.message = message
    def __str__(self):
        return repr(self.message)

#--------------------------------------------
class BoardObserver(object):
    "The Board Observer Class from which all other Board Observers should be derived"
    def __init__(self, board):
        self._parentBoard = board
        self.AnnoFuncs={}
        self._targetAnnotations = None #Set by the Board with a call to "RegisterBoardObserver"
        
    def onStrokeAdded( self, stroke ):
        pass
    
    def onStrokeRemoved( self, stroke ):
        pass
    
    def onStrokeEdited( self, oldStroke, newStroke ):
        pass
    
    def onAnnotationAdded( self, obj, annotation ):
        pass

    def onAnnotationUpdated( self, annotation ):
        pass

    def onAnnotationRemoved(self, annotation):
        pass

    def onAnnotationSuggested(self, anno_type, strokelist):
        """Called when the a list of strokes are suggested to yield an annotation of type anno_type."""

    def drawMyself(self):
        pass

    def getBoard(self):
        return self._parentBoard
    def getGUI(self):
        return self._parentBoard._GUI
        

#--------------------------------------------

# TODO: Does Board really need to be a sigleton?  If we want 
#       multiple boards operating simultanously, it might be better to avoid
#       the Singleton pattern

class Board(object):
    Count = 0
    "A Object containing the Board and all of the strokes."

    def __init__(self, gui = None):
        self._id = Board.Count
        Board.Count += 1
        self.Reset()
        if gui is None:
            self._GUI = DummyGUI() #The GUI that the board observers registered to this board will be using
        else:
            self._GUI = gui

    def getID(self):
        return self._id
    def setGUI(self, gui):
        """Set the SketchGUI instance associated with this board"""
        self._GUI = gui
    def getGUI(self):   
        """Get the SketchGUI instance associated with this board"""
        return self._GUI

    def Reset(self):
        self.Strokes = [] #All the strokes on the board
        self.StrokeObservers=[] #All of the stroke observers to be called onStrokeAdded
        self.AnnoObservers={} #Dict indexed by annotation type to be called onAnnotationAdded
        self.BoardObservers=[] #Generic list of all board observers. Deprecated?
        self.AnnoTargeters = {} #Dict indexed by annotation type, to a list of board observers that add that kind of annotation
        #Ensure that we don't add something after its removal
        self._removed_annotations = {}
        self._removed_strokes = {}
        

    def xml(self):
        root = ET.Element("Board")

        root.attrib["id"] = str(self._id)
        strokes_el = ET.SubElement(root, "Strokes")
        for s in self.Strokes:
            strokes_el.append(s.xml())

        annos_el = ET.SubElement(root, "Annotations")
        for a in self.FindAnnotations():
            annos_el.append(a.xml())

        return root
        
    def AddStroke( self, newStroke ):
        "Input: Stroke newStroke.  Adds a Stroke to the board and calls any Stroke Observers as needed"
        logger.debug( "Adding Stroke: %d", newStroke.id )
        
        self.Strokes.append( newStroke )
        newStroke.setBoard(self)
        
        for so in self.StrokeObservers:
            if newStroke not in self._removed_strokes: #Nobody has removed this stroke yet
                so.onStrokeAdded( newStroke )

    def RemoveStroke( self, oldStroke ):
        "Input: Stroke oldStroke.  Removes a Stroke from the board and calls any Stroke Observers as needed"
        logger.debug( "Removing stroke %s" % (oldStroke.id) )
        

        self._removed_strokes[oldStroke] = True

        for so in self.StrokeObservers:
            so.onStrokeRemoved( oldStroke )
        if oldStroke in self.Strokes:
            self.Strokes.remove( oldStroke )
        else:
            logger.warn("Removing an unknown stroke!")
        
    def EditStroke ( self, oldStroke, newStroke ):
        "Input: Stroke oldStroke, newStroke.  Edits oldStroke to be newStroke on the board; calls any Stroke Observers as needed"
        logger.debug( "Edit stroke (FIXME: Not Fully Implemented)" );
        for so in self.StrokeObservers:
            so.onStrokeEdited( oldStroke, newStroke )
        if oldStroke in self.Strokes:
            idx = self.Strokes.index(oldStroke)
            self.Strokes[idx] = newStroke
        else:
            logger.warn("Editing a non-existant stroke!")
            
            
    def RegisterForStroke( self, strokeObserver ):
        "Input: BoardObserver stroke.  Registers with the board an Observer to be called when strokes are added"
        self.StrokeObservers.append( strokeObserver )
        if strokeObserver not in self.BoardObservers:
            raise BoardException("Trying to register unknown observer for strokes")

    def RegisterForAnnotation( self, annoType, annoObserver, funcToCall = None ):
        "Input: Type annoType, BoardObserver annoObserver, function funcToCall.  Call the observer when the matching annoation is found"
	    #  Function funcToCall Registers with the board an Observer based on an 
	    #  Annotation type.  Optional: An *additional* function to call on the observer upon annotation occurence
        if annoObserver not in self.BoardObservers:
            raise BoardException("Trying to register unknown observer for annotation %s" % (annoType.__name__))
            
        if ( annoType not in self.AnnoObservers ):
            self.AnnoObservers[annoType] = []

        if annoObserver not in self.AnnoObservers[annoType]:
            self.AnnoObservers[annoType].append( annoObserver )
            logger.debug( "Registering %s for %s", str(type(annoObserver)), str(annoType) )
        else:
            logger.warning( "%s already registered for %s", str(type(annoObserver)), str(annoType) )
            
        # TODO: can we depricate this?  Is this still actively used?
        if (funcToCall != None):
            if not hasattr(annoObserver, "AnnoFuncs"): #Cause Python does things arguably backwards and calls the child ctors before the parents..
                annoObserver.AnnoFuncs = {}
            
            if annoType not in annoObserver.AnnoFuncs:
                 annoObserver.AnnoFuncs[annoType] = funcToCall
                 print "Registering",annoObserver.__class__.__name__,".",funcToCall, "for", annoType.__name__

    def UnregisterObserver( self, annoType, annoObserver ):
        "Input: Type annoType, BoardObserver annonObserve.  remove the annObserver from the list of observers for annoType"
        if annoType in self.AnnoObservers:
            if annoObserver in self.AnnoObservers[annoType]:
	            self.AnnoObservers[annoType].remove(annoObserver)

    def IsRegisteredForAnnotation( self, annoType, annoObserver ):
        "Input: Type annoType, BoardObserver annonObserve.  return true if annoObserver is already listening for annoType"
        if ( annoType not in self.AnnoObservers ):
            return False
        if annoObserver in self.AnnoObservers[annoType]:
            return True
        else: return False
        
    def UnregisterStrokeObserver( self, observer ):
        "Input: BoardObserver observer.  Remove the observer from the list of stroke observers"
        if observer in self.StrokeObservers:
	        self.StrokeObservers.remove(observer)

    def IsRegisteredForStroke( self, observer ):
        "Input: BoardObserver observer.  return true if observer is already listening for strokes"
        if annoObserver in self.StrokeObservers:
            return True
        else: return False

    def AnnotateStrokes(self, strokes, anno):
        "Input: list of Strokes strokes, Annotation anno.  Add annotation to the set of strokes"
	    # time is used to play back stroke orderings during debug
        if not hasattr(anno, "Time"):
	    anno.Time = datetime.datetime.utcnow()
        # the annotation keeps a list of strokes it annotates
        anno.Strokes = list(strokes)
        # for each stroke, add this annotation to the list of annotations of that type for that stroke
        for s in strokes:
            annoList = s.Annotations.setdefault(type(anno), [])
            annoList.append(anno)

        # if anyone listening for this class of anno, notify them
        annoObsvrs = self.AnnoObservers.get(anno.__class__)
        if (annoObsvrs != None):
            for i in annoObsvrs:
                if anno not in self._removed_annotations: #Will fail if someone has called "RemoveAnnotation"
                    i.onAnnotationAdded(strokes, anno)

    def SuggestAnnotation(self, anno_type, strokelist):
        """Send these strokes back to whoever manages anno_type Annotations and try to get a good annotation from them"""
        logger.debug("Suggesting %s strokes be annotated with %s" % (len(strokelist), anno_type.__name__))
        obsSet = self.AnnoTargeters.get(anno_type, set())

        for observer in obsSet:
            observer.onAnnotationSuggested(anno_type, strokelist)

    def UpdateAnnotation(self, anno, new_strokes=None, notify=True, remove_empty = True ):
	"""Input: Annotation, Strokes.  Changes the annotation and alerts the correct listeners. 
       If the new strokes are empty, remove_empty determines whether to remove the annotation."""
        # if strokes are different from the old strokes then we update them too
        # if notify is False, then don't send the update notification.  This allows
        # people to perform multiple updates, and then call notify one time at the end
        # preventing everyone from being notified on every small change made
        logger.debug( "Updating Annotation: %s", str(anno) )

        # if we added or subtracted strokes, update accordingly
        old_strokes = anno.Strokes
        shouldRemove = (len(new_strokes) == 0 and remove_empty) #We still have strokes, or no strokes and we're not removing empty annos
        if new_strokes!=None:
            if new_strokes!=old_strokes:
                stroke_gone_list = list( set(old_strokes).difference(new_strokes))
                stroke_added_list = list( set(new_strokes).difference(old_strokes))
                for old_stroke in stroke_gone_list:
                    if anno in old_stroke.Annotations[anno.__class__]:
                        old_stroke.Annotations[anno.__class__].remove( anno )
                for new_stroke in stroke_added_list:
                    if anno.__class__ in new_stroke.Annotations:
                        new_stroke.Annotations[anno.__class__].append(anno)
                    else:
                        new_stroke.Annotations[anno.__class__] = [anno]
                anno.Strokes = new_strokes

            # if anyone is listening for this class of annotation, let them know we updated
            if not shouldRemove and notify and anno.__class__ in self.AnnoObservers:
                for obs in self.AnnoObservers[anno.__class__]:
                    # tell obs about the updated annotation
                    if anno not in self._removed_annotations: #Fails if someone called removeAnnotation
                        obs.onAnnotationUpdated(anno)
            elif shouldRemove:
                #The strokes are empty, so remove the annotation
                self.RemoveAnnotation(anno)
           

    def RemoveAnnotation(self, anno):
        "Input: Annotation anno.  Removes anno from the board and alert the correct listeners"
        logger.debug( "Removing Annotation: %s", str(anno) )

        self._removed_annotations[anno] = True
        
        # if anyone is listening for this class of annotation, let them know
        if anno.__class__ in self.AnnoObservers:
            for obs in self.AnnoObservers[anno.__class__]:
                obs.onAnnotationRemoved(anno)
        # remove the annotation from the strokes. 
        # do this second, since observers may need to check the old strokes' properties
        for stroke in anno.Strokes:
            # logger.debug("RemoveAnnotation: stroke.Annotations = %s, id=%d", stroke.Annotations, stroke.id )
            # logger.debug("RemoveAnnotation: anno.__class__ = %s", anno.__class__ )
            try:
                stroke.Annotations[anno.__class__].remove(anno)
                #if len(stroke.Annotations[anno.__class__]) == 0:
                #    del(stroke.Annotations[anno.__class__]) #Delete the entry if it's empty
            except KeyError:
                logger.error( "RemoveAnnotation: Annotation %s not found in stroke.Annotations", anno.__class__ )
            except ValueError:
                logger.error( "RemoveAnnotation: Trying to remove nonexistant annotation %s", anno  )
            
    def AddBoardObserver ( self, obs, targetAnnoList ):
        "Input: Observer obs.  Obs is added to the list of Board Observers"
        # FIXME? should we check that the object is one in the list once?
        if obs not in self.BoardObservers:
            logger.debug( "Adding Observer: %s", str(obs.__class__.__name__) )
            self.BoardObservers.append( obs )

        #Note that this observer adds these kinds of annotations
        for anno_type in targetAnnoList:
            obsSet = self.AnnoTargeters.setdefault(anno_type, set())
            obsSet.add(obs)


    def RemoveBoardObserver( self, obs):
        "Input: Observer obs.  Obs is removed from the list of Board Observers"
        while obs in self.BoardObservers:
            self.BoardObservers.remove(obs)

    def GetBoardObservers ( self, type=None):
        "Gets the board objects of type. If no type is specified, all board objects are returned"
        if type == None:
            return self.BoardObservers
        else:
            retlist = []
            for obj in self.BoardObservers:
                if obj.__class__ == type:
                    retlist.append(obj)
            return retlist

    def FindAnnotations( self, location=None, radius=None, strokelist = None, anno_type = None):
        anno_set = set()
        if strokelist is None:
            stroke_list = self.FindStrokes(location, radius )
        else:
            stroke_list = strokelist
        for s in stroke_list:
            anno_set.update(s.findAnnotations(annoType = anno_type))
            # keep a set to avoid adding annotations redundantly
        return list(anno_set)

    #FIXME: I think FindStrokes would be better if it returned any stroke that had any points
    #       in the query region?  Much more computationally expensive, but much more useful?
    def FindStrokes( self, location=None, radius=None ):
        "Input: Point location, int/double radius. Searches for Strokes on the board within the location and radius. Radius of -1 means find all strokes."
        if location != None:
            x,y = location.X, location.Y
        else:
            x = y = 0

	# find all the strokes that have a center point within radius of given location
        stroke_list = []
        for s in self.Strokes:
            isStroke = isinstance(s, Stroke)  # FIXME: this looks a little weird? 
            if isStroke and (radius==None or PointDistance(s.X,s.Y,x,y) < radius): 
                stroke_list.append(s)
        return stroke_list
                
#--------------------------------------------

