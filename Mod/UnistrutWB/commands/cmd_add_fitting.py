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

def _safe_norm(v):
    try:
        if v.Length == 0:
            return None
        out = App.Vector(v.x, v.y, v.z)
        out.normalize()
        return out
    except Exception:
        return None


def _pick_face_normal(face):
    try:
        umin, umax, vmin, vmax = face.ParameterRange
        u = (umin + umax) / 2.0
        v = (vmin + vmax) / 2.0
        n = face.normalAt(u, v)
        return _safe_norm(n)
    except Exception:
        return None


def _rotation_from_axes(x_dir: App.Vector, y_dir: App.Vector, z_dir: App.Vector):
    m = App.Matrix()
    m.A11, m.A21, m.A31 = x_dir.x, x_dir.y, x_dir.z
    m.A12, m.A22, m.A32 = y_dir.x, y_dir.y, y_dir.z
    m.A13, m.A23, m.A33 = z_dir.x, z_dir.y, z_dir.z
    return App.Rotation(m)


def fitting_rotation_from_selection(subobj, channel=None):
    # Canonical channel axis for current generated members
    channel_x = App.Vector(1, 0, 0)

    if subobj is None:
        return App.Rotation()

        # Face selection
    if isinstance(subobj, Part.Face):
        z_dir = _pick_face_normal(subobj)
        if z_dir is None:
            return App.Rotation()

        world_y = App.Vector(0, 1, 0)
        world_z = App.Vector(0, 0, 1)

        # Broad-face policy: normalize opposing Z faces to one mounting convention.
        if abs(z_dir.dot(world_z)) > 0.9:
            face_class = "z_face"
            if z_dir.dot(world_z) > 0:
                z_dir = z_dir.negative()

        # Side-face policy: provisional
        elif abs(z_dir.dot(world_y)) > 0.9:
            face_class = "y_face"
            if z_dir.dot(world_y) > 0:
                z_dir = z_dir.negative()

        else:
            face_class = "other"

        App.Console.PrintMessage(f"[UnistrutWB] face_normal: {z_dir}\n")
        App.Console.PrintMessage(f"[UnistrutWB] face_class: {face_class}\n")

        if abs(z_dir.dot(channel_x)) > 0.999:
            trial = App.Vector(0, 1, 0)
        else:
            trial = channel_x

        y_dir = _safe_norm(z_dir.cross(trial))
        if y_dir is None:
            return App.Rotation()

        x_dir = _safe_norm(y_dir.cross(z_dir))
        if x_dir is None:
            return App.Rotation()

        App.Console.PrintMessage(f"[UnistrutWB] x_dir: {x_dir}\n")
        App.Console.PrintMessage(f"[UnistrutWB] y_dir: {y_dir}\n")
        App.Console.PrintMessage(f"[UnistrutWB] z_dir: {z_dir}\n")

        return _rotation_from_axes(x_dir, y_dir, z_dir)

    # Edge selection fallback
    if isinstance(subobj, Part.Edge):
        try:
            p0 = subobj.Vertexes[0].Point
            p1 = subobj.Vertexes[-1].Point
            edge_dir = _safe_norm(p1.sub(p0))
            if edge_dir is not None:
                # Keep fitting Z "up" in current modeling frame
                z_dir = App.Vector(0, 0, 1)
                if abs(edge_dir.dot(z_dir)) > 0.999:
                    z_dir = App.Vector(0, 1, 0)

                y_dir = _safe_norm(z_dir.cross(edge_dir))
                if y_dir is None:
                    return App.Rotation()
                z_dir = _safe_norm(edge_dir.cross(y_dir))
                if z_dir is None:
                    return App.Rotation()

                return _rotation_from_axes(edge_dir, y_dir, z_dir)
        except Exception:
            return App.Rotation()

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
            obj.Label = f"F_{fid}"
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

            App.Console.PrintMessage(f"[UnistrutWB] channel: {channel.Name if channel else None}\n")
            App.Console.PrintMessage(f"[UnistrutWB] picked_point: {picked_point}\n")
            App.Console.PrintMessage(f"[UnistrutWB] picked_subobj: {type(picked_subobj).__name__ if picked_subobj else None}\n")
            
            if channel and "SlotCenters" in channel.PropertiesList and channel.SlotCenters:
                centers = list(channel.SlotCenters)
                App.Console.PrintMessage(f"[UnistrutWB] slotcenters_count: {len(centers)}\n")

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
                rot = fitting_rotation_from_selection(picked_subobj, channel)

                App.Console.PrintMessage(f"[UnistrutWB] guess: {guess}\n")
                App.Console.PrintMessage(f"[UnistrutWB] chosen_slot: {slot}\n")

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
