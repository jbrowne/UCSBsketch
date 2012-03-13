#!/usr/bin/env python

import cPickle as pickle
import sys
import pdb
import time
import traceback
from Utils import Rubine, Logger, GeomUtils, ImageStrokeConverter, StrokeStorage
from SketchFramework.Point import *
from SketchFramework.Stroke import *


DOTRACE = False
logger = Logger.getLogger("Driver", Logger.DEBUG)

def printUsage():
    print "Usage: %s [--train | --classify] ..." % (sys.argv[0])

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
def classifyMain(args):
    if len(args) == 2:
        #Load labeled data and train on it
        logger.debug( "Loading binary stroke dataset" )
        strokeData = pickle.load(open(args[0], "rb"))
        logger.debug( "Loading classifier weights" )

        featureSet = Rubine.BCP_AllFeatureSet()
        classifier = Rubine.RubineClassifier(featureSet = featureSet, debug = False)
        #classifier = Rubine.RubineClassifier(featureSet = Rubine.RubineFeatureSet(), debug = False)
        classifier.loadWeights(args[1])
        logger.debug( "Classifying dataset" )
        results = batchClassify(strokeData, classifier)
        resultsFile = open("Results.txt", "w")
        printResults(results, resultsFile)
        
    else: 
        print "Usage: %s --classify <DataSet.p> <Classifier.xml>" % (sys.argv[0])
        exit(1)

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
def batchClassify(strokeData, classifier, diagType, resultStorage = None, classifyOnParticipants = None):
    """Given a dataset, and a classifier object, evaluate the strokes in the dataset
    and decide what they are"""
    #logger.warn("Only using diagram # %s from each participant"% (DIAGNUM))
    if resultStorage == None: 
        outData = {
                   'diagram' : diagType,
                   'classifier' : classifier.__class__.__name__,
                   'featureSet' : classifier.featureSet.__class__.__name__,
                   'byLabel' : {},
                   'byParticipant' : {},
                   'overAll' : {'right' : 0, 'wrong': 0}
                  }
    else:
        outData = resultStorage
    for participant in strokeData.participants:
        if classifyOnParticipants is None or participant.id in classifyOnParticipants:
            #for diagram in participant.diagrams:
            logger.debug( "Classifying dataset %s on participant %s" % (diagType, participant.id) )
            partResults = outData['byParticipant'].setdefault(participant.id, {'right': 0, 'wrong' : 0})
            for diagnum, diagram in enumerate(participant.diagrams):
                if diagram.type != diagType:
                    continue
                for label in diagram.groupLabels:
                    name = label.type
                    labelResults = outData['byLabel'].setdefault(name, {'right': 0, 'wrong' : 0})
                    for stkID in label.ids:
                        try:
                            stroke = diagram.InkStrokes[stkID].stroke
                            #stroke = traceStroke(stroke)
                            classification = classifier.classifyStroke(stroke)
                            if name == classification:
                                labelResults['right'] += 1
                                outData['overAll']['right'] += 1
                                partResults['right'] += 1
                                logger.debug( "O\t%s\tSID:%s\tPID:%s\tDID:%s" % (name, stkID, participant.id, diagnum) )
                            else:
                                labelResults['wrong'] += 1
                                outData['overAll']['wrong'] += 1
                                partResults['wrong'] += 1
                                logger.debug( "X\t%s<>%s\tSID:%s\tPID:%s\tDID:%s" % (classification, name, stkID, participant.id, diagnum))
                        except Exception as e:
                            print traceback.format_exc()
                            print e
                            exit(1)
            logger.debug( "\tFor participant %s: %s correct, %s wrong" % (participant.id, partResults['right'], partResults['wrong']) )
            #logger.warn("FINISHING CLASSIFY EARLY")
            #break

    return outData
    

def traceStroke(stroke):
    """Take in a true stroke with timing data, bitmap it and
    then trace the data for it"""
    #logger.debug("Stripping Timing Information from Stroke")
    #logger.debug("Stroke in, %s points" % len(stroke.Points))
    strokeLen = GeomUtils.strokeLength(stroke)
    sNorm = GeomUtils.strokeNormalizeSpacing(stroke, int(len(stroke.Points) * 1.5)) #Normalize to ten pixel spacing
    graph = {}
    #Graph structure looks like 
    #   { <point (x, y)> : {'kids' : <set of Points>, 'thickness' : <number>} }
    #Find self intersections
    intersections = {}
    for i in range(len(sNorm.Points) - 1):
        seg1 = (sNorm.Points[i], sNorm.Points[i+1])
        for j in range(i+1, len(sNorm.Points) - 1 ):
            seg2 = (sNorm.Points[j], sNorm.Points[j+1])
            cross = GeomUtils.getLinesIntersection( seg1, seg2)
            #Create a new node at the intersection
            if cross != None \
                and cross != seg1[0] \
                and cross != seg2[0]:
                    crossPt = (cross.X, cross.Y)
                    intDict = intersections.setdefault(crossPt, {'kids' : set(), 'thickness' : 1})
                    for pt in seg1 + seg2: #Add the segment endpoints as kids
                        coords = (int(pt.X), int(pt.Y))
                        if coords != crossPt:
                            intDict['kids'].add(coords)
            
    prevPt = None
    #for i in range(1, len(sNorm.Points)):
    for pt in sNorm.Points:
        curPt = (int(pt.X), int(pt.Y))
        if prevPt != None:
            #prevPt = (pt.X, pt.Y)
            graph[curPt] = {'kids' : set([prevPt]), 'thickness':1}
            graph[prevPt]['kids'].add(curPt)
        else:
            graph[curPt] = {'kids' : set(), 'thickness' :1 }
        prevPt = curPt
    for pt, ptDict in intersections.items():
        for k in graph.get(pt, {'kids' : []})['kids']:
            ptDict['kids'].add(k)
            graph[k]['kids'].add(pt)
        for k in ptDict['kids']:
            graph[k]['kids'].add(pt)
        graph[pt] = ptDict
    strokeList = ImageStrokeConverter.graphToStrokes(graph)
    if len(strokeList) > 1:
        #logger.debug("Stroke tracing split into multiple strokes")
        strokeList.sort(key=(lambda s: -len(s.points)))

    retPts = []
    
    if len(strokeList) > 0:
        for pt in strokeList[0].points:
            #logger.debug("Adding point %s" % (str(pt)))
            retPts.append(Point(pt[0], pt[1]))

    #logger.debug("Stroke out, %s points" % len(retPts))
    retStroke = Stroke(retPts)
    #saver = StrokeStorage.StrokeStorage()
    #saver.saveStrokes([stroke, retStroke])
    return retStroke
    
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
def printResults(trainIDs, classifyIDs, results, outfile = sys.stdout):
    print >> outfile, "Kind\tTotal\tRight\tPct_Right\tWrong\tPct_Wrong\t"
    featureSet = results['featureSet']
    right = results['overAll']['right']
    wrong = results['overAll']['wrong']
    total = float(right + wrong)
    if total > 0:
        print >> outfile, "%s_Overall\t%s\t%s\t%s\t%s\t%s" % (featureSet, total, right, right/total * 100, wrong, wrong/total * 100)
    for label, label_results in results['byLabel'].items():
        right = label_results['right']
        wrong = label_results['wrong']
        total = float(right + wrong)
        if total > 0:
            print >> outfile, "%s\t%s\t%s\t%s\t%s\t%s" % (label, total, right, right/total * 100, wrong, wrong/total * 100)
    #print >> outfile, "TrainingIDs:%s" % (",".join([str(i) for i in trainIDs]) )
    print >> outfile, "ClassifyIDs:%s" % (",".join([str(i) for i in results['byParticipant'].keys()]) )
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
def batchTraining(trainer, dataSet, diagType, outfname, trainOnParticipants = None ):
    """Perform training on an entire dataset in infname, and output the results to outfname.
    trainOnParticipants is a set of participant indexes to train from"""
    seenLabels = set()
    logger.warn("Only using diagram # %s from each participant"% (diagType))
    for participant in dataSet.participants:
        if trainOnParticipants is None or participant.id in trainOnParticipants:
            logger.debug( "Training from participant %s" % (participant.id) )
            #for diagram in participant.diagrams:
            for diagnum, diagram in enumerate(participant.diagrams):
                if diagram.type != diagType:
                    continue
                for label in diagram.groupLabels:
                    if label.type not in seenLabels:
                        trainer.newClass(name = label.type)
                        seenLabels.add(label.type)
                    for stkID in label.ids:
                        try:
                            stroke = diagram.InkStrokes[stkID].stroke
                            #stroke = traceStroke(stroke)
                            trainer.addStroke(stroke, label.type)
                        except Exception as e:
                            print traceback.format_exc()
                            print e
            #logger.warn("FINISHING TRAINING EARLY")
            #break

    trainer.saveWeights(outfname)

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
def openDataset(infname):
    if infname.split('.')[-1] == "p":
        logger.debug( "Loading binary dataset file" )
        import cPickle as pickle
        try:
            dataSet = pickle.load(open(infname, "rb"))
        except Exception as e:
            print "Problem loading dataset. Wrong file extension? " + e
            exit(1)
    else:
        dataSet = DataManager.loadDataset(open(infname, "r"))
    return dataSet

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
def trainingMain(args):
    if len(args) >= 1:
        infname = args[0]
        featureSet = Rubine.BCP_AllFeatureSet()
        trainer = Rubine.RubineClassifier(featureSet = featureSet)
        dataSet = openDataset(infname)

        if len(args) > 1:
            outfname = args[1]
        else:
            outfname = "BatchRubineData_%s.xml"%(time.ctime())
        batchTraining(trainer, dataSet, outfname)
    else:
        print "Usage: %s --train <Dataset.p> [classifier_out.xml]" % (sys.argv[0])
        exit(1)
        

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
def allMain(args):
    if len(args) > 0:
        infname = args[0]
        dataSet = openDataset(infname)
        allFeatureSets = { 
                        'Shapes': [Rubine.BCP_ShapeFeatureSet, Rubine.BCP_ShapeFeatureSet_Combinable],
                        'Directed graph': [Rubine.BCP_GraphFeatureSet, Rubine.BCP_GraphFeatureSet_Combinable],
                        'Class diagram' : [Rubine.BCP_ClassFeatureSet, Rubine.BCP_ClassFeatureSet_Combinable],
                      }
        for featureSetList in allFeatureSets.values():
            featureSetList.append(Rubine.BCPFeatureSet)
            featureSetList.append(Rubine.BCPFeatureSet_Combinable)

        if DOTRACE:
            traceTag = "Trage"
        else:
            traceTag = "NoTrace"
        testDiags = ['Shapes', 'Directed graph', 'Class diagram']
        if len(args) > 1:
            idx = int(args[1])
            testDiags = [testDiags[idx]]

        #allFeatureSets = 3* [[Rubine.BCPFeatureSet] ]

        #Split participants into training and evaluation groups
        trainIDs = set()
        classifyIDs = set()
        for i, participant in enumerate(dataSet.participants):
            if i % 2 == 0:
                trainIDs.add(participant.id)
            else:
                classifyIDs.add(participant.id)
            
        swapIDs = 0
        for diagType in testDiags:
            for fsType in allFeatureSets[diagType]:
            #for fsType in [Rubine.BCPFeatureSet]:
                results = None
                for swapIDs in (False, True):
                    swapTag = ""
                    if swapIDs:
                        logger.debug("Swapping IDs")
                        swapTag = "_swap"
                        trainIDs, classifyIDs = classifyIDs, trainIDs
                    featureSet = fsType()
                    tag = "Diagram-%s_Feature-%s_%s" % (diagType, type(featureSet).__name__, traceTag)
                    classifierFname = "BatchRubineData_%s.xml"%(tag)
                    classifier = Rubine.RubineClassifier(featureSet = featureSet)
                    logger.debug( "-----------------------" )
                    logger.debug( "Training classifier %s" % (type(featureSet).__name__) )
                    logger.debug( "-----------------------" )
                    batchTraining(classifier, dataSet, diagType, classifierFname, trainOnParticipants = trainIDs)
                    #classifier.loadWeights(classifierFname)
                    logger.debug( "-----------------------" )
                    logger.debug( "Classifying Dataset" )
                    logger.debug( "-----------------------" )
                    results = batchClassify(dataSet, classifier, diagType, resultStorage = results, classifyOnParticipants = classifyIDs)
                    printResults(trainIDs, classifyIDs, results, outfile = sys.stdout)
                #Save results AFTER swapping
                fname = "Results_%s.txt" % (tag)
                resultsFile = open(fname, "w")
                print >> resultsFile, fname
                logger.debug( "-----------------------" )
                logger.debug( "Printing Results to %s" % (fname) )
                logger.debug( "-----------------------" )
                printResults(trainIDs, classifyIDs, results, resultsFile)
                resultsFile.close()
    else:
        print "Usage: %s --all <Training/Testing dataset>"
        exit(1)
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#

if __name__ == "__main__":
    args = sys.argv
    if len(args) > 1:
        if args[1] == "--train":
            newArgs = args[2:]
            trainingMain(newArgs)
        elif args[1] == "--classify":
            newArgs = args[2:]
            classifyMain(newArgs)
        elif args[1] == "--all":
            newArgs = args[2:]
            allMain(newArgs)
        else:
            printUsage()
            exit(1)
    else:
        printUsage()
        exit(1)
