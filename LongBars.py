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

#######################################################
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
RebarDim2 = UnwrapElement(IN[2])
Dim = RebarDim.LookupParameter("Bar Diameter").AsDouble() * Imper
SLayer_W = IN[3]
Tol_H = IN[4]
Rev = IN[5]

import time

time.sleep(3)

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

    lines2, edges2 = get_lines([StructuralF])
    lines2PT = [l.ToProtoType() for l in lines2]


    def get_outer_curves(curves):
        gc = groupCurves(curves)
        lengths = []
        for curves in gc:
            lengths.append(sum([c.Length for c in curves]))
        Maindex = lengths.index(max(lengths))
        return gc[Maindex]


    PCurve = PolyCurve.ByJoinedCurves(get_outer_curves(lines2PT))
    PCurve = PolyCurve.Offset(PCurve, -35, False)  # Transalte for cover planar
    PCurve = PCurve.Translate(Vector, 35)  # Transalte for cover inside
    PCNorm = PCurve.Normal
    CvsExp = PCurve.Explode();
    CvsExp = [c.ToRevitType() for c in CvsExp]

    w = Width / 2 - cover

    #
    #	#Create poly curve
    #	#Wall edge direcitons
    LnDirs = [l.Direction for l in lines2]
    LnLengths0 = [round(l.ToProtoType().Length) for l in lines2]


    def sort_horzs_verts(curves):
        horizontal = []
        vertical = []

        for c in curves:
            SPt = c.ToProtoType().StartPoint
            EPt = c.ToProtoType().EndPoint
            if round(SPt.Z) == round(EPt.Z):
                horizontal.append(c)
            else:
                vertical.append(c)

        return horizontal, vertical


    def sort_L_U_I(polysurface, curves):
        I_curves = []
        U_curves = []
        L_curves = []
        tol = 200

        for c in curves:
            c = c.ToProtoType()
            ctemp = c.ExtendEnd(tol)
            ctemp = ctemp.ExtendStart(tol)
            intersection = polysurface.Intersect(ctemp)

            if len(intersection) == 2:
                U_curves.append(c)
            elif len(intersection) == 1:
                L_curves.append(c)
            else:
                I_curves.append(c)
        return I_curves, U_curves, L_curves


    h_lines, v_lines = sort_horzs_verts(CvsExp)


    def extend_horzs(psurfs, curvs):
        tol = 200
        curves = []
        for c in curvs:
            c = c.ToProtoType()
            Spt = c.StartPoint
            Ept = c.EndPoint
            ipt0 = c.Extend(100, Spt).Intersect(PolySurf)
            ipt1 = c.Extend(100, Ept).Intersect(PolySurf)
            if len(ipt0) > 0 and len(ipt1) > 0:
                curves.append(c)
            elif len(ipt0) > 0 and len(ipt1) == 0:
                curves.append(c.Extend(500, Ept))
            elif len(ipt0) == 0 and len(ipt1) > 0:
                curves.append(c.Extend(500, Spt))
            else:
                c = c.Extend(500, Spt).Extend(500, Ept)
                curves.append(c)
        return curves


    def get_short_horzs(hln, hln_new, tol=700):
        ind_lns = []
        dpnd_lns = []
        for l1, l2 in zip(hln, hln_new):
            if l1.Length * Imper <= tol:
                dpnd_lns.append(l2)
            else:
                ind_lns.append(l2)

        return ind_lns, dpnd_lns


    WFacesPT = []
    for f in WFaces:
        try:
            WFacesPT.append(f.ToProtoType()[0])
        except:
            continue
    try:
        PolySurf = PolySurface.BySolid(WSolid[0].ToProtoType())
    except:
        PolySurf = PolySurface.ByJoinedSurfaces(WFacesPT)

    h_lines_new = extend_horzs(PolySurf, h_lines)
    H_lines, short_hlines = get_short_horzs(h_lines, h_lines_new, Tol_H)

    '''Sort I, U, L shapes rebars'''
    I_curvs, U_curvs, L_curvs = sort_L_U_I(PolySurf, v_lines)

    '''U shape bars curves'''
    N_vecs = [c.TangentAtParameter(0.5) for c in U_curvs]
    vectors = [v1.Cross(PCNorm.Reverse()) for v1 in N_vecs]

    extend_Spts = [c.StartPoint.Translate(v1, 700) for v1, c in zip(vectors, U_curvs)]
    extend_Epts = [c.EndPoint.Translate(v1, 700) for v1, c in zip(vectors, U_curvs)]

    ln1 = [Line.CreateBound(c.StartPoint.ToXyz(), pt.ToXyz()).ToProtoType() for c, pt in zip(U_curvs, extend_Spts)]
    ln2 = [Line.CreateBound(c.EndPoint.ToXyz(), pt.ToXyz()).ToProtoType() for c, pt in zip(U_curvs, extend_Epts)]

    ReU_rebars = [[a, b, c] for a, b, c in zip(U_curvs, ln1, ln2)]

    '''L shape bars curves'''
    N_vecs = [c.TangentAtParameter(0.5) for c in L_curvs]
    vectors = [v1.Cross(PCNorm.Reverse()) for v1 in N_vecs]

    pts = []
    pts2 = []
    for c in L_curvs:
        spt = c.StartPoint
        ept = c.EndPoint
        if len(PolySurf.Intersect(c.Extend(100, spt))) == 1:
            pts.append(spt)
            pts2.append(ept)
        else:
            pts.append(ept)
            pts2.append(spt)

    extend_pts = [pt.Translate(v1, 700) for v1, pt in zip(vectors, pts)]
    ln3 = [Line.CreateBound(pt.ToXyz(), ept.ToXyz()).ToProtoType() for pt, ept in zip(pts, extend_pts)]


    def extend_curve(pt, curve, polysurf):
        dist1 = 500
        dist2 = 500
        for pt2 in polysurf.Intersect(curve.Extend(700, pt)):
            dist2 = pt.DistanceTo(pt2)
        return curve.Extend(min(dist1, dist2 - cover), pt)


    Ext_Lcurves = [extend_curve(pt, c, PolySurf) for c, pt in zip(L_curvs, pts2)]

    ReL_rebars = [[a, b] for a, b in zip(ln3, Ext_Lcurves)]

    '''Remove short lines'''
    app_curves = flatten([ln1, ln2, ln3])
    sorted_curves = []
    for ac in app_curves:
        state = []
        for h_line in short_hlines:
            state.append(ac.DoesIntersect(h_line))
        if not any(state):
            sorted_curves.append(ac)

    grouped_curves = groupCurves(flatten([sorted_curves, short_hlines, Ext_Lcurves, U_curvs]))

    Total_rebars = []
    '''Create bars from L,U,I curves'''
    for cs in grouped_curves:
        TransactionManager.Instance.EnsureInTransaction(doc)  # Start
        try:
            PS = PolyCurve.ByJoinedCurves(cs).Explode()
        except:
            continue
        rvtCurves = [[c.ToRevitType() for c in i] for i in [PS]]
        rebars = rebar_create(rvtCurves[0], Vector.Reverse().ToXyz(), WallUn, RebarDim, RebarStyle.Standard, None)  #
        TransactionManager.Instance.TransactionTaskDone()
        rebar = rebars.GetShapeDrivenAccessor().SetLayoutAsFixedNumber(2, (SLayer_W - cover * 2) / Imper, False, True,
                                                                       True)
        Total_rebars.append(rebars)

    '''Create bars from H curves'''
    for cs in H_lines:
        TransactionManager.Instance.EnsureInTransaction(doc)  # Start

        rebars = rebar_create([cs.ToRevitType()], Vector.Reverse().ToXyz(), WallUn, RebarDim2, RebarStyle.Standard,
                              None)  #
        TransactionManager.Instance.TransactionTaskDone()
        rebar = rebars.GetShapeDrivenAccessor().SetLayoutAsFixedNumber(2, (SLayer_W - cover * 2) / Imper, False, True,
                                                                       True)
        Total_rebars.append(rebars)


    def correct_rebars(rebar):  # remove extra values from diameters
        a = r.LookupParameter("a").AsDouble() * Imper;
        b = r.LookupParameter("b").AsDouble() * Imper;
        c = r.LookupParameter("c").AsDouble() * Imper;
        Diam = doc.GetElement(r.LookupParameter("Type").AsElementId()).BarDiameter * Imper
        try:
            d = r.LookupParameter("d").AsDouble() * Imper;
            d = round(d / 10) * 10
        except:
            COND = False
            d = 0
        values = [a, b, c, d]
        state = len(values) - values.count(0)  # no zero
        if state == 1:
            rebar.LookupParameter("a").Set(round(a / 100) * 100 / Imper)

        elif state == 2:
            rebar.LookupParameter("a").Set((a - Diam / 2) / Imper)
            rebar.LookupParameter("b").Set((b - Diam / 2) / Imper)

        elif state == 3:
            rebar.LookupParameter("a").Set((a - Diam / 2) / Imper)
            rebar.LookupParameter("b").Set((b - Diam) / Imper)
            rebar.LookupParameter("c").Set((c - Diam / 2) / Imper)

        elif state == 4:
            rebar.LookupParameter("a").Set((a - Diam / 2) / Imper)
            rebar.LookupParameter("b").Set((b - Diam) / Imper)
            rebar.LookupParameter("c").Set((c - Diam) / Imper)
            rebar.LookupParameter("d").Set((d - Diam / 2) / Imper)

        return Diam


    for r in Total_rebars:
        s = correct_rebars(r)

# Assign your output to the OUT variable.
OUT = h_lines, v_lines