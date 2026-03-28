# -*- coding: utf-8 -*-
import FreeCAD as App
import FreeCADGui as Gui
import Part

from ..core.loader import Catalog
from ..core.fittings import build_fitting_shape, add_mate_markers
from ..core.profiles import nearest_slot_center

try:
    from PySide import QtGui as QtWidgets  # type: ignore
except Exception:
    from PySide2 import QtWidgets

SPLICE_PLATE_4H = {
    "id": "SPLICE_4H",
    "name": "4-Hole Splice Plate",
    "width_mm": 41.275,     # match P4100 width for now
    "height_mm": 82.55,     # ~3.25 in
    "thickness_mm": 4.76,   # ~3/16 in
}

def build_splice_plate(spec: dict) -> Part.Shape:
    w = float(spec["width_mm"])
    h = float(spec["height_mm"])
    t = float(spec["thickness_mm"])
    # Plate in XY, thickness in +Z
    face = Part.makePlane(w, h)
    return face.extrude(App.Vector(0, 0, t))

def fitting_rotation_from_selection(subobj):
    if subobj is None:
        return App.Rotation()

    # Face selection: align fitting local +Z to face normal
    if isinstance(subobj, Part.Face):
        try:
            umin, umax, vmin, vmax = subobj.ParameterRange
            u = (umin + umax) / 2.0
            v = (vmin + vmax) / 2.0
            normal = subobj.normalAt(u, v)
            return App.Rotation(App.Vector(0, 0, 1), normal)
        except Exception:
            return App.Rotation()

    # Edge selection: later
    return App.Rotation()

class _CmdAddFitting:
    def GetResources(self):
        return {"MenuText": "Add Fitting", "ToolTip": "Place a fitting from datastore (placeholder geometry in v0.1)"}

    def Activated(self):
        cat = Catalog.load()
        dlg = QtWidgets.QDialog()
        dlg.setWindowTitle("Unistrut: Add Fitting")
        layout = QtWidgets.QVBoxLayout(dlg)
        doc = App.ActiveDocument
        if doc is None:
            doc = App.newDocument()

        combo = QtWidgets.QComboBox()
        combo.addItems(cat.list_fittings())
        layout.addWidget(combo)

        btns = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        layout.addWidget(btns)

        def ok():
            fid = combo.currentText()
            fitting = cat.get_fitting(fid)
            shp = build_fitting_shape(fitting)

            doc = App.ActiveDocument or App.newDocument("UnistrutWB")
            obj = doc.addObject("Part::Feature", f"F_{fid}")
            obj.Shape = shp

            obj.addProperty("App::PropertyString", "UnistrutType", "Unistrut").UnistrutType = "fitting"
            obj.addProperty("App::PropertyString", "FittingId", "Unistrut").FittingId = fid
            add_mate_markers(obj, fitting)

            channel = None
            picked_point = None
            picked_subobj = None

            sel_ex = Gui.Selection.getSelectionEx()
            for s in sel_ex:
                obj_sel = s.Object
                if getattr(obj_sel, "UnistrutType", "") == "profile":
                    channel = obj_sel
                    if getattr(s, "PickedPoints", None):
                        if s.PickedPoints:
                            picked_point = s.PickedPoints[0]
                        if getattr(s, "SubObjects", None):
                            if s.SubObjects:
                                picked_subobj = s.SubObjects[0]
                    break

            if channel is None:
                sel = Gui.Selection.getSelection()
                for s in sel:
                    if getattr(s, "UnistrutType", "") == "profile":
                        channel = s
                        break

            print("channel:", channel.Name if channel else None)
            print("picked_point:", picked_point)
            print("picked_subobj:", type(picked_subobj).__name__ if picked_subobj else None)
            
            if channel and "SlotCenters" in channel.PropertiesList and channel.SlotCenters:
                centers = list(channel.SlotCenters)
                print("slotcenters_count:", len(centers))

                if picked_point is not None:
                    guess = picked_point
                elif picked_subobj is not None:
                    try:
                        guess = picked_subobj.BoundBox.Center
                    except Exception:
                        guess = centers[0]
                else:
                    guess = centers[0]

                slot = nearest_slot_center(centers, guess) or centers[0]
                rot = fitting_rotation_from_selection(picked_subobj)

                print("guess:", guess)
                print("chosen_slot:", slot)

                obj.Placement = App.Placement(slot, rot)
            else:
                obj.Placement = App.Placement(App.Vector(0, 0, 0), App.Rotation())

            if "HostProfile" not in obj.PropertiesList:
                obj.addProperty("App::PropertyString", "HostProfile", "Unistrut")

            obj.HostProfile = channel.Name if channel else ""    

            doc.recompute()
            dlg.accept()

        btns.accepted.connect(ok)
        btns.rejected.connect(dlg.reject)
        dlg.exec_()

Gui.addCommand("Unistrut_AddFitting", _CmdAddFitting())
