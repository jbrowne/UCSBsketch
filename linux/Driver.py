#!/usr/bin/env python

import cPickle as pickle
import sys
import pdb
import time
import traceback
from Utils import Rubine, Logger


DIAGNUM = 2
logger = Logger.getLogger("Driver", Logger.DEBUG)

def printUsage():
    print "Usage: %s [--train | --classify] ..." % (sys.argv[0])

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
def classifyMain(args):
    if len(args) == 2:
        #Load labeled data and train on it
        print "Loading binary stroke dataset"
        strokeData = pickle.load(open(args[0], "rb"))
        print "Loading classifier weights"

        classifier = Rubine.RubineClassifier(featureSet = Rubine.RubineFeatureSet(), debug = False)
        #classifier = Rubine.RubineClassifier(featureSet = Rubine.RubineFeatureSet(), debug = False)
        classifier.loadWeights(args[1])
        print "Classifying dataset"
        results = batchClassify(strokeData, classifier)
        resultsFile = open("Results.txt", "w")
        printResults(results, resultsFile)
        
    else:
        print "Usage: %s --classify <DataSet.p> <Classifier.xml>" % (sys.argv[0])
        exit(1)

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
def batchClassify(strokeData, classifier):
    """Given a dataset, and a classifier object, evaluate the strokes in the dataset
    and decide what they are"""
    global DIAGNUM
    logger.warn("Only using diagram # %s from each participant"% (DIAGNUM))
    outData = {'byLabel' : {},
               'overAll' : {'right' : 0, 'wrong': 0}
              }
    for participant in strokeData.participants:
        #for diagram in participant.diagrams:
        diagram = participant.diagrams[DIAGNUM]
        for label in diagram.groupLabels:
            name = label.type
            labelResults = outData['byLabel'].setdefault(name, {'right': 0, 'wrong' : 0})
            for stkID in label.ids:
                try:
                    classification = classifier.classifyStroke(diagram.InkStrokes[stkID].stroke)
                    if name == classification:
                        labelResults['right'] += 1
                        outData['overAll']['right'] += 1
                    else:
                        labelResults['wrong'] += 1
                        outData['overAll']['wrong'] += 1
                except Exception as e:
                    print traceback.format_exc()
                    print e
                    exit(1)
    return outData
    

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
def printResults(results, outfile = sys.stdout):
    print >> outfile, "Kind\tTotal\tRight\tPct_Right\tWrong\tPct_Wrong\t"
    right = results['overAll']['right']
    wrong = results['overAll']['wrong']
    total = float(right + wrong)
    if total > 0:
        print >> outfile, "Overall\t%s\t%s\t%s\t%s\t%s" % (total, right, right/total * 100, wrong, wrong/total * 100)
    for label, results in results['byLabel'].items():
        right = results['right']
        wrong = results['wrong']
        total = float(right + wrong)
        if total > 0:
            print >> outfile, "%s\t%s\t%s\t%s\t%s\t%s" % (label, total, right, right/total * 100, wrong, wrong/total * 100)
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
def batchTraining(trainer, dataSet, outfname):
    """Perform training on an entire dataset in infname, and output the results to outfname"""
    global DIAGNUM
    seenLabels = set()
    logger.warn("Only using diagram # %s from each participant"% (DIAGNUM))
    for participant in dataSet.participants:
        #for diagram in participant.diagrams:
        diagram = participant.diagrams[DIAGNUM]
        for label in diagram.groupLabels:
            if label.type not in seenLabels:
                trainer.newClass(name = label.type)
                seenLabels.add(label.type)
            for stkID in label.ids:
                try:
                    trainer.addStroke(diagram.InkStrokes[stkID].stroke, label.type)
                except Exception as e:
                    print e

    trainer.saveWeights(outfname)

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
def openDataset(infname):
    if infname.split('.')[-1] == "p":
        print "Loading binary dataset file"
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
        trainer = Rubine.RubineTrainer(featureSet = Rubine.RubineFeatureSet() )
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
    global DIAGNUM
    if len(args) > 0:
        infname = args[0]
        dataSet = openDataset(infname)
        for fsType in (Rubine.BCPFeatureSet, Rubine.RubineFeatureSet):
            featureSet = fsType()
            for i in range (3):
                DIAGNUM = i

                tag = "SymbolClass-%s_Feature-%s" % (DIAGNUM, type(featureSet).__name__)
                classifierFname = "BatchRubineData_%s.xml"%(tag)
                trainer = Rubine.RubineTrainer(featureSet = featureSet)
                classifier = Rubine.RubineClassifier(featureSet = featureSet)
                batchTraining(trainer, dataSet, classifierFname)
                classifier.loadWeights(classifierFname)
                results = batchClassify(dataSet, classifier)
                resultsFile = open("Results_%s.txt" % (tag), "w")
                printResults(results, resultsFile)
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
