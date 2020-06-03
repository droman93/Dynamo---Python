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

clr.ImportExtensions(Revit.Elements)
clr.ImportExtensions(Revit.GeometryConversion)

#####################################################
doc = DocumentManager.Instance.CurrentDBDocument
Imper = 304.8
# Options
opt = Options()
opt.ComputeReferences = True
opt.IncludeNonVisibleObjects = False
# end Options
uidoc = DocumentManager.Instance.CurrentUIApplication.ActiveUIDocument

columns = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_StructuralColumns
                                                   ).WhereElementIsNotElementType().ToElements()

beams = FilteredElementCollector(doc).OfCategory(
    BuiltInCategory.OST_StructuralFraming).WhereElementIsNotElementType().ToElements()

RebarTypes = FilteredElementCollector(doc).OfClass(RebarBarType).ToElements()

RebarHookTypes = FilteredElementCollector(doc).OfClass(RebarHookType).ToElements()

RebarTypesNames = []
for r in RebarTypes:
    name = r.get_Parameter(BuiltInParameter.ALL_MODEL_TYPE_NAME).AsString()
    RebarTypesNames.append(name)

RebarHookTypesNames = []
for r in RebarHookTypes:
    name = r.get_Parameter(BuiltInParameter.ALL_MODEL_TYPE_NAME).AsString()
    RebarHookTypesNames.append(name)

for r, n in zip(RebarHookTypes, RebarHookTypesNames):
    if "135" in n:
        hook135 = r


def get_solids(el):
    geoms = el.get_Geometry(opt)
    solids = []
    for g in geoms:
        type = g.GetType().Name
        if type == "Solid":
            solids.append(g)
    return solids


def get_faces(solids):
    faces = []
    for solid in solids:
        fs = solid.Faces
        if fs is not None:
            for f in fs:
                if f.GetType().Name != "RevolvedFace":
                    faces.append(f)
    return faces


def get_lines(faces):
    lines = []
    edges = []
    for face in faces:
        contours = face.EdgeLoops
        for curves in contours:
            for curve in curves:
                line = curve.AsCurve()
                d_curve = line.ToProtoType()
                lines.append(line)
                edges.append(curve)
    return lines, edges


def get_g_lines(el):
    geoms = el.get_Geometry(opt)
    lines = []
    for g in geoms:
        # if isinstance(g, Line):
        type = g.GetType().Name
        if type == "Line":  # "GeometryInstance":
            lines.append(g)
    return lines


def rebar_create(curves, vector, Host, ReBarType, RS=RebarStyle.Standard, RHookType=None):
    UseExistingShapeIfPossible = True
    RebarHOrient = RebarHookOrientation.Left
    CreateNewShape = False

    return Rebar.CreateFromCurves(doc, RS, ReBarType, RHookType, RHookType, Host, vector, curves, RebarHOrient,
                                  RebarHOrient, UseExistingShapeIfPossible, CreateNewShape)


# join/group curves function
def groupCurves(Line_List):
    ignore_distance = 0.1  # Assume points this close or closer to each other are touching
    Grouped_Lines = []
    Queue = set()
    while Line_List:
        Shape = []
        Queue.add(Line_List.pop())  # Move a line from the Line_List to our queue
        while Queue:
            Current_Line = Queue.pop()
            Shape.append(Current_Line)
            for Potential_Match in Line_List:
                Points = (Potential_Match.StartPoint, Potential_Match.EndPoint)
                for P1 in Points:
                    for P2 in (Current_Line.StartPoint, Current_Line.EndPoint):
                        distance = P1.DistanceTo(P2)
                        if distance <= ignore_distance:
                            Queue.add(Potential_Match)
            Line_List = [item for item in Line_List if item not in Queue]
        Grouped_Lines.append(Shape)
    return Grouped_Lines


flatten = lambda l: [item for sublist in l for item in sublist]
# The inputs to this node will be stored as a list in the IN variables.
dataEnteringNode = IN
beams = IN[0]
clasaDuctilitate = "M"
for beam in [beams]:
    beamUn = UnwrapElement(beam)

    NbarsT = IN[3]
    NbarsB = IN[4]
    cover = 25
    # Place your code below this line

    BSolid = get_solids(beamUn)
    BFaces = get_faces(BSolid)  # ; BFaces = flatten(BFaces)
    BEdges = BSolid[0].Edges
    vector = beamUn.HandOrientation

    L = beamUn.LookupParameter("Cut Length").AsDouble() * Imper
    Beam_category = beamUn.Category.Name
    Struc_type = beamUn.StructuralType
    Facing = beamUn.FacingOrientation
    locCurve = beamUn.Location

    b = doc.GetElement(beamUn.GetTypeId()).LookupParameter("b").AsDouble() * Imper
    h = doc.GetElement(beamUn.GetTypeId()).LookupParameter("h").AsDouble() * Imper

    lcr = 1.5 * h if clasaDuctilitate == "H" else h if clasaDuctilitate == "M" else L / 4
    Step1 = round(min(h / 4, 150, 7 * 12) / 10) * 10 if clasaDuctilitate == "H" else round(
        min(h / 4, 200, 8 * 12) / 10) * 10 if clasaDuctilitate == "M" else 150
    Step2 = IN[2]

    lines, edges = get_lines(BFaces)

    Amin = 100
    for f in BFaces:
        if f.Area < Amin:
            Amin = f.Area
            mFace = f
    mFaceNormal = mFace.FaceNormal

    lines2, edges2 = get_lines([mFace])

    RebarBar = RebarTypes[1]


    def sort_curves():
        return 1


    def get_iso_curve(face, param, Dir=0):
        return [face.ToProtoType()[0].GetIsoline(Dir, p) for p in param]


    def translate_curves(curvs, vec, dist):
        return [i.ToProtoType().Translate(vec.ToVector().Reverse(), dist).ToRevitType() for i in curvs]


    def get_top_bottom_face(faces):

        BF = TF = None
        for face in faces:
            if round(face.FaceNormal[2]) == 1:
                TF = face
            elif round(face.FaceNormal[2]) == -1:
                BF = face
        return BF, TF


    # Assign your output to the OUT variable.
    listCurves = [l.ToProtoType() for l in lines2]
    P_curve = PolyCurve.ByJoinedCurves(listCurves)
    P_curve = PolyCurve.Offset(P_curve, -cover - 4, False)
    P_curve = P_curve.Explode()
    curves = [i.ToRevitType() for i in P_curve]

    c1 = translate_curves(curves, mFaceNormal, 50)
    c2 = translate_curves(curves, mFaceNormal, lcr)
    c3 = translate_curves(curves, mFaceNormal, L - lcr)

    TransactionManager.Instance.EnsureInTransaction(doc)
    rebar = rebar_create(c1, mFaceNormal, beamUn, RebarBar, RebarStyle.StirrupTie, hook135)  #
    rebar1 = rebar_create(c2, mFace.FaceNormal, beamUn, RebarBar, RebarStyle.StirrupTie, hook135)
    rebar2 = rebar_create(c3, mFace.FaceNormal, beamUn, RebarBar, RebarStyle.StirrupTie, hook135)
    ####	###	###	###	###	###	###	###	###
    rebar.GetShapeDrivenAccessor().SetLayoutAsMaximumSpacing(Step1 / Imper, (lcr - 50) / Imper, False, True, True)
    rebar1.GetShapeDrivenAccessor().SetLayoutAsMaximumSpacing(Step2 / Imper, (L - 2 * lcr) / Imper, False, True, True)
    rebar2.GetShapeDrivenAccessor().SetLayoutAsMaximumSpacing(Step1 / Imper, (lcr - 50) / Imper, False, True, True)

    BF, TF = get_top_bottom_face(BFaces)
    long_curves = BF.ToProtoType()[0].PerimeterCurves()[3]
    l_curve = BF.ToProtoType()[0].PerimeterCurves()[1]
    Vec = Vector.ByTwoPoints(long_curves.StartPoint, l_curve.EndPoint)

    long_curves = long_curves.Translate(Vec, cover + 8 + 6)
    ####long_curves = get_iso_curve(TF,[(cover+8+6)/b] )

    long_curves1 = long_curves.Translate(XYZ(0, 0, 1).ToVector(), cover + 8)
    long_curves2 = long_curves.Translate(XYZ(0, 0, 1).ToVector(), h - cover - 8)
    #
    curve1 = long_curves1.ToRevitType()
    curve2 = long_curves2.ToRevitType()

    long_vector = BFaces[1].FaceNormal.ToVector()
    rebar4 = rebar_create([curve1], Vec.ToXyz(), beamUn, RebarBar, RebarStyle.Standard, None)
    rebar5 = rebar_create([curve2], Vec.ToXyz(), beamUn, RebarBar, RebarStyle.Standard, None)
    rebar4.GetShapeDrivenAccessor().SetLayoutAsFixedNumber(NbarsB, (b - 2 * cover - 8 * 2 - 12) / Imper, True, True,
                                                           True)
    rebar5.GetShapeDrivenAccessor().SetLayoutAsFixedNumber(NbarsT, (b - 2 * cover - 8 * 2 - 12) / Imper, True, True,
                                                           True)
    TransactionManager.Instance.TransactionTaskDone()

####typeId  = ElementId.CreateDefaultRebarContainerType(doc)
######RebarContainer.Create(doc, beamUn,typeId)
#######rebar.SetLayoutAsFixedNumber(numberOfBarPositions,arrayLength,barsOnNormalSide,inclFirstBar,inclLastBar)


OUT = Vec  # get_top_bottom_face(BFaces)#h,long_curves1,long_curves2 #[i.ToProtoType().Translate(mFaceNormal.ToVector(),-3000) for i in curves] #c1,c2,c3 #lines,edges#[i.Area for i in BFaces]#[i.ToProtoType() for i in BFaces] #[#i.AsCurve() for i in BEdges]













