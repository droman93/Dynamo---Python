# Load the Python Standard and DesignScript Libraries
import clr

clr.AddReference("ProtoGeometry")
from Autodesk.DesignScript.Geometry import *

clr.AddReference('RevitAPI')
from Autodesk.Revit.DB import *
from Autodesk.Revit.DB.Structure import *

clr.AddReference('RevitAPIUI')
import Autodesk
from Autodesk.Revit.UI import *

ST = Autodesk.Revit.UI.Selection
clr.AddReference("RevitNodes")
clr.AddReference("RevitServices")
import RevitServices
from RevitServices.Persistence import DocumentManager

clr.AddReference("System")
from System.Collections.Generic import List
from RevitServices.Transactions import TransactionManager
import sys
import math
import Revit
from Revit.Elements import *

clr.ImportExtensions(Revit.Elements)
clr.ImportExtensions(Revit.GeometryConversion)
doc = DocumentManager.Instance.CurrentDBDocument
# The inputs to this node will be stored as a list in the IN variables.1
dataEnteringNode = IN
view0 = IN[0]
view = UnwrapElement(IN[0])
Cond = IN[3]
# Place your code below this line

Imper = 304.8

texts = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_TextNotes
                                                 ).WhereElementIsNotElementType().ToElements()

for text in texts:
    if text.Name == '2.5mm Arial':
        TextType = doc.GetElement(text.GetTypeId()).ToDSType(True)


def detail_curve(curves):
    TransactionManager.Instance.EnsureInTransaction(doc)
    elementlist = []
    for curve in curves:
        detcurve = doc.Create.NewDetailCurve(view, curve.ToRevitType())
        elementlist.append(detcurve)

    TransactionManager.Instance.TransactionTaskDone()
    return elementlist


def rebar_curve(rebar):
    AFSI = False
    sH = False
    sBH = False
    MOPT = MultiplanarOption.IncludeAllMultiplanarCurves
    bPI = 0
    return rebar.GetCenterlineCurves(AFSI, sH, sBH, MOPT, bPI)


Zaxis = XYZ(0, 0, 1).ToVector()
vector = view.ViewDirection.ToVector()
vector1 = vector.Cross(Zaxis)
# rebars in active view
# rebars = FilteredElementCollector(doc,view.Id).OfCategory(BuiltInCategory.OST_Rebar).WhereElementIsNotElementType().ToElements()


rebars = UnwrapElement(IN[2])

rebar_curves = [rebar_curve(r) for r in rebars]
rebar_curvesPT = [[i.ToProtoType() for i in j] for j in rebar_curves]

pcurves = [PolyCurve.ByJoinedCurves(cs) for cs in rebar_curvesPT]
pcurvesNs = [pc.Normal for pc in pcurves]
pcurve_orgs = [c.PointAtParameter(0.5) for c in pcurves]

anglesView = [round(v.AngleWithVector(vector)) for v in pcurvesNs]
anglesZ = [round(v.AngleWithVector(XYZ(0, 0, 1).ToVector())) for v in pcurvesNs]

new_rebars = []
new_pcs = []
rebar_nums = []
for i, pc in enumerate(pcurves):
    r = rebars[i]
    n = r.LookupParameter('Rebar Number').AsString()  ##
    if (anglesView[i] not in [0, 180]) and (anglesZ[i] in [0, 180]) and (n not in rebar_nums):
        newpc = pc.Rotate(pcurve_orgs[i], vector1, anglesView[i])
        new_pcs.append(newpc)
        new_rebars.append(r)
        rebar_nums.append(n)

    elif anglesView[i] not in [0, 180] and anglesZ[i] == 90 and n not in rebar_nums:
        newpc = pc.Rotate(pcurve_orgs[i], Zaxis, anglesView[i])
        new_pcs.append(newpc)
        new_rebars.append(r)
        rebar_nums.append(n)

    elif anglesView[i] not in [0, 180] and anglesZ[i] != 90 and n not in rebar_nums:
        newvec = vector.Cross(pcurvesNs[i])
        newpc = pc.Rotate(pcurve_orgs[i], newvec, anglesView[i])
        new_pcs.append(newpc)
        new_rebars.append(r)
        rebar_nums.append(n)

    elif anglesView[i] in [0, 180]:
        new_pcs.append(pc)
        new_rebars.append(r)

rebars = new_rebars
pcurves = [pc.Translate(Zaxis.Reverse(), 500 * d) for pc, d in zip(new_pcs, range(2, len(new_pcs) + 2))]
new_pcsNs = [pc.Normal for pc in new_pcs]

detail_curves = [pc.Explode() for pc in pcurves]

RTcurves = [[i.ToRevitType() for i in j] for j in detail_curves]

lines_no_arcs = []
for i, cs in enumerate(RTcurves):
    temp_curves = []
    for c in cs:
        if c.GetType().Name != 'Arc':
            temp_curves.append(c.ToProtoType())

    lines_no_arcs.append(temp_curves)


def place_tag(rebar, pt):
    pt = pt.Translate(Zaxis, -150)
    tag = Tag.ByElementAndLocation(view0, rebar.ToDSType(True), pt, True, False)
    return tag


angles = []


def place_text(text, pt, tangent, V):
    N = tangent.Cross(V)

    angle = round(N.AngleWithVector(Zaxis))
    angleT = round(tangent.AngleWithVector(Zaxis))
    angleV = round(V.AngleWithVector(Zaxis))
    if angle == 180:
        angle = 0
    elif angleT == 90 and angle == 0:
        angle = 0
        pt = pt.Translate(N, 85)
    elif angleT == 90 and angle != 0:
        angle = 0
    elif angle not in [0, 90, 180]:
        angles.append(angle)
        angle = 0
        pt = pt.Translate(N, 70)
    text = str(int(text / 10))
    text = "-" + text + "-"
    t = TextNote.ByLocation(view0, pt, text, "Center", TextType, False, angle)
    return t


def get_rebar_abc(rebar):
    if Cond:
        params = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'H1', 'H2']
    else:
        params = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H1', 'H2']
    ps = [rebar.LookupParameter(p) for p in params]  # .AsDouble()*Imper
    a = [round(i.AsDouble() * Imper) if i != None else 0 for i in ps]
    return a


details = [detail_curve(cs) for cs in detail_curves]


def create_list(items):
    ids = list()
    rejects = list()
    for item in items:
        try:
            ids.append(item.Id)
        except:
            rejects.append(item)
    return List[ElementId](ids)


flatten = lambda l: [item for sublist in l for item in sublist]


def unique_items(lines):
    new_list = []
    unique_lens = []
    for l in lines:
        L = round(l.Length)
        if L not in unique_lens:
            new_list.append(l)
            unique_lens.append(L)
    return new_list


#
TransactionManager.Instance.EnsureInTransaction(doc)
for i, r in enumerate(rebars):
    abc = get_rebar_abc(r)
    # abc = list(set(abc))
    temp_loc = []
    temp_values = []
    temp_vectors = []
    listLines = lines_no_arcs[i]
    # listLines = unique_items(listLines)
    while len(listLines) > 0:
        listLengths = [lin.Length for lin in listLines]
        ind = listLengths.index(max(listLengths))
        ind2 = abc.index(max(abc))
        #
        temp_loc.append(listLines[ind].PointAtParameter(0.5))
        temp_values.append(abc[ind2])
        temp_vectors.append(listLines[ind].TangentAtParameter(0.5))  #
        #
        del listLines[ind]
        del abc[ind2]
    pt = filter(lambda p: p.Z == min([i.Z for i in temp_loc]), temp_loc)[0]
    place_tag(r, pt)

    texts = UnwrapElement([place_text(t, pt, v, new_pcsNs[i]) for t, pt, v in zip(temp_values, temp_loc, temp_vectors)])

    group_items = flatten([texts, details[i]])
    group = doc.Create.NewGroup(create_list(group_items))
    group.GroupType.Name = str(r.Id)
#
#


# Assign your output to the OUT variable.1
TransactionManager.Instance.TransactionTaskDone()

# doc.Create.NewGroup()
OUT = rebar_nums  # get_rebar_abc(rebars[0])1111




























