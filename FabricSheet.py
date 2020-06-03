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

# FAreas = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_FabricAreas
# ).WhereElementIsNotElementType().ToElements()

# FAreas =  FilteredElementCollector(doc).OfClass(FabricArea).ToElements()

FRein = FilteredElementCollector(doc).OfClass(FabricSheet).ToElements()

# AtypeId = FAreas[0].GetTypeId()

FReinNames = []
for fr in FRein:
    FReinNames.append(fr.Name)
    if fr.Name == "111GQ 196":
        S196 = fr.GetTypeId()
    elif fr.Name == "116GQ 283":
        S283 = fr.GetTypeId()


def WallOrientation(wall):
    loc = wall.Location
    flipped = False
    if hasattr(loc, "Curve"):
        lcurve = loc.Curve
        if hasattr(wall, "Flipped"): flipped = wall.Flipped
        if str(lcurve.GetType()) == "Autodesk.Revit.DB.Line":
            if flipped:
                return wall.Orientation.ToVector().Reverse()
            else:
                return wall.Orientation.ToVector()
        else:
            direction = (lcurve.GetEndPoint(1) - lcurve.GetEndPoint(0)).Normalize()
            if flipped:
                return XYZ.BasisZ.CrossProduct(direction).ToVector().Reverse()
            else:
                return XYZ.BasisZ.CrossProduct(direction).ToVector()
    else:
        return None


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


def translate_curves(curvs, vec, dist):
    return [i.ToProtoType().Translate(vec.ToVector().Reverse(), dist).ToRevitType() for i in curvs]


def get_top_bottom_face(faces):
    for face in faces:
        if face.FaceNormal[2] == 1:
            TF = face
        elif face.FaceNormal[2] == -1:
            BF = face
    return BF, TF


def groupCurves(Line_List):
    tempList = []
    if isinstance(Line_List, list):
        print('nice')
    else:
        tempList = [c for c in Line_List]
        Line_List = tempList

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
walls, parts = UnwrapElement(IN[0])

Rev = IN[2]
SLayerW = IN[1]

import time

time.sleep(6)

for Wall, cpart in zip(walls, parts):
    # ids = Assembly.GetMemberIds()
    #
    # Parts = []
    # for id in ids:
    #	el = doc.GetElement(id)
    #	category = el.Category.Name
    #	if category=="Walls":
    #		Wall = el
    #	elif category=="Parts":
    #		Parts.append(el)
    #
    # def get_wall(part):
    #	Wall = None
    #	cond = True
    #	k = 0
    #	temp = part
    #	while cond:
    #		id = temp.GetSourceElementIds()[0].HostElementId
    #		el = doc.GetElement(id)
    #		temp = el
    #		category = el.Category.Name
    #		k += 1
    #		if category=="Walls":
    #			Wall = el
    #			break
    #		elif k>100:
    #			break
    #	return Wall
    #
    # MaxVolume = 0
    # for p in Parts:
    #	V = get_solids(p)[0].ToProtoType().Volume
    #	if V>MaxVolume:
    #		MaxVolume=V
    #		cpart = p
    #	#
    # Wall = 	get_wall(cpart)
    WallUn = UnwrapElement(Wall)
    Width = UnitUtils.ConvertFromInternalUnits(WallUn.Width, DisplayUnitType.DUT_MILLIMETERS)  # wall width
    #

    '''Geometry'''
    WSolid = get_solids(cpart)
    WFaces = get_faces(WSolid)  # ; BFaces = flatten(BFaces)
    WEdges = WSolid[0].Edges
    Vector = WallOrientation(WallUn)
    locCurve = WallUn.Location
    if Rev:
        Vector = Vector.Reverse()
    cover = 25
    lines, edges = get_lines(WFaces)


    def get_furthest(pt, Faces, vec):
        dist = 0

        for f in Faces:
            pl = Plane.CreateByNormalAndOrigin(f.FaceNormal, f.Origin)
            ProjectPt = pt.Project(pl.ToPlane(), vec)
            for p in ProjectPt:
                d = p.DistanceTo(pt)
                if d >= dist:
                    dist = d
                    F = f
        return F


    def get_front_back_faces(Faces, Solid, Vec):
        FFaces = []
        BFaces = []
        try:
            pt = Solid.ToProtoType().Centroid()
        except:
            pt = Solid.ComputeCentroid().ToPoint()
        for f in Faces:
            if f.FaceNormal.ToVector().IsAlmostEqualTo(Vec):
                FFaces.append(f)
            elif f.FaceNormal.ToVector().IsAlmostEqualTo(Vec.Reverse()):
                BFaces.append(f)

        FF = get_furthest(pt, FFaces, Vec)
        BF = get_furthest(pt, BFaces, Vec.Reverse())
        return FF, BF


    FacadeF, StructuralF = get_front_back_faces(WFaces, WSolid[0], Vector)
    StrucFaNorm = StructuralF.FaceNormal.ToVector()
    org = StructuralF.Origin


    def get_curves_from_face(face):
        lines2, edges2 = get_lines([face])
        lines2PT = [l.ToProtoType() for l in lines2]
        PCurve = PolyCurve.ByJoinedCurves(lines2PT)
        PCurve = PolyCurve.Offset(PCurve, -cover, False)  # Transalte for cover planar
        PCurve = PCurve.Translate(Vector.Reverse(), cover)  # Transalte for cover inside
        PCNorm = PCurve.Normal
        CvsExp = PCurve.Explode();
        CvsExp = [c.ToRevitType() for c in CvsExp]
        return CvsExp


    w = Width / 2 - cover

    CLoopF = CurveLoop()
    [CLoopF.Append(c) for c in get_curves_from_face(FacadeF)]
    #
    CLoopS = CurveLoop()
    [CLoopS.Append(c) for c in get_curves_from_face(StructuralF)]

    MDir = Vector.Cross(XYZ(0, 0, 1).ToVector()).ToXyz()


    def create_fabric_area(host, curves, dir, origin, AId, SId):
        return FabricArea.Create(doc, host, curves, dir, origin, AId, SId)


    def set_comment_append_assembly(fabric_area, comm):
        TransactionManager.Instance.EnsureInTransaction(doc)
        sheets = []
        ids = fabric_area.GetFabricSheetElementIds()
        for id in ids:
            el = doc.GetElement(id)
            el.LookupParameter("Comments").Set(comm)
        # assembly.AddMemberIds(ids)
        TransactionManager.Instance.TransactionTaskDone()
        return True


    TransactionManager.Instance.EnsureInTransaction(doc)  # Start
    defaultAreaReinforcementTypeId = doc.GetDefaultElementTypeId(ElementTypeGroup.FabricAreaType)

    rebar_rez1 = create_fabric_area(WallUn, [CLoopS], MDir, org, defaultAreaReinforcementTypeId, S196)
    rebar_rez1.FabricLocation = FabricLocation.BottomOrInternal

    #
    rebar_rez2 = create_fabric_area(WallUn, [CLoopS], MDir, org, defaultAreaReinforcementTypeId, S283)
    rebar_rez2.LookupParameter("Additional Cover Offset").Set((SLayerW - 2 * cover) / Imper)
    rebar_rez2.FabricLocation = FabricLocation.BottomOrInternal

    #
    rebar_fac = create_fabric_area(WallUn, [CLoopF], MDir, org, defaultAreaReinforcementTypeId, S283)
    TransactionManager.Instance.TransactionTaskDone()
    TransactionManager.Instance.ForceCloseTransaction()

    r1 = set_comment_append_assembly(rebar_rez1, 'Rezistenta')
    r2 = set_comment_append_assembly(rebar_rez2, 'Rezistenta')
    f1 = set_comment_append_assembly(rebar_fac, 'Fatada')

OUT = 1










