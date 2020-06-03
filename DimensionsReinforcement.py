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
from Autodesk.Revit.DB.Structure import *
from Autodesk.Revit.DB import *

clr.AddReference("System")
from System.Collections.Generic import List

uidoc = DocumentManager.Instance.CurrentUIApplication.ActiveUIDocument

doc = DocumentManager.Instance.CurrentDBDocument

datum = DatumExtentType.ViewSpecific
opt = Options()
opt.ComputeReferences = True
opt.IncludeNonVisibleObjects = False
# opt.View = view
refcenterfrontback = FamilyInstanceReferenceType.CenterFrontBack
refcenterleftright = FamilyInstanceReferenceType.CenterLeftRight
refcentertopdown = FamilyInstanceReferenceType.CenterElevation

# -------------------------------------------------
ST = Autodesk.Revit.DB.Structure
stype = ST.StructuralType.NonStructural
# -----------Pick type based on name------------------


type1 = None
types = FilteredElementCollector(doc).OfCategory(
    BuiltInCategory.OST_MultiReferenceAnnotations).WhereElementIsElementType().ToElements()
NAMS = []
t1 = "Bare distribuite"
for t in types:
    name = t.get_Parameter(BuiltInParameter.ALL_MODEL_TYPE_NAME).AsString()
    NAMS.append(name)
    if t1 == name:
        type1 = t


#
#

def get_fam_name(el):
    return el.get_Parameter(BuiltInParameter.ELEM_FAMILY_PARAM).AsValueString()


def get_type_name(el):
    return el.get_Parameter(BuiltInParameter.ELEM_TYPE_PARAM).AsValueString()


def get_type_id(el):
    return el.get_Parameter(BuiltInParameter.ELEM_TYPE_PARAM).AsElementId()


def get_type_el(type_id):
    return doc.GetElement(type_id)


def get_solids(el):
    geoms = el.get_Geometry(opt)
    solids = []
    for g in geoms:
        type = g.GetType().Name
        if type == "Solid":
            solids.append(g)
    return solids


def get_g_lines(el):
    geoms = el.get_Geometry(opt)
    lines = []
    for g in geoms:
        # if isinstance(g, Line):
        type = g.GetType().Name
        if type == "Line":  # "GeometryInstance":
            lines.append(g)
    return lines


def get_front_faces(solids, orient):
    faces = []
    for solid in solids:
        fs = solid.Faces
        if fs is not None:
            for f in fs:
                try:
                    normal = f.FaceNormal
                    if round(normal.X) == round(orient.X) and round(normal.Y) == -round(orient.Y):
                        faces.append(f)
                except:
                    0
    A = 0
    for f in faces:
        if f.Area > A:
            F = f
            A = f.Area
    return F


def get_lines(faces):
    lines = []
    edges = []
    for face in [faces]:
        contours = face.EdgeLoops
        for curves in contours:
            for curve in curves:
                line = curve.AsCurve()
                d_curve = line.ToProtoType()
                lines.append(line)
                edges.append(curve)
    return lines, edges


def get_relative_coord(loc, orient1, pt2):
    pt1 = loc
    x1 = pt1.X
    y1 = pt1.Y
    z1 = pt1.Z
    x2 = pt2.X
    y2 = pt2.Y
    z2 = pt2.Z
    a = math.radians(get_angle(orient1))
    dx = (x2 - x1) * math.cos(a) + (y2 - y1) * math.sin(a)
    dy = -(x2 - x1) * math.sin(a) + (y2 - y1) * math.cos(a)
    dz = z2 - z1
    new_pt = XYZ(dx, dy, dz)
    return new_pt


def get_true_coord(loc, orient1, pt2):
    pt1 = loc
    x1 = pt1.X
    y1 = pt1.Y
    z1 = pt1.Z
    dx = pt2.X
    dy = pt2.Y
    dz = pt2.Z
    a = math.radians(get_angle(XYZ(orient1.X, orient1.Y, orient1.Z)))
    x2 = dx * math.cos(a) - dy * math.sin(a) + x1
    y2 = dx * math.sin(a) + dy * math.cos(a) + y1
    z2 = dz + z1
    new_pt = XYZ(x2, y2, z2)
    return new_pt


def get_angle(a):
    x1 = a.X
    y1 = a.Y
    a1 = DVector.ByCoordinates(x1, y1, 0)
    angle = 360 - DVector.AngleAboutAxis(a1, DVector.XAxis(), DVector.ZAxis())
    return angle


def get_relative_lines(lines, orient1):  # creates a line with relative pts
    lines2 = []
    edges2 = []
    i = 0
    for line in lines[0]:
        pt1 = line.GetEndPoint(0)
        pt2 = line.GetEndPoint(1)
        new_pt1 = get_relative_coord(loc, orient1, pt1)
        new_pt2 = get_relative_coord(loc, orient1, pt2)
        new_line = Line.CreateBound(new_pt1, new_pt2)
        lines2.append(new_line)  # .ToProtoType())
        edges2.append(lines[1][i])
        i = i + 1
    return lines2, edges2


def get_bottom_line(lines2):
    bot_line = None
    bot_edge = None
    i = 0
    min_Z = 10000
    for line in lines2[0]:
        pt1 = line.GetEndPoint(0)
        pt2 = line.GetEndPoint(1)
        if pt1.Z == pt2.Z and pt1.Z < min_Z:
            min_Z = pt1.Z
            bot_line = line
            bot_edge = lines2[1][i]
        i = i + 1
    return bot_line, bot_edge


def get_left_line(lines2):
    left_line = None
    left_edge = None
    i = 0
    min_x = 10000
    for line in lines2[0]:
        pt1 = line.GetEndPoint(0)
        pt2 = line.GetEndPoint(1)
        if pt1.X == pt2.X and pt1.X < min_x:
            min_x = pt1.X
            left_line = line
            left_edge = lines2[1][i]
        i = i + 1
    return left_line, left_edge


def get_right_line(lines2):
    right_line = None
    right_edge = None
    i = 0
    max_x = 0
    for line in lines2[0]:
        pt1 = line.GetEndPoint(0)
        pt2 = line.GetEndPoint(1)
        if round(pt1.X) == round(pt2.X) and pt1.X > max_x:
            max_x = pt1.X
            right_line = line
            right_edge = lines2[1][i]
        i = i + 1
    return right_line, right_edge


def get_top_line(lines2):
    top_line = None
    top_edge = None
    i = 0
    max_Z = -10000
    for line in lines2[0]:
        pt1 = line.GetEndPoint(0)
        pt2 = line.GetEndPoint(1)
        if round(pt1.Z) == round(pt2.Z) and pt1.Z > max_Z:
            max_Z = pt1.Z
            top_line = line
            top_edge = lines2[1][i]
        i = i + 1
    return top_line, top_edge


def get_vertical_lines(lines2):
    lines = []
    edges = []
    i = 0
    max_x = 0
    list_x = []
    for line in lines2[0]:
        pt1 = line.GetEndPoint(0)
        pt2 = line.GetEndPoint(1)
        x1 = round(pt1.X, 2)
        x2 = round(pt2.X, 2)
        if x1 == x2 and lines2[1][i].ApproximateLength > 1 and x1 not in list_x:
            lines.append(line)
            edges.append(lines2[1][i])
            list_x.append(x1)
        i = i + 1
    return lines, edges


def get_refs(lines):
    refs = ReferenceArray()
    for line in lines:
        try:
            ref = line.Reference
        except:
            ref = line
        refs.Append(ref)
    return refs


def create_dim_h(view, lines, dz):
    refs = get_refs(lines[1])
    y = lines[0][0].GetEndPoint(0).Y
    pt1 = XYZ(-100, -y, dz / 304.8)
    new_pt1 = get_true_coord(loc, orient1, pt1)
    pt2 = XYZ(100, -y, dz / 304.8)
    new_pt2 = get_true_coord(loc, orient1, pt2)
    ln1 = Line.CreateBound(new_pt1, new_pt2)
    dim = doc.Create.NewDimension(view, ln1, refs)
    return dim


def endPoint(curve):
    return curve.GetEndPoint(1)


def joinCurves(list):
    curves = list
    comp = []
    re = []
    unjoined = []
    for c in curves:
        c = c.ToRevitType()
        match = False
        for co in comp:
            if startPoint(c).IsAlmostEqualTo(startPoint(co)) and endPoint(c).IsAlmostEqualTo(endPoint(co)):
                match = True
        if match:
            continue
        else:
            comp.append(c)
            joined = []
            for c2 in curves:

                match = False
                c2 = c2.ToRevitType()
                for co in comp:
                    if startPoint(c2).IsAlmostEqualTo(startPoint(co)) and endPoint(c2).IsAlmostEqualTo(endPoint(co)):
                        match = True
                if match:
                    continue
                else:
                    if c2.Intersect(c) == SetComparisonResult.Disjoint:
                        continue
                    elif c2.Intersect(c) == SetComparisonResult.Equal:
                        continue
                    elif c2.Intersect(c) == SetComparisonResult.Subset:
                        comp.append(c2)
                        joined.append(c2.ToProtoType())
        joined.append(c.ToProtoType())
        re.append(joined)

    return re


def create_dim_hMOD(view, refs, dx, y):
    pt1 = XYZ(-100, -y, dx / 304.8)
    new_pt1 = get_true_coord(loc, orient1, pt1)
    pt2 = XYZ(100, -y, dx / 304.8)
    new_pt2 = get_true_coord(loc, orient1, pt2)
    ln1 = Line.CreateBound(new_pt1, new_pt2)
    dim = doc.Create.NewDimension(view, ln1, refs)
    return dim


def create_dim_v(view, refs, dx, y):
    pt1 = XYZ(dx / 304.8, -y, -100)
    new_pt1 = get_true_coord(loc, orient1, pt1)
    pt2 = XYZ(dx / 304.8, -y, 100)
    new_pt2 = get_true_coord(loc, orient1, pt2)
    ln1 = Line.CreateBound(new_pt1, new_pt2)
    dim = doc.Create.NewDimension(view, ln1, refs)
    return dim


def get_list_x(lines4, orient):
    list_x = []
    for line in lines[0]:
        x = round(get_relative_coord(loc, orient1, line.GetEndPoint(0)).X, 2)
        list_x.append(x)
    return list_x


def get_left_pt(edges):
    refs = ReferenceArray()
    uniq = []
    for edge in edges:
        pt1 = get_relative_coord(loc, orient1, edge.AsCurve().GetEndPoint(0))
        pt2 = get_relative_coord(loc, orient1, edge.AsCurve().GetEndPoint(1))
        x1 = round(pt1.X, 2)
        x2 = round(pt2.X, 2)
        z1 = round(pt1.Z, 2)
        z2 = round(pt2.Z, 2)
        if x1 < l / 2 and z1 not in uniq:
            ref = edge.GetEndPointReference(0)
            refs.Append(ref)
            uniq.append(z1)
        elif x2 < l / 2 and z2 not in uniq:
            ref = edge.GetEndPointReference(1)
            refs.Append(ref)
            uniq.append(z2)
    return refs, uniq


def get_right_pt(edges):
    refs = ReferenceArray()
    uniq = []
    for edge in edges:
        pt1 = get_relative_coord(loc, orient1, edge.AsCurve().GetEndPoint(0))
        pt2 = get_relative_coord(loc, orient1, edge.AsCurve().GetEndPoint(1))
        x1 = round(pt1.X, 2)
        x2 = round(pt2.X, 2)
        z1 = round(pt1.Z, 2)
        z2 = round(pt2.Z, 2)
        if x1 > l / 2 and z1 not in uniq:
            ref = edge.GetEndPointReference(0)
            refs.Append(ref)
            uniq.append(z1)
        elif x2 > l / 2 and z2 not in uniq:
            ref = edge.GetEndPointReference(1)
            refs.Append(ref)
            uniq.append(z2)
    return refs, uniq


def get_horizontal_edges(lines2):
    lines = []
    edges = []
    i = 0
    for line in lines2[0]:
        pt1 = get_relative_coord(loc, orient1, line.GetEndPoint(0))
        pt2 = get_relative_coord(loc, orient1, line.GetEndPoint(1))
        z1 = round(pt1.Z, 2)
        z2 = round(pt2.Z, 2)
        if z1 == z2 and lines2[1][i].ApproximateLength > 1:
            edges.append(lines2[1][i])
        i = i + 1
    return edges


def create_bypoint(point, familytype, view):
    el = doc.Create.NewFamilyInstance(point, familytype, view)
    return el


def move_pt(pt, x, y, z):
    x1 = pt.X + x
    y1 = pt.Y + y
    z1 = pt.Z + z
    pt2 = XYZ(x1, y1, z1)
    return pt2


def create_tags(view, elRefs, tagorn, els, r_orient):
    tags = []
    for i, el in enumerate(els):
        r_curve = rebar_curve(el)

        if r_orient[i]:
            pt1 = r_curve[0].GetEndPoint(0)
            pt2 = r_curve[0].GetEndPoint(1)
            mdpt = get_mid_point(pt1, pt2, 0.763)  #

            rel_org_Z = get_relative_coord(loc, orient1, mdpt).ToPoint().Z
            if rel_org_Z > h * Imper / 2:
                dx = 300 / Imper
                dz = 700 / Imper
            else:
                dx = -300 / Imper
                dz = -500 / Imper

            pt = get_new_point(mdpt, dx, 0, dz, 0)


        else:
            pt1 = r_curve[2].GetEndPoint(0)
            pt2 = r_curve[2].GetEndPoint(1)
            mdpt = get_mid_point(pt1, pt2, 0.75)  #

            rel_org_X = get_relative_coord(loc, orient1, mdpt).ToPoint().X
            if rel_org_X > l * Imper / 2:
                dx = 1000 / Imper
                dz = 100 / Imper
            else:
                dx = -1000 / Imper
                dz = 100 / Imper
            pt = get_new_point(mdpt, 0, dx, dz, 0)
        # t1 = el.Location#.Point

        # a = -get_angle(el.HandOrientation)
        # a = 30

        # pt2 = get_new_point(pt,-5*50/304.8,0,0,a)
        # pt = move_pt(pt,0,0,dz) # ,view,el,0,tagMode,tagorn,pt
        tag = IndependentTag.Create(doc, view.Id, elRefs[i], 1, tagMode, tagorn, pt)
        tag.get_Parameter(BuiltInParameter.LEADER_LINE).Set(1)

        tag.HasLeader = 1
        # tag.LeaderElbow = pt2
        # tag.LeaderEndCondition = LeaderEndCondition.Free
        tag.LeaderEndCondition = LeaderEndCondition.Attached
        # tag.LeaderEnd = pt1
        tag.TagHeadPosition = pt
        tags.append(tag)
    return tags


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


def closestEdge(pt, edges, Sides=["T", "B"]):
    dist = 10000
    for i, e in enumerate(edges):
        D = e.Distance(pt)
        if D < dist:
            dist = D
            S = Sides[i]
    return S


def rebar_curve(rebar):
    AFSI = False
    sH = False
    sBH = False
    MOPT = MultiplanarOption.IncludeAllMultiplanarCurves
    bPI = 0
    return rebar.GetCenterlineCurves(AFSI, sH, sBH, MOPT, bPI)


def rebars_normal(rebar):
    Curves = rebar_curve(rebar)
    if len(Curves) == 1:
        return True
    else:
        r_end_pts = [c.GetEndPoint(0.5) for c in Curves]
        return Plane.CreateByThreePoints(r_end_pts[0], r_end_pts[1], r_end_pts[2]).Normal


def rebars_plane(rebar):
    Curves = rebar_curve(rebar)
    if len(Curves) == 1:
        return True
    else:
        r_end_pts = [c.GetEndPoint(1) for c in Curves]
        r_start_pts = [c.GetEndPoint(0) for c in Curves]
        r_mid_pts = [c.get_mid_point(i, j) for i, j in zip(r_end_pts, r_start_pts)]

        return Plane.CreateByThreePoints(r_mid_pts[0], r_mid_pts[1], r_mid_pts[2])


def get_new_point(pt1, fx, fy, fz, a):
    x1 = pt1.X
    y1 = pt1.Y
    x2 = x1 + (fx) * math.cos(math.radians(a)) - (fy) * math.sin(math.radians(a))
    y2 = y1 + (fx) * math.sin(math.radians(a)) + (fy) * math.cos(math.radians(a))
    z1 = pt1.Z + fz
    pt2 = XYZ(x2, y2, z1)
    return pt2


def get_mid_point(pt1, pt2, param=0.5):
    x1 = pt1.X * (1 - param)
    y1 = pt1.Y * (1 - param)
    z1 = pt1.Z * (1 - param)

    x2 = pt2.X * (param)
    y2 = pt2.Y * (param)
    z2 = pt2.Z * (param)
    return XYZ((x1 + x2), (y1 + y2), (z1 + z2))


def isHorizontal(line):
    line = line.ToProtoType()
    EPz = line.EndPoint.Z
    SPz = line.StartPoint.Z
    if EPz == SPz:
        return True
    else:
        return False


def mra_options(type, elIds, Vec, view, org, org_T, refs):
    options = MultiReferenceAnnotationOptions(type)
    options.TagHeadPosition = org_T
    options.DimensionLineOrigin = org
    options.DimensionPlaneNormal = view.ViewDirection
    options.DimensionLineDirection = Vec  # .CrossProduct(view.ViewDirection) #XYZ( 1, 0, 0 )
    options.SetElementsToDimension(elIds)
    # options.TagHasLeader = False
    options.SetAdditionalReferencesToDimension(refs)
    return options


# Create the dimension in a transaction
Zaxis = XYZ(0, 0, 1)
TransactionManager.Instance.EnsureInTransaction(doc)
views = UnwrapElement(IN[0])

if not hasattr(views, '__iter__'):
    views = [views]

for view in views:
    asms = FilteredElementCollector(doc, view.Id).OfCategory(
        BuiltInCategory.OST_Assemblies).WhereElementIsNotElementType().ToElements()
    ids = asms[0].GetMemberIds()
    list = []
    panel = None
    rebars = []
    parts = []

    for id in ids:
        el = doc.GetElement(id)
        category = el.Category.Name
        if category == "Walls":
            panel = el
        elif category == "Structural Rebar":
            rebars.append(el)
        elif category == "Parts":
            parts.append(el)

    Imper = 304.8
    #

    ## Get Concrete part
    V = 0
    pEl = 0
    for p in parts:
        pV = get_solids(p)[0].Volume
        if pV > V:
            pEl = p
            V = pV

    geoms = panel.get_Geometry(opt)
    locCurve = panel.Location
    Curve = locCurve.Curve
    CurvLen = Curve.Length
    loc = Curve.Origin
    # panel = UnwrapElement(panel)
    BBox = pEl.get_BoundingBox(None)  # bounding box of wall

    list = []
    faces = []
    orient = WallOrientation(panel)
    orientXYZ = orient.ToXyz()
    orient1 = orientXYZ.CrossProduct(Zaxis)
    l = CurvLen  # *Imper
    h = panel.LookupParameter("Unconnected Height").AsDouble()  # *Imper
    t = panel.Width  # *Imper

    long_bars = []
    trans_bars = []
    angles = []
    angles1 = []
    vectors = []
    abc = []
    r_bars_orient = []
    for r in rebars:
        normal = rebars_normal(r)
        abc.append(normal)
        if normal == True:
            long_bars.append(r)
            r_bars_orient.append(True)
        else:
            angle = orientXYZ.AngleTo(normal)
            angle = round(math.degrees(angle))

            angleZ = Zaxis.AngleTo(normal)
            angleZ = round(math.degrees(angleZ))

            angles1.append(angle)
            angles.append(angleZ)
            if angleZ in [165, 15] or angle in [0, 180]:
                long_bars.append(r)
                r_bars_orient.append(False)
            else:
                trans_bars.append(r)
                vectors.append(normal)
    #

    lines = []
    solids = get_solids(pEl)
    faces = get_front_faces(solids, orient)  # faces
    lines = get_lines(faces)  # lines of front faces
    lines2 = get_relative_lines(lines, orient1)  # lines acording to wall position
    #
    left = get_left_line(lines2)
    right = get_right_line(lines2)
    lines3 = [[left[0], right[0]], [left[1], right[1]]]
    #
    #
    topL = get_top_line(lines2)
    bottomL = get_bottom_line(lines2)
    ToBo = [[topL[0], bottomL[0]], [topL[1], bottomL[1]]]
    refs = get_refs(ToBo[1])
    #
    #
    LR = [left[0], right[0]]
    TB = [topL[0], bottomL[0]]
    dim01 = create_dim_v(view, refs, l * 304.8 + 500, t / 2)
    dim1 = create_dim_h(view, lines3, h * Imper + 500)

    distances = []
    r_aaso_refs = []
    orgs = []
    r_orientation = []
    r_lines = []
    T_dist = []
    r_edges = []
    NR = []

    for i, r in enumerate(trans_bars):
        r_curves = rebar_curve(r)
        r_curve = r_curves[1]
        temp_ln = []
        temp_e = []

        # NR.append([round(math.degrees(LL.Direction.AngleTo(vectors[i]))) for LL in lines[0]])

        for ln, e in zip(lines[0], lines[1]):
            angle = ln.Direction.AngleTo(vectors[i])
            angle = round(math.degrees(angle))

            if (angle == 180 or angle == 0):
                temp_ln.append(ln)
                temp_e.append(e)

        dist = 10000000
        edge = None
        Line = None
        for ln, e in zip(temp_ln, temp_e):
            D = ln.Distance(r_curve.GetEndPoint(0.5))
            distances.append(D)
            if D <= dist:
                dist = D
                edge = e
                Line = ln

        #	T_dist.append(dist)
        #
        orgs.append(get_mid_point(Line.GetEndPoint(0), Line.GetEndPoint(1)))
        r_orientation.append(isHorizontal(Line))
        r_lines.append(Line)
        r_edges.append(edge)
        r_aaso_refs.append([edge.GetEndPointReference(0), edge.GetEndPointReference(1)])

    for n, i in enumerate(trans_bars):
        Vec = vectors[n]

        elId = List[ElementId]([i.Id])
        pt1 = rebar_curve(i)
        pt1 = pt1[0].GetEndPoint(0.5)
        if r_orientation[n]:  # LR, TB
            rel_org_Z = get_relative_coord(loc, orient1, orgs[n]).ToPoint().Z
            if rel_org_Z > h * Imper / 2:
                org = XYZ(orgs[n][0], orgs[n][1], orgs[n][2] + 300 / Imper)
                org_T = XYZ(orgs[n][0], orgs[n][1], orgs[n][2] + 200 / Imper)
            else:
                org = XYZ(orgs[n][0], orgs[n][1], orgs[n][2] - 200 / Imper)
                org_T = XYZ(orgs[n][0], orgs[n][1], orgs[n][2] - 300 / Imper)

        else:
            rel_org_X = get_relative_coord(loc, orient1, orgs[n]).ToPoint().X
            if rel_org_X > l / 2 * Imper:
                org = XYZ(orgs[n][0], orgs[n][1] + 300 / Imper, orgs[n][2])
                org_T = XYZ(orgs[n][0], orgs[n][1] + 200 / Imper, orgs[n][2])
            else:
                org = XYZ(orgs[n][0], orgs[n][1] - 200 / Imper, orgs[n][2])
                org_T = XYZ(orgs[n][0], orgs[n][1] - 300 / Imper, orgs[n][2])

        OPT = mra_options(type1, elId, Vec, view, org, org_T, r_aaso_refs[n])
        TransactionManager.Instance.EnsureInTransaction(doc)
        multiRebar = MultiReferenceAnnotation.Create(doc, view.Id, OPT)
        TransactionManager.Instance.TransactionTaskDone()
        TId = doc.GetElement(multiRebar.TagId)
        TId.LeaderEndCondition = LeaderEndCondition.Free
        TId.HasLeader = False
        if not r_orientation[n]:
            TId.TagOrientation = TagOrientation.Vertical
    #

    # flatten = lambda l: [item for sublist in l for item in sublist]11

    ###-----------Generic models labels----------------
    tagMode = TagMode.TM_ADDBY_CATEGORY
    tagorn = TagOrientation.Horizontal
    #
    #####Create the dimension in a transaction
    TransactionManager.Instance.EnsureInTransaction(doc)
    rebars_refs = [Reference(i) for i in long_bars]

    tags = create_tags(view, rebars_refs, tagorn, long_bars, r_bars_orient)

    TransactionManager.Instance.TransactionTaskDone()

OUT = 1  # [i.ToProtoType() for i in lines[0]]#,[i.ApproximateLength*Imper for i in lines ]