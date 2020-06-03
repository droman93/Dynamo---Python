import clr

clr.AddReference("ProtoGeometry")
from Autodesk.DesignScript.Geometry import *

clr.AddReference('RevitAPI')
from Autodesk.Revit.DB import *

clr.AddReference('RevitAPIUI')
import Autodesk
from Autodesk.Revit.UI import *

ST = Autodesk.Revit.UI.Selection
clr.AddReference("RevitNodes")
clr.AddReference("RevitServices")
import RevitServices
from RevitServices.Persistence import DocumentManager
from RevitServices.Transactions import TransactionManager
import sys
import math
import Revit

clr.ImportExtensions(Revit.Elements)
clr.ImportExtensions(Revit.GeometryConversion)
#####################################################33
doc = DocumentManager.Instance.CurrentDBDocument
uidoc = DocumentManager.Instance.CurrentUIApplication.ActiveUIDocument
a_view = doc.ActiveView
assemblies = FilteredElementCollector(doc).OfCategory(
    BuiltInCategory.OST_Assemblies).WhereElementIsNotElementType().ToElements()
types = FilteredElementCollector(doc).OfCategory(
    BuiltInCategory.OST_DetailComponents).WhereElementIsElementType().ToElements()
snapTypes = ST.ObjectSnapTypes.Endpoints
objectType = ST.ObjectType.Element
filter = ST.ISelectionFilter
splane = a_view.SketchPlane
# plane = doc.Create.Plane(a_view.ViewDirection, a_view.Origin)
stype = Autodesk.Revit.DB.Structure.StructuralType.NonStructural
titles = FilteredElementCollector(doc).OfCategory(
    BuiltInCategory.OST_TitleBlocks).WhereElementIsElementType().ToElements()
title_id = titles[1].Id
views = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Views).WhereElementIsNotElementType().ToElements()
schedules = FilteredElementCollector(doc).OfCategory(
    BuiltInCategory.OST_Schedules).WhereElementIsNotElementType().ToElements()
# Options
opt = Options()
opt.ComputeReferences = True
opt.IncludeNonVisibleObjects = False

# ----------INPUTS DATA----------------
retry = IN[0]
title_f = IN[1]
title_t = IN[2]
detail_Front = IN[3]
v3d_name = IN[4]
spec_name = IN[5]
detail_Top = IN[7]
detail_Left = IN[8]
rebar_Front = IN[9]
rebar_Left = IN[10]
fsheet_Front_F = IN[11]
fsheet_Front_R = IN[12]
rebars_schedule = IN[13]
fasonare_schedule = IN[24]  # extras formede fasonare
fabric_schedule = IN[14]
generic_schedule = IN[15]
t_armare_schedule = IN[16]  # titlu armare
t_fabric_schedule = IN[17]
t_cofraj_schedule = IN[18]
# Legend views
Det_tesire = UnwrapElement(IN[19])
Nota = UnwrapElement(IN[20])
Schema_ridicare = UnwrapElement(IN[21])
Mat_cofraj = UnwrapElement(IN[22])
Mat_armare = UnwrapElement(IN[23])
Rev = IN[25]

type1 = None
test = []
v_templates = []
for v in views:
    if v.IsTemplate:
        v_templates.append(v)

# Schedule for material take off
s_templates = []
for s in schedules:
    if s.IsTemplate:
        s_templates.append(s)

# Template front view
detail_t_front = None
for v in v_templates:
    if v.Name == detail_Front:
        detail_t_front = v.Id

# Template left view
detail_t_left = None
for v in v_templates:
    if v.Name == detail_Left:
        detail_t_left = v.Id

# Template top view
detail_t_top = None
for v in v_templates:
    if v.Name == detail_Top:
        detail_t_top = v.Id

# Template front rebar veiw
rebar_F = None
for v in v_templates:
    if v.Name == rebar_Front:
        rebar_F = v.Id

# Template front fabric sheet struc
fsheet_FR = None
for v in v_templates:
    if v.Name == fsheet_Front_R:
        fsheet_FR = v.Id

# Template front fabric sheet facade
fsheet_FF = None
for v in v_templates:
    if v.Name == fsheet_Front_F:
        fsheet_FF = v.Id

# Template section rebar veiw
rebar_L = None
for v in v_templates:
    if v.Name == rebar_Left:
        rebar_L = v.Id

# 3D view template
v3d_t = None
for v in v_templates:
    if v.Name == v3d_name:
        v3d_t = v.Id

spec_t = None
for s in s_templates:
    if s.Name == spec_name:
        spec_t = s.Id

# Generic models template
sched_gm = None
for s in s_templates:
    if s.Name == generic_schedule:
        sched_gm = s.Id

# Rebars template
s_rebars = None
for s in s_templates:
    if s.Name == rebars_schedule:
        s_rebars = s.Id

# Rebar shape template
s_fasonare = None
for s in s_templates:
    if s.Name == fasonare_schedule:
        s_fasonare = s.Id

# Fabric template
s_fabric = None
for s in s_templates:
    if s.Name == fabric_schedule:
        s_fabric = s.Id

# Titlu armare template
t_rebar = None
for s in s_templates:
    if s.Name == t_armare_schedule:
        t_rebar = s.Id

# Titlu Fabric template
t_fabric = None
for s in s_templates:
    if s.Name == t_fabric_schedule:
        t_fabric = s.Id

# Titlu Cofraj template
t_cofraj = None
for s in s_templates:
    if s.Name == t_cofraj_schedule:
        t_cofraj = s.Id

for t in titles:
    fam = t.get_Parameter(BuiltInParameter.ALL_MODEL_FAMILY_NAME).AsString()
    type = t.get_Parameter(BuiltInParameter.ALL_MODEL_TYPE_NAME).AsString()
    if title_f == fam and title_t == type:
        title_id = t.Id
        break

# ----------Categories--------------------------------------

Generic_category = [i for i in doc.Settings.Categories if i.Name == "Generic Models"]
Generic_category = Generic_category[0]
#
Walls_category = [i for i in doc.Settings.Categories if i.Name == "Walls"]
Walls_category = Walls_category[0]
#
Rebar_category = [i for i in doc.Settings.Categories if i.Name == "Structural Rebar"]
Rebar_category = Rebar_category[0]
#
Fabric_category = [i for i in doc.Settings.Categories if i.Name == "Structural Fabric Reinforcement"]
Fabric_category = Fabric_category[0]
#
Parts_category = [i for i in doc.Settings.Categories if i.Name == "Parts"]
Parts_category = Parts_category[0]
# ----------Viewport title--------------------------------------
element_types = FilteredElementCollector(doc).OfClass(ElementType).ToElements()
Tp = None
Ts = None
Tv = None
Tva = None
Nt = None

for a in element_types:
    name = a.GetParameters("Type Name")[0].AsString()
    if name in ["No Title"]:
        Nt = a.Id
    elif name in ["Titlu vederi"]:
        Tv = a.Id
    elif name in ["Titlu sectiune"]:
        Ts = a.Id
    elif name in ["Titlu plase"]:
        Tp = a.Id
    elif name in ["Titlu vederi armare"]:
        Tva = a.Id

# ----------FUNCTIONS--------------------------------------
flatten = lambda l: [item for sublist in l for item in sublist]


def get_selected_elements():
    ids = uidoc.Selection.GetElementIds()
    if isinstance(ids, list) == True:
        ids = [ids]
    els = []
    for id in ids:
        el = doc.GetElement(id)
        els.append(el)
    return els


def get_solids(el):
    geoms = el.get_Geometry(opt)
    solids = []
    for g in geoms:
        type = g.GetType().Name
        if type == "Solid":
            solids.append(g)
    return solids


def get_wall(part):
    tempList = []
    List = []
    Level = 0
    temp = part
    k = 1
    i = 0
    iter = 0
    List.append(temp.GetSourceElementIds())
    Wall = None
    while True:
        try:
            el = doc.GetElement(List[Level][i].HostElementId)
            category = el.Category.Name
            tempList.append(el.GetSourceElementIds())
        except:
            1
        k += 1
        i += 1
        iter += 1
        if k > len(List[Level]):
            List.append(flatten(tempList))
            Level += 1
            i = 0
            k = 0
        if iter == 100:
            break
        if category == "Walls":
            Wall = el
            break
    return Wall


def get_orientation(asm_id):
    Parts = []
    asm = doc.GetElement(asm_id)
    ids = asm.GetMemberIds()
    for id in ids:
        el = doc.GetElement(id)
        category = el.Category.Name
        # if cat=="Walls":
        #	panel=el
        if category == "Parts":
            Parts.append(el)
    MaxVolume = 0
    try:
        for p in Parts:
            V = get_solids(p)[0].ToProtoType().Volume
            if V > MaxVolume:
                MaxVolume = V
                cpart = p
    except:
        cpart = Parts[0]
    orient = WallOrientation(get_wall(cpart))
    if Rev:
        orient = orient.Reverse()
    return orient


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


def rotate_assembly(e, WallOrient):
    Zaxis = XYZ(0, 0, 1)
    trans = e.GetTransform()
    X = Zaxis.CrossProduct(WallOrient.ToXyz()) * -1
    trans.BasisX = X
    trans.BasisY = WallOrient.ToXyz()
    trans.BasisZ = Zaxis

    # TransactionManager.Instance.EnsureInTransaction(doc)
    e.SetTransform(trans)


# TransactionManager.Instance.ForceCloseTransaction()


def rotate(angle, view):
    TransactionManager.Instance.EnsureInTransaction(doc)
    view.CropBoxVisible = False
    TransactionManager.Instance.TransactionTaskDone()
    TransactionManager.Instance.ForceCloseTransaction()
    collector = FilteredElementCollector(doc, view.Id)
    shownElems = collector.ToElementIds()
    TransactionManager.Instance.EnsureInTransaction(doc)
    view.CropBoxVisible = True
    TransactionManager.Instance.TransactionTaskDone()
    TransactionManager.Instance.ForceCloseTransaction()
    TransactionManager.Instance.EnsureInTransaction(doc)
    collector = FilteredElementCollector(doc, view.Id)
    collector.Excluding(shownElems)
    cropBoxElement = collector.FirstElement()
    bb = view.CropBox
    center = 0.5 * (bb.Max + bb.Min)
    axis = Line.CreateBound(center, center + XYZ.BasisZ)
    ElementTransformUtils.RotateElement(doc, cropBoxElement.Id, axis, math.radians(angle))
    TransactionManager.Instance.TransactionTaskDone()
    TransactionManager.Instance.ForceCloseTransaction()
    TransactionManager.Instance.EnsureInTransaction(doc)
    view.CropBoxVisible = False
    TransactionManager.Instance.TransactionTaskDone()
    TransactionManager.Instance.ForceCloseTransaction()
    TransactionManager.Instance.EnsureInTransaction(doc)


# -----------------------------------------------------
els = UnwrapElement(IN[6])  # get_selected_elements()

if not hasattr(els, '__iter__'):
    els = [els]
assemblies1 = []
Zaxis = XYZ(0, 0, 1)
# for el in els:
#	type = el.GetType().Name
#	id = el.Id
#	if type == "AssemblyInstance":
#		asm_id=None
#		for a in assemblies:
#			id2 = a.get_Parameter(BuiltInParameter.ELEM_TYPE_PARAM).AsElementId()
#			if id==id2:
#				asm_id= a.Id
#				break
#
# assemblies1.append(asm_id)
genetal_views = []
top_views = []
right_views = []
Imper = 304.8

TransactionManager.Instance.EnsureInTransaction(doc)
for asm_id in els:
    aId = asm_id.Id
    orient = get_orientation(aId)
    name = doc.GetElement(aId).Name

    rotate_assembly(asm_id, orient)
    top = AssemblyDetailViewOrientation.ElevationTop
    if round(orient.X) == 1 and round(orient.Y) == 0:
        front = AssemblyDetailViewOrientation.ElevationBack
        right = AssemblyDetailViewOrientation.ElevationRight
        DetSecA = AssemblyDetailViewOrientation.DetailSectionB
        angle = 180
    elif round(orient.X) == 0 and round(orient.Y) == -1:
        front = AssemblyDetailViewOrientation.ElevationBack
        right = AssemblyDetailViewOrientation.ElevationRight
        DetSecA = AssemblyDetailViewOrientation.DetailSectionB
        angle = 180
    elif round(orient.X) == 0 and round(orient.Y) == 1:
        front = AssemblyDetailViewOrientation.ElevationBack
        right = AssemblyDetailViewOrientation.ElevationRight
        DetSecA = AssemblyDetailViewOrientation.DetailSectionB
        angle = 180
    elif round(orient.X) == -1 and round(orient.Y) == 0:
        front = AssemblyDetailViewOrientation.ElevationBack
        right = AssemblyDetailViewOrientation.ElevationLeft
        DetSecA = AssemblyDetailViewOrientation.DetailSectionB
        angle = 180
    else:
        front = AssemblyDetailViewOrientation.ElevationFront
        right = AssemblyDetailViewOrientation.ElevationRight
        DetSecA = AssemblyDetailViewOrientation.DetailSectionA
        angle = 0
    # asm_id = assembly.Id
    view3d = AssemblyViewUtils.Create3DOrthographic(doc, aId, v3d_t, 1)
    view3d.Name = "Vedere 3D"

    ### CREARE EXTRASE
    MTO = AssemblyViewUtils.CreateMaterialTakeoff(doc, aId, spec_t, 1)
    MTO.Name = "Cantitati Materiale Panou"

    Legend_schedule = AssemblyViewUtils.CreateSingleCategorySchedule(doc, aId, Generic_category.Id, sched_gm, 1)
    Legend_schedule.Name = "Legenda"

    Rebar_schedule = AssemblyViewUtils.CreateSingleCategorySchedule(doc, aId, Rebar_category.Id, s_rebars, 1)
    Rebar_schedule.Name = "Extras Armare"

    Shape_schedule = AssemblyViewUtils.CreateSingleCategorySchedule(doc, aId, Rebar_category.Id, s_fasonare, 1)
    Shape_schedule.Name = "Extras Forme de Fasonare"

    Fabric_schedule = AssemblyViewUtils.CreateSingleCategorySchedule(doc, aId, Fabric_category.Id, s_fabric, 1)
    Fabric_schedule.Name = "Extras Plase Sudate"

    Titlu_cofraj = AssemblyViewUtils.CreateSingleCategorySchedule(doc, aId, Parts_category.Id, t_cofraj, 1)
    Titlu_cofraj.Name = "Titlu cofraj"

    Titlu_aramre = AssemblyViewUtils.CreateSingleCategorySchedule(doc, aId, Parts_category.Id, t_rebar, 1)
    Titlu_aramre.Name = "Titlu armare"

    Titlu_plase = AssemblyViewUtils.CreateSingleCategorySchedule(doc, aId, Parts_category.Id, t_fabric, 1)
    Titlu_plase.Name = "Titlu plase"

    ### CREARE VEDERI
    direction = front
    detail1 = AssemblyViewUtils.CreateDetailSection(doc, aId, direction, detail_t_front, 1)
    detail1.Name = "Din Fata"

    R_detail1 = AssemblyViewUtils.CreateDetailSection(doc, aId, direction, rebar_F, 1)
    R_detail1.Name = "Din Fata Armare"

    FF_detail1 = AssemblyViewUtils.CreateDetailSection(doc, aId, direction, fsheet_FF, 1)
    FF_detail1.Name = "Dispunere plase sudate in stratul de fatada"

    FR_detail1 = AssemblyViewUtils.CreateDetailSection(doc, aId, direction, fsheet_FR, 1)
    FR_detail1.Name = "Dispunere plase sudate in stratul de rezistenta"

    genetal_views.append(detail1)
    direction = top
    detail2 = AssemblyViewUtils.CreateDetailSection(doc, aId, direction, detail_t_top, 1)
    detail2.Name = "De Sus"
    top_views.append(detail2)

    direction = right
    detail3 = AssemblyViewUtils.CreateDetailSection(doc, aId, direction, detail_t_left, 1)
    detail3.Name = "A"

    direction = DetSecA
    detail4 = AssemblyViewUtils.CreateDetailSection(doc, aId, direction, detail_t_left, 1)
    detail4.Name = "B"

    direction = DetSecA
    R_detail4 = AssemblyViewUtils.CreateDetailSection(doc, aId, direction, rebar_L, 1)
    R_detail4.Name = "C"

    right_views.append(detail3)
    right_views.append(detail4)
    sheet = AssemblyViewUtils.CreateSheet(doc, aId, title_id)
    sheet.Name = "Cofraj " + name;  # sheet.Number = "1"
    sheet2 = AssemblyViewUtils.CreateSheet(doc, aId, title_id)
    sheet2.Name = "Armare " + name;  # sheet2.Number = "2"
    sheet3 = AssemblyViewUtils.CreateSheet(doc, aId, title_id)
    sheet3.Name = "Plase sudate " + name;  # sheet3.Number = "3"

    #### Viewports on rebar sheet #vp3.ChangeTypeId()
    vp1 = Viewport.Create(doc, sheet.Id, view3d.Id, XYZ(500 / Imper, 200 / Imper, 0));
    vp1.ChangeTypeId(Tp)
    vp2 = Viewport.Create(doc, sheet.Id, detail1.Id, XYZ(500 / Imper, 170 / Imper, 0));
    vp2.ChangeTypeId(Tv)
    vp4 = Viewport.Create(doc, sheet.Id, detail3.Id, XYZ(500 / Imper, 140 / Imper, 0));
    vp4.ChangeTypeId(Ts)
    vp5 = Viewport.Create(doc, sheet.Id, detail4.Id, XYZ(500 / Imper, 110 / Imper, 0));
    vp5.ChangeTypeId(Ts)
    vp6 = ScheduleSheetInstance.Create(doc, sheet.Id, MTO.Id, XYZ(500 / Imper, 80 / Imper, 0))
    if angle != 0:
        rotate(angle, detail2)
    vp3 = Viewport.Create(doc, sheet.Id, detail2.Id, XYZ(500 / Imper, 50 / Imper, 0));
    vp3.ChangeTypeId(Tv)
    vp7 = ScheduleSheetInstance.Create(doc, sheet.Id, Titlu_cofraj.Id, XYZ(500 / Imper, 20 / Imper, 0))
    vp8 = ScheduleSheetInstance.Create(doc, sheet.Id, Legend_schedule.Id, XYZ(500 / Imper, -10 / Imper, 0))
    vp9 = Viewport.Create(doc, sheet.Id, Det_tesire.Id, XYZ(500 / Imper, -40 / Imper, 0));
    vp9.ChangeTypeId(Nt)
    vp10 = Viewport.Create(doc, sheet.Id, Schema_ridicare.Id, XYZ(500 / Imper, -70 / Imper, 0));
    vp10.ChangeTypeId(Nt)
    vp11 = Viewport.Create(doc, sheet.Id, Nota.Id, XYZ(500 / Imper, -100 / Imper, 0));
    vp11.ChangeTypeId(Nt)
    vp12 = Viewport.Create(doc, sheet.Id, Mat_cofraj.Id, XYZ(500 / Imper, -130 / Imper, 0));
    vp12.ChangeTypeId(Nt)

    #### Viewports on rebar sheet
    vpr1 = Viewport.Create(doc, sheet2.Id, R_detail1.Id, XYZ(500 / Imper, 150 / Imper, 0));
    vpr1.ChangeTypeId(Tva)
    vpr2 = Viewport.Create(doc, sheet2.Id, R_detail4.Id, XYZ(500 / Imper, 120 / Imper, 0));
    vpr2.ChangeTypeId(Ts)
    vpr3 = ScheduleSheetInstance.Create(doc, sheet2.Id, Titlu_aramre.Id, XYZ(500 / Imper, 90 / Imper, 0))
    vpr4 = Viewport.Create(doc, sheet2.Id, Mat_armare.Id, XYZ(500 / Imper, 60 / Imper, 0));
    vpr4.ChangeTypeId(Nt)

    ###Viewports on fabric sheet!
    vpf1 = Viewport.Create(doc, sheet3.Id, FF_detail1.Id, XYZ(500 / Imper, 150 / Imper, 0));
    vpf1.ChangeTypeId(Tp)
    vpf2 = Viewport.Create(doc, sheet3.Id, FR_detail1.Id, XYZ(500 / Imper, 120 / Imper, 0));
    vpf2.ChangeTypeId(Tp)
    vpf3 = ScheduleSheetInstance.Create(doc, sheet3.Id, Titlu_plase.Id, XYZ(500 / Imper, 90 / Imper, 0))
    vpf4 = ScheduleSheetInstance.Create(doc, sheet3.Id, Rebar_schedule.Id, XYZ(500 / Imper, 60 / Imper, 0))
    vpf5 = ScheduleSheetInstance.Create(doc, sheet3.Id, Shape_schedule.Id, XYZ(500 / Imper, 30 / Imper, 0))
    vpf6 = ScheduleSheetInstance.Create(doc, sheet3.Id, Fabric_schedule.Id, XYZ(500 / Imper, 0 / Imper, 0))
    vpf7 = Viewport.Create(doc, sheet3.Id, Mat_armare.Id, XYZ(500 / Imper, -30 / Imper, 0));
    vpf7.ChangeTypeId(Nt)

    FCO3 = detail3.LookupParameter("Far Clip Offset")
    FCO3.Set(1400 / Imper)
    FCO4 = detail4.LookupParameter("Far Clip Offset")
    FCO4.Set(400 / Imper)
    RFCO4 = R_detail4.LookupParameter("Far Clip Offset")
    RFCO4.Set(200 / Imper)

TransactionManager.Instance.TransactionTaskDone()
TransactionManager.Instance.ForceCloseTransaction()

OUT = genetal_views, top_views, right_views, R_detail1, FF_detail1, FR_detail1, R_detail4




























