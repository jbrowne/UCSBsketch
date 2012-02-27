#!/usr/bin/python
"""
filename: DataManager.py

Description:
   
Todo:
   
"""

import math
import string
import sys

from Utils import Logger
from Utils import GeomUtils

from SketchFramework.Point import Point
from SketchFramework.Stroke import Stroke
from Observers import ObserverBase

from xml.etree import ElementTree as ET

import pdb

from SketchFramework import SketchGUI
from SketchFramework.Board import BoardObserver, BoardSingleton
from SketchFramework.Annotation import Annotation, AnnotatableObject


logger = Logger.getLogger('Rubine', Logger.WARN )

#------------------------------------------------------------

class Dataset():
    # top class of the data set. Containes each participant
    def __init__(self):
        """ Initiates the Dataset.
        """
        self.participants = []
        
class Participant():
    #
    def __init__(self, id):
        """ Initiates the Participant.
        """
        self.id = id # int
        self.diagrams = []

class Diagram(): 

    def __init__(self, type):
        """ Initiates the Diagram.
        """
        self.type = type # string
        self.InkStrokes = []
        self.strokeLabels = []
        self.groupLabels = []

class StrokeLabel():

    def __init__(self, id, type, color):
        """ Initiates the strokeLabel.
        """
        self.id = id # int
        self.type = type # string
        self.color = color # string

class GroupLabel(): 

    def __init__(self, type):
        """ Initiates the groupLabel.
        """
        self.type = type # string
        self.ids = []
        self.groupLabels = []
        self.boundingBox = None

class BoundingBox():

    def __init__(self, x, y, height, width):
        self.x = x 
        self.y = y
        self.height = height
        self.width = width

class InkStroke:

    def __init__(self, id, stroke):
        """ Initiates the InkStroke.
        """
        self.id = id # int 
        self.stroke = stroke # stroke
        self.label = None


def loadDataset(file):
    "Loads the dataset from the xml file"

    # parses the xml file. Takes a long time for large files
    print "Loading..."
    et = ET.parse(file).getroot()
    print "Loaded"
    
    # create the initial daata set
    dataset = Dataset()
    
    # iterate through each participant
    MyParticipants = et.find("MyParticipants").findall("MyParticipant");
    for participant in MyParticipants:
        p = Participant(int(participant.find("ID").text))
        #print p.id
        #sys.stdout.flush()
        for diagram in participant.find("MyDiagrams").findall("MyDiagram"):
            d = Diagram(diagram.find("MyTemplate").find("Name").text)
            print d.type
            sys.stdout.flush()

            for stroke in diagram.find("InkRaw").findall("Stk"):
                points = []
                for point in stroke.find("Points").findall("p"):
                    x = int(point.find("X").text)
                    y = int(point.find("Y").text)
                    points.append(Point(x,y))
                s = Stroke(points)
                iStroke = InkStroke(int(stroke.find("Id").text), s)
                d.InkStrokes.append(iStroke)

            for labels in diagram.find("MyStrokeLabels").findall("MyStrokeLabel"):
                id = int(labels.find("ID").text)
                type = labels.find("MyLabels").find("MyLabel").find("Text").text
                color = string.replace(labels.find("MyLabels").find("MyLabel").find("ColorType").text, "NamedColor:", "")
                label = StrokeLabel(id, type, color)
                d.strokeLabels.append(label)
                # find the stroke with the given label id, and add the label to the stroke
                for i in d.InkStrokes:
                    if i.id == id:
                        i.label = label

            for labels in diagram.find("MyGroupLabels").findall("MyGroupLabels"):
                label = GroupLabel(labels.find("Name").text)
                for id in labels.find("MyIDs").findall("MyIDs"):
                    label.ids.append(int(id.text))
               
                for glabels in labels.find("MyGroupLabels").findall("MyGroupLabel"):
                    type = glabels.find("Text").text
                    color = string.replace(glabels.find("ColorType").text, "NamedColor:", "")
                    # group labels do not have an id, so we just pass -1
                    d.strokeLabels.append(StrokeLabel(-1, type, color))

                bbox = labels.find("MyBoundingBoxes")
                x = int(bbox.find("X").text)
                y = int(bbox.find("Y").text)
                height = int(bbox.find("Height").text)
                width = int(bbox.find("Width").text)
                label.boundingBox = BoundingBox(x,y, 0, 0)

                d.groupLabels.append(label)

            p.diagrams.append(d)
 
        dataset.participants.append(p)
    
    return dataset

#-------------------------------------

class DataManagerAnnotation(Annotation):
    def __init__(self, text):
        "Create a Text annotation. text is the string, and scale is an appropriate size"
        Annotation.__init__(self)
        self.text = text # an approximate "size" for the text

#-------------------------------------

class DataManagerVisualizer( ObserverBase.Visualizer ):

    def __init__(self):
        ObserverBase.Visualizer.__init__( self, DataManagerAnnotation )

    def drawAnno( self, a ):
        ul,br = GeomUtils.strokelistBoundingBox( a.Strokes )
        spaceing = 5
        ul.X -= spaceing
        ul.Y += spaceing
        br.X += spaceing
        br.Y -= spaceing

        logger.debug(a.Strokes)
        height = ul.Y - br.Y
        midpointY = (ul.Y + br.Y) / 2
        midpointX = (ul.X + br.X) / 2
        left_x = midpointX - a.scale / 2.0
        right_x = midpointX + a.scale / 2.0
        SketchGUI.drawBox(ul, br, color="#a0a0a0");
        
        SketchGUI.drawText( br.X - 15, br.Y, a.text, size=15, color="#a0a0a0" )

def standAloneMain():
    "for testing"

    loadDataset("UI_Org_Graph_raw.xml")

if __name__ == '__main__':   
    standAloneMain()
 
