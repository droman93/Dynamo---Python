# Copyright(c) 2015, Konrad K Sobon
# @arch_laboratory, http://archi-lab.net
import os
import re
import clr

clr.AddReference('ProtoGeometry')
from Autodesk.DesignScript.Geometry import *

# Import Element wrapper extension methods
clr.AddReference("RevitNodes")
import Revit

clr.ImportExtensions(Revit.Elements)

# Import geometry conversion extension methods
clr.ImportExtensions(Revit.GeometryConversion)

# Import DocumentManager and TransactionManager
clr.AddReference("RevitServices")
import RevitServices
from RevitServices.Persistence import DocumentManager
from RevitServices.Transactions import TransactionManager

doc = DocumentManager.Instance.CurrentDBDocument
uiapp = DocumentManager.Instance.CurrentUIApplication
app = uiapp.Application

# Import RevitAPI
clr.AddReference("RevitAPI")
import Autodesk
from Autodesk.Revit.DB import *

import sys

pyt_path = r'C:\Program Files (x86)\IronPython 2.7\Lib'
sys.path.append(pyt_path)
import System

# The inputs to this node will be stored as a list in the IN variable.
dataEnteringNode = IN

sheets = IN[0]
printSetting = UnwrapElement(IN[1])
filePath = IN[2]
printerName = IN[3]

pRange = Autodesk.Revit.DB.PrintRange.Select
combined = False
runIt = IN[4]
actualPath = IN[5]
Word = IN[6]
if isinstance(sheets, list):
    viewSheets = []
    for i in sheets:
        viewSheets.append(UnwrapElement(i))
else:
    viewSheets = UnwrapElement(sheets)


def PrintView(doc, sheet, pRange, printerName, combined, filePath, printSetting):
    # create view set
    viewSet = ViewSet()
    viewSet.Insert(sheet)
    # determine print range
    printManager = doc.PrintManager
    printManager.PrintRange = pRange
    printManager.Apply()
    # make new view set current
    viewSheetSetting = printManager.ViewSheetSetting
    viewSheetSetting.CurrentViewSheetSet.Views = viewSet
    # set printer
    printManager.SelectNewPrintDriver(printerName)
    printManager.Apply()
    # set combined and print to file
    if printManager.IsVirtual:
        printManager.CombinedFile = combined
        printManager.Apply()
        printManager.PrintToFile = True
        printManager.Apply()
    else:
        # printManager.CombinedFile = combined
        printManager.Apply()
        printManager.PrintToFile = False
        printManager.Apply()
    # set file path
    printManager.PrintToFileName = filePath
    printManager.Apply()
    # apply print setting

    printSetup = printManager.PrintSetup
    printSetup.CurrentPrintSetting = printSetting
    printManager.Apply()

    # save settings and submit print
    TransactionManager.Instance.EnsureInTransaction(doc)
    viewSheetSetting.SaveAs("tempSetName")
    printManager.Apply()
    printManager.SubmitPrint()
    viewSheetSetting.Delete()
    TransactionManager.Instance.TransactionTaskDone()

    return True


# try:
#	viewSets = FilteredElementCollector(doc).OfClass(ViewSheetSet)
#	for i in viewSets:
#		if i.Name == "tempSetName":
#			TransactionManager.Instance.EnsureInTransaction(doc)
#			doc.Delete(i.Id)
#			TransactionManager.Instance.ForceCloseTransaction()
#		else:
#			continue
#
#	errorReport = None
#	message = "Success"
if runIt:
    for set in sheets:
        set = UnwrapElement(set)
        for sheet in set['Sheets']:
            PrintView(doc, sheet, pRange, printerName, combined, filePath + "\\test.pdf", printSetting)
##	else:
#		message = "Set RunIt to True"
# except:
#	# if error accurs anywhere in the process catch it
#	import traceback
#	errorReport = traceback.format_exc()


# Word = 'Hala incubat 9-12, 13-16'
Extra = " - " + Word if len(Word) > 0 else ''


def rename(files):
    for file in files:
        currentFileName = filePath + "\\" + file

        r = re.compile("tip \d\d\d\d")
        Number = r.findall(currentFileName)[0][-4:]

        r = re.compile("R-2\d-\d\d\w")
        nr = r.findall(currentFileName)[0]
        if "Cofraj" in currentFileName:
            N = Extra + " - Cofraj panou soclu tip " + Number
            newFileName = actualPath + "\\" + nr + N + '.pdf'
            os.rename(currentFileName, newFileName)

        elif "Armare" in currentFileName:
            N = Extra + " - Armare panou tip " + Number
            newFileName = actualPath + "\\" + nr + N + '.pdf'
            os.rename(currentFileName, newFileName)

        elif "plase" in currentFileName:
            N = Extra + " - Armare cu plase panou tip " + Number
            newFileName = actualPath + "\\" + nr + N + '.pdf'
            os.rename(currentFileName, newFileName)
    return 1


import time

time.sleep(5)
files = os.listdir(filePath)
rename(files)

OUT = files

##Assign your output to the OUT variable
# if errorReport == None:
#	OUT = message
# else:
#	OUT = errorReport