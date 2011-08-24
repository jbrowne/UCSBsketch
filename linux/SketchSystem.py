#!/usr/bin/python
"""
filename: SketchSystem.py

Description:
   This is the root program that loads everything necessary to run the Sketch application.
   Within the main function, it either runs WebMain to output drawing strings to a web server
   or StandaloneMain to load a Tkinter interface on the local machine.

   Initialization of all the observers should occur in Initialize, since multiple initializations
   of the same observer may lead to multiple instances of that observer modifying board objects.

Todo:
   Consolidate all interface code into the SketchGUI module so that the interface can be swapped
   out by just changing that file.
"""

import sys


from Observers import CircleObserver
from Observers import LineObserver
from Observers import ArrowObserver
from Observers import DiGraphObserver
from Observers import TextObserver
from Observers import DebugObserver
from Observers import TemplateObserver
from Observers import TuringMachineObserver


def initialize(Board):
    " This function calls the board and board observer initialization code. Interface code should import this function"

    Board.Reset()

    
    CircleObserver.CircleMarker()
    #CircleObserver.CircleVisualizer()
    ArrowObserver.ArrowMarker()
    ArrowObserver.ArrowVisualizer()
    #LineObserver.LineMarker()
    #LineObserver.LineVisualizer()
    TextObserver.TextCollector()
    TextObserver.TextVisualizer()
    DiGraphObserver.DiGraphMarker()
    DiGraphObserver.DiGraphVisualizer()
    DiGraphObserver.DiGraphExporter()
    TuringMachineObserver.TuringMachineCollector()
    
    #TemplateObserver.TemplateMarker()
    #TemplateObserver.TemplateVisualizer()
    
    
    d = DebugObserver.DebugObserver()
    #d.trackAnnotation(MSAxesObserver.LabelMenuAnnotation)
    #d.trackAnnotation(MSAxesObserver.LegendAnnotation)
    #d.trackAnnotation(LineObserver.LineAnnotation)
    #d.trackAnnotation(ArrowObserver.ArrowAnnotation)
    #d.trackAnnotation(MSAxesObserver.AxesAnnotation)
    #d.trackAnnotation(TemplateObserver.TemplateAnnotation)
    #d.trackAnnotation(CircleObserver.CircleAnnotation)
    
    #d.trackAnnotation(TuringMachineObserver.TuringMachineAnnotation)
    d.trackAnnotation(DiGraphObserver.DiGraphAnnotation)
    #d.trackAnnotation(TextObserver.TextAnnotation)
    #d.trackAnnotation(BarAnnotation)
    

def standAloneMain():
    "Sets up the SketchGUI interface on the local machine"
    from SketchFramework import TkSketchGUI as GUI
    #GUI.LoadApp()
    GUI.run()

if __name__ == '__main__':   
    standAloneMain()
 
