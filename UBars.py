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

######################################################
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

beams = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_StructuralColumns
                                                 ).WhereElementIsNotElementType().ToElements()

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


def get_parts(el):
    Id = el.Id
    a = PartUtils.GetAssociatedParts(doc, Id, True, False)
    parts = []
    for i in a:
        parts.append(doc.GetElement(i).ToDSType(True))
    # List.append(parts)
    return parts


def tolist(obj1):
    if hasattr(obj1, "__iter__"):
        return obj1
    else:
        return [obj1]


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


def rebar_create(curves, vector, Host, ReBarType, RS=RebarStyle.Standard, RHookType=None):
    UseExistingShapeIfPossible = True
    RebarHOrient = RebarHookOrientation.Left
    CreateNewShape = False

    return Rebar.CreateFromCurves(doc, RS, ReBarType, RHookType, RHookType, Host, vector, curves, RebarHOrient,
                                  RebarHOrient, UseExistingShapeIfPossible, CreateNewShape)


def get_iso_curve(face, param, Dir=0):
    return [face.ToProtoType()[0].GetIsoline(Dir, p) for p in param]


def translate_curves(curvs, vec, dist):
    return [i.ToProtoType().Translate(vec.ToVector().Reverse(), dist).ToRevitType() for i in curvs]


def get_top_bottom_face(faces):
    for face in faces:
        if face.FaceNormal[2] == 1:
            TF = face
        elif face.FaceNormal[2] == -1:
            BF = face
    return BF, TF


# join/group curves function
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
RebarDim = UnwrapElement(IN[1])
Dim = RebarDim.LookupParameter("Bar Diameter").AsDouble() * Imper
A_stirrup = IN[3]
Step = IN[2]
Rev = IN[4]

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
    #
    #
    '''Geometry'''
    WSolid = get_solids(cpart)
    WFaces = get_faces(WSolid)  # ; BFaces = flatten(BFaces)
    WEdges = WSolid[0].Edges
    Vector = WallOrientation(WallUn)
    if Rev:
        Vector = Vector.Reverse()
    #	locCurve = WallUn.Location
    #
    cover = 25
    lines, edges = get_lines(WFaces)


    #
    #
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


    def get_front_faces(Faces, Vec):
        FFaces = []
        BFaces = []
        for f in Faces:
            if f.FaceNormal.ToVector().IsAlmostEqualTo(Vec):
                FFaces.append(f.ToProtoType()[0])
            elif f.FaceNormal.ToVector().IsAlmostEqualTo(Vec.Reverse()):
                BFaces.append(f.ToProtoType()[0])

        return FFaces, BFaces


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
    #
    lines2, edges2 = get_lines([StructuralF])
    lines2PT = [l.ToProtoType() for l in lines2]


    # Gcurves = groupCurves(lines2PT)
    def get_outer_curves(curves):
        gc = groupCurves(curves)
        lengths = []
        for curves in gc:
            lengths.append(sum([c.Length for c in curves]))
        Maindex = lengths.index(max(lengths))
        return gc[Maindex]


    PCurve = PolyCurve.ByJoinedCurves(get_outer_curves(lines2PT))
    #
    CvsExpPT = PCurve.Explode()  # for width finder

    PCurve = PolyCurve.Offset(PCurve, -cover, False)
    PCNorm = PCurve.Normal
    CvsExp = PCurve.Explode();
    CvsExp = [c.ToRevitType() for c in CvsExp]


    def find_width_part(faces, curves, vec):
        ff, bf = get_front_faces(faces, vec)
        ffpc = [PolyCurve.ByJoinedCurves(get_outer_curves(f.PerimeterCurves())) for f in ff]
        bfpc = [PolyCurve.ByJoinedCurves(get_outer_curves(f.PerimeterCurves())) for f in bf]
        curves1 = flatten([ffpc, bfpc])
        abc = []
        widths = []
        for c in curves:
            dist = 10000
            pt = c.PointAtParameter(0.5)
            for c1 in curves1:
                pts = pt.Project(c1, vec)
                for pt2 in pts:
                    dist2 = pt.DistanceTo(pt2)
                    if dist2 < dist and dist2 != 0:
                        w = dist2
                        dist = dist2
            try:
                widths.append(round(w))
            except:
                widths.append(140)
        return widths


    widths = find_width_part(WFaces, CvsExpPT, Vector)
    w = Width / 2 - cover
    #
    #
    startPoint = [l.GetEndPoint(0) for l in CvsExp]
    ## First 2 points translated left and right with w
    N_vecs = [c.ToProtoType().TangentAtParameter(0.5) for c in CvsExp]
    vectors = [v1.Cross(PCNorm.Reverse()) for v1 in N_vecs]

    LeftSP = [pt.ToPoint().Translate(Vector, w) for pt in startPoint]
    RightSP = [pt.ToPoint().Translate(Vector.Reverse(), w) for pt in startPoint]
    #
    ## Second 2 points translated up with A
    LeftSPTop = [pt.Translate(vec, A_stirrup) for pt, vec in zip(LeftSP, vectors)]
    RightSPTop = [pt.Translate(vec, A_stirrup) for pt, vec in zip(RightSP, vectors)]
    #
    ## Construct lines with points
    ln1 = [Line.CreateBound(pt1.ToXyz(), pt2.ToXyz()) for pt1, pt2 in zip(LeftSP, RightSP)]
    ln2 = [Line.CreateBound(pt1.ToXyz(), pt2.ToXyz()) for pt1, pt2 in zip(LeftSP, LeftSPTop)]
    ln3 = [Line.CreateBound(pt1.ToXyz(), pt2.ToXyz()) for pt1, pt2 in zip(RightSP, RightSPTop)]
    #
    ##Group rebars
    grouped_curves = [[l1.ToProtoType(), l2.ToProtoType(), l3.ToProtoType()] for l1, l2, l3 in zip(ln1, ln2, ln3)]
    #
    #	#Create poly curve
    P_curves = [PolyCurve.ByJoinedCurves(curves) for curves in grouped_curves]
    #
    #	#Wall edge direcitons
    LnDirs = [l.Direction for l in CvsExp]
    LnLengths0 = [round(l.ToProtoType().Length) for l in CvsExp]
    LnLengths = [max(((l - 50) // Step) * Step, Step) for l in LnLengths0]

    # Rotate polycurves
    # Rotated_pcurves =  [pcurve.Rotate(spt.ToPoint(),Vector,angle) for spt,pcurve,angle in zip(startPoint,P_curves,Angles)]
    #
    #	# Translate polycurves inside the element
    Trans_pcurves0 = [pc.Translate(Vector, Width / 2) for pc in P_curves]
    #   #
    #	## Translate polycurves inside from the wall surface
    Trans_pcurves = [pc.Translate(v.ToVector(), 50) for pc, v in zip(Trans_pcurves0, LnDirs)]
    #	##Explode polycurves to get single curves
    ExpCurve = []
    for p in Trans_pcurves:
        ExpCurve.append(p.Explode())
    #	#
    rvtCurves = [[c.ToRevitType() for c in i] for i in ExpCurve]
    #	##
    #	##
    #	### Create rebar and distribution
    TransactionManager.Instance.EnsureInTransaction(doc)  # Start
    #	##
    rebars = [rebar_create(cs, v.ToVector().Reverse().ToXyz(), WallUn, RebarTypes[0], RebarStyle.Standard, None) for
              cs, v in zip(rvtCurves, LnDirs)]  #
    #	##
    for i, r in enumerate(rebars):
        r.LookupParameter("a").Set(A_stirrup / Imper)
        r.LookupParameter("b").Set((widths[i] - 2 * cover) / Imper)
        r.LookupParameter("c").Set(A_stirrup / Imper)
    #
    rebar = [r.GetShapeDrivenAccessor().SetLayoutAsMaximumSpacing(Step / Imper, l / Imper, False, True, True) for r, l
             in zip(rebars, LnLengths)]

    TransactionManager.Instance.TransactionTaskDone()  # End1

# Assign your output to the OUT variable.##
OUT = 1













