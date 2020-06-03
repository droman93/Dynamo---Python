import clr
import math

clr.AddReference('RevitAPI')
from Autodesk.Revit.DB import *
import itertools

clr.AddReference('RevitNodes')
import Revit
from Autodesk.Revit.Creation import *

clr.ImportExtensions(Revit.GeometryConversion)
clr.ImportExtensions(Revit.Elements)
clr.AddReference('ProtoGeometry')
import Autodesk

DVector = Autodesk.DesignScript.Geometry.Vector
clr.AddReference('RevitServices')
import RevitServices
from RevitServices.Persistence import DocumentManager
from RevitServices.Transactions import TransactionManager
from operator import itemgetter

clr.AddReference("RevitAPIUI")
import Autodesk
from Autodesk.Revit.UI import *
from Autodesk.Revit.UI.Selection import *

doc = DocumentManager.Instance.CurrentDBDocument
# The inputs to this node will be stored as a list in the IN variables.
dataEnteringNode = IN

# Place your code below this line

assemblies = FilteredElementCollector(doc).OfCategory(
    BuiltInCategory.OST_Assemblies).WhereElementIsNotElementType().ToElements()

# Assign your output to the OUT variable.

sheets = FilteredElementCollector(doc).OfCategory(
    BuiltInCategory.OST_Sheets).WhereElementIsNotElementType().ToElements()


def tolist(obj1):
    if hasattr(obj1, "__iter__"):
        return obj1
    else:
        return [obj1]


sheets = tolist(sheets)
# ids = assemblies[0].GetMemberIds()

Toggle = IN[0]
Extra = UnwrapElement(IN[1])

if Extra == "":
    Extra_text = Extra
else:
    Extra_text = Extra + " - "

T_cofraj = Extra_text + "Cofraj panou soclu tip"
T_armare = Extra_text + "Armare panou soclu tip"
T_plase = Extra_text + "Dispunere plase sudate panou soclu tip"

# TitluPl = T_cofraj+" "+aName


cofraje = []
ids = []
for assembly in assemblies:
    aid = assembly.Id
    aName = assembly.Name
    if Toggle:
        Pname = " " + aName
    else:
        Pname = ""
    TransactionManager.Instance.EnsureInTransaction(doc)
    for sheet in sheets:

        if sheet.AssociatedAssemblyInstanceId == aid and "ofraj" in sheet.Name:
            cofraje.append(sheet)
            TitluPl = T_cofraj + " " + aName
            NrPlanC = 'R-{}-{}c'.format(aName[0:2], aName[2:])

            t = sheet.LookupParameter('Sheet Name')
            t.Set(TitluPl)

            n = sheet.LookupParameter('Sheet Number')
            n.Set(NrPlanC)


        elif sheet.AssociatedAssemblyInstanceId == aid and "Armare" in sheet.Name:
            TitluPl = T_armare + " " + aName
            NrPlanA = 'R-{}-{}a'.format(aName[0:2], aName[2:])

            t = sheet.LookupParameter('Sheet Name')
            t.Set(TitluPl)

            n = sheet.LookupParameter('Sheet Number')
            n.Set(NrPlanA)

        elif sheet.AssociatedAssemblyInstanceId == aid and " sudate" in sheet.Name:
            TitluPl = T_plase + " " + aName
            NrPlanB = 'R-{}-{}b'.format(aName[0:2], aName[2:])

            t = sheet.LookupParameter('Sheet Name')
            t.Set(TitluPl)

            n = sheet.LookupParameter('Sheet Number')
            n.Set(NrPlanB)

    TransactionManager.Instance.TransactionTaskDone()
OUT = 1