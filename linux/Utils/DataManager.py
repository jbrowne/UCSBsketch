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

from Observers import ObserverBase

from xml.etree import ElementTree as ET

import pdb

from SketchFramework.Annotation import Annotation, AnnotatableObject


logger = Logger.getLogger('Rubine', Logger.WARN )

#------------------------------------------------------------
class Stroke:
    COUNT = 0
    def __init__(self, points = [], id = None):
        if id is None:
            self.id = Stroke.COUNT
        else:
            self.id = id
        Stroke.COUNT = self.id + 1 #Try to avoid conflicts

        self.points = points

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
        self.InkStrokes = {} #ID: InkStroke
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
        """ Initializes the InkStroke.
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
    
    maxmaxX = maxmaxY = 0
    # iterate through each participant
    MyParticipants = et.find("MyParticipants").findall("MyParticipant");
    for participant in MyParticipants:
        p = Participant(int(participant.find("ID").text))
        #print p.id
        #sys.stdout.flush()
        for diagram in participant.find("MyDiagrams").findall("MyDiagram"):
            d = Diagram(diagram.find("MyTemplate").find("Name").text)
            maxX = maxY = 0
            print d.type
            sys.stdout.flush()

            strokeDict = {}

            for stroke in diagram.find("InkRaw").findall("Stk"):
                points = []
                
                stkId = int(stroke.find("Id").text)
                for point in stroke.find("Points").findall("p"):
                    x = int(point.find("X").text)
                    y = int(point.find("Y").text)
                    maxY = max(y, maxY)
                    maxX = max(x, maxX)
                    points.append((x,y))
                strokeDict[stkId] = points

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
                y = maxY - int(bbox.find("Y").text)
                height = int(bbox.find("Height").text)
                width = int(bbox.find("Width").text)
                label.boundingBox = BoundingBox(x,y, 0, 0)

                d.groupLabels.append(label)

            print "Diagram size: %s x %s" % (maxX, maxY)
            for stkId, points in strokeDict.items():
                for pt in points:
                    pt.Y = maxY - pt.Y
                iStroke = InkStroke(stkId, Stroke(id = stkId, points=points))
                d.InkStrokes[stkId] = iStroke

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

    def __init__(self, board):
        ObserverBase.Visualizer.__init__( self, board, DataManagerAnnotation )

    def drawAnno( self, a ):
        ul,br = GeomUtils.strokelistBoundingBox( a.Strokes )
        spaceing = 5
        ul.X -= spaceing
        ul.Y += spaceing
        br.X += spaceing
        br.Y -= spaceing

        self.getBoard().getGUI().drawBox(ul, br, color="#a0a0a0");
        self.getBoard().getGUI().drawText( br.X - 15, br.Y, a.text, size=15, color="#a0a0a0" )

def standAloneMain():
    "for testing"

    loadDataset("UI_Org_Graph_raw.xml")

if __name__ == '__main__':   
    standAloneMain()
 
