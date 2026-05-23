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

def classify_face(subobj, channel=None):
    if not isinstance(subobj, Part.Face):
        return None

    n = _pick_face_normal(subobj)
    if n is None:
        return None

    world_y = App.Vector(0, 1, 0)
    world_z = App.Vector(0, 0, 1)

    face_class = "other"
    if abs(n.dot(world_z)) > 0.9:
        face_class = "z_face"
    elif abs(n.dot(world_y)) > 0.9:
        face_class = "y_face"

    # Provisional P4100/P-series convention:
    # open/channel-nut side is the low-Z side of the generated channel.
    # Include the sheet-thickness/lip faces near the opening.
    if face_class == "z_face" and channel is not None:
        try:
            face_z = subobj.BoundBox.Center.z
            channel_zmin = channel.Shape.BoundBox.ZMin

            App.Console.PrintMessage(
                f"[UnistrutWB] face_z: {face_z}, channel_zmin: {channel_zmin}\n"
            )

            if abs(face_z - channel_zmin) < 0.5:
                return "open_face"
        except Exception:
            pass

    return face_class

def _safe_norm(v):
    try:
        if v.Length == 0:
            return None
        out = App.Vector(v.x, v.y, v.z)
        out.normalize()
        return out
    except Exception:
        return None

def fitting_anchor_offset(fitting, picked_subobj, rot):
    return App.Vector(0, 0, 0)

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

def fitting_rotation_from_selection(subobj, channel=None, fitting=None, semantic_face_class=None):
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

        # Normalize opposing broad Z faces to one mounting convention so Add Fitting
        # behaves predictably on either broad side of the channel.
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

        effective_face_class = semantic_face_class or face_class

        App.Console.PrintMessage(f"[UnistrutWB] face_normal: {z_dir}\n")
        App.Console.PrintMessage(
            f"[UnistrutWB] rotation_face_class: {face_class}"
            f" / semantic_face_class: {semantic_face_class}"
            f" / effective_face_class: {effective_face_class}\n"
        )

        if effective_face_class == "y_face":
            x_dir = App.Vector(1, 0, 0)
            y_dir = _safe_norm(z_dir.cross(x_dir))
            if y_dir is None:
                return App.Rotation()

            App.Console.PrintMessage(f"[UnistrutWB] x_dir: {x_dir}\n")
            App.Console.PrintMessage(f"[UnistrutWB] y_dir: {y_dir}\n")
            App.Console.PrintMessage(f"[UnistrutWB] z_dir: {z_dir}\n")

            rot = _rotation_from_axes(x_dir, y_dir, z_dir)

            if fitting and fitting.get("type") == "angle_plate":
                rot = rot.multiply(App.Rotation(z_dir, 90))

            return rot

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

        rot = _rotation_from_axes(x_dir, y_dir, z_dir)

        if fitting and fitting.get("type") == "angle_plate":
            rot = rot.multiply(App.Rotation(z_dir, 90))

        return rot

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

def _add_string_prop(obj, name, value):
    if name not in obj.PropertiesList:
        obj.addProperty("App::PropertyString", name, "Unistrut")
    setattr(obj, name, "" if value is None else str(value))


def _add_int_prop(obj, name, value):
    if value is None:
        return
    if name not in obj.PropertiesList:
        obj.addProperty("App::PropertyInteger", name, "Unistrut")
    setattr(obj, name, int(value))


def _add_float_prop(obj, name, value):
    if value is None:
        return
    if name not in obj.PropertiesList:
        obj.addProperty("App::PropertyFloat", name, "Unistrut")
    setattr(obj, name, float(value))


def add_catalog_metadata(obj, fitting):
    _add_string_prop(obj, "FamilyId", fitting.get("family_id", ""))
    _add_string_prop(obj, "FittingType", fitting.get("type", ""))
    _add_string_prop(obj, "Category", fitting.get("category", ""))
    _add_string_prop(obj, "DisplayGroup", fitting.get("display_group", ""))
    _add_string_prop(obj, "VariantLabel", fitting.get("variant_label", ""))
    _add_string_prop(obj, "HardwarePreset", fitting.get("hardware_preset", ""))

    _add_int_prop(obj, "HoleCount", fitting.get("hole_count"))
    _add_float_prop(obj, "HoleDiameterIn", fitting.get("default_hole_diameter_in"))

    opts = fitting.get("hole_diameter_options_in", [])
    _add_string_prop(
        obj,
        "HoleDiameterOptionsIn",
        ", ".join(str(x) for x in opts),
    )

class _CmdAddFitting:
    def GetResources(self):
        return {"MenuText": "Add Fitting", "ToolTip": "Place a fitting from datastore (placeholder geometry in v0.1)"}

    def Activated(self):
        cat = Catalog.load(force_reload=True)
        for fitting_id in cat.list_fittings():
            f = cat.get_fitting(fitting_id)
            App.Console.PrintMessage(
                f"[UnistrutWB] fitting {fitting_id}: "
                f"display_group={f.get('display_group')} "
                f"category={f.get('category')} "
                f"variant={f.get('variant_label')}\n"
            )
        sel_ex_initial = Gui.Selection.getSelectionEx()
        sel_initial = Gui.Selection.getSelection()
        dlg = QtWidgets.QDialog()
        dlg.setWindowTitle("Unistrut: Add Fitting")
        layout = QtWidgets.QVBoxLayout(dlg)
        doc = App.ActiveDocument
        if doc is None:
            doc = App.newDocument()

        fitting_groups = {}

        for fitting_id in cat.list_fittings():
            fitting = cat.get_fitting(fitting_id)

            group_label = (
                fitting.get("display_group")
                or fitting.get("category")
                or "Other"
            )

            variant_label = (
                fitting.get("variant_label")
                or fitting.get("name")
                or fitting_id
            )

            fitting_groups.setdefault(group_label, []).append(
                (variant_label, fitting_id)
            )

        category_combo = QtWidgets.QComboBox()
        variant_combo = QtWidgets.QComboBox()

        for group_label in sorted(fitting_groups.keys()):
            category_combo.addItem(group_label, group_label)

        layout.addWidget(category_combo)
        layout.addWidget(variant_combo)


        def refresh_variant_combo():
            variant_combo.clear()

            group_label = category_combo.itemData(category_combo.currentIndex())
            variants = fitting_groups.get(group_label, [])

            for variant_label, fitting_id in sorted(variants):
                variant_combo.addItem(variant_label, fitting_id)


        category_combo.currentIndexChanged.connect(refresh_variant_combo)
        refresh_variant_combo()

        btns = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        layout.addWidget(btns)

        def ok():
            fid = variant_combo.itemData(variant_combo.currentIndex())
            if not fid:
                App.Console.PrintMessage(
                "[UnistrutWB] No fitting variant selected.\n"
            )
                return

            fitting = cat.get_fitting(fid)
            shp = build_fitting_shape(fitting)
            doc = App.ActiveDocument or App.newDocument("UnistrutWB")

            channel = None
            picked_point = None
            picked_subobj = None

            for s in sel_ex_initial:
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
                for s in sel_initial:
                    if getattr(s, "UnistrutType", "") == "profile":
                        channel = s
                        break

            App.Console.PrintMessage(f"[UnistrutWB] channel: {channel.Name if channel else None}\n")
            App.Console.PrintMessage(f"[UnistrutWB] picked_point: {picked_point}\n")
            App.Console.PrintMessage(
                f"[UnistrutWB] picked_subobj: {type(picked_subobj).__name__ if picked_subobj else None}\n"
            )

            use_selected_placement = channel is not None and picked_subobj is not None

            if channel is not None and picked_subobj is None:
                App.Console.PrintMessage(
                    "[UnistrutWB] Whole-object selection detected; creating fitting unplaced at origin.\n"
                )
                use_selected_placement = False

            if use_selected_placement:
                if not (channel and "SlotCenters" in channel.PropertiesList and channel.SlotCenters):
                    App.Console.PrintMessage(
                        "[UnistrutWB] No valid host profile / SlotCenters available for fitting placement.\n"
                    )
                    return

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

                placement = fitting.get("placement", {})
                supported_modes = placement.get("supported_modes", [])
                allowed_face_classes = placement.get("allowed_face_classes", [])
                slot_policy = placement.get("slot_policy", "nearest_slot_center")

                current_mode = "face_mount" if isinstance(picked_subobj, Part.Face) else None
                current_face_class = classify_face(picked_subobj, channel) if picked_subobj is not None else None
                App.Console.PrintMessage(f"[UnistrutWB] contract_face_class: {current_face_class}\n")

                if supported_modes and current_mode not in supported_modes:
                    App.Console.PrintMessage(
                        f"[UnistrutWB] Fitting {fid} does not support placement mode: {current_mode}\n"
                    )
                    return

                if allowed_face_classes and current_face_class not in allowed_face_classes:
                    App.Console.PrintMessage(
                        f"[UnistrutWB] Fitting {fid} does not support face class: {current_face_class}\n"
                    )
                    return

                App.Console.PrintMessage(f"[UnistrutWB] slot_policy: {slot_policy}\n")

                if slot_policy == "nearest_slot_center":
                    if current_face_class == "open_face":
                        slot = nearest_slot_center(centers, guess) or centers[0]
                    else:
                        # SlotCenters live on the open/channel-nut side.
                        # For non-open faces, honor the picked point instead.
                        slot = guess

                elif slot_policy == "picked_point":
                    slot = guess

                else:
                    App.Console.PrintMessage(
                        f"[UnistrutWB] Unsupported slot policy for {fid}: {slot_policy}\n"
                    )
                    return

                rot = fitting_rotation_from_selection(
                    picked_subobj,
                    channel,
                    fitting,
                    current_face_class,
                )

            else:
                guess = App.Vector(0, 0, 0)
                slot = App.Vector(0, 0, 0)
                rot = App.Rotation()
                current_face_class = None

                App.Console.PrintMessage(
                    "[UnistrutWB] No valid placement selection; creating fitting at origin.\n"
                )

            App.Console.PrintMessage(f"[UnistrutWB] guess: {guess}\n")
            App.Console.PrintMessage(f"[UnistrutWB] chosen_slot: {slot}\n")
            obj = doc.addObject("Part::Feature", f"F_{fid}")
            obj.Label = f"F_{fid}"
            obj.Shape = shp

            obj.addProperty("App::PropertyString", "UnistrutType", "Unistrut").UnistrutType = "fitting"
            obj.addProperty("App::PropertyString", "FittingId", "Unistrut").FittingId = fid

            add_catalog_metadata(obj, fitting)
            add_mate_markers(obj, fitting)

            offset = fitting_anchor_offset(fitting, picked_subobj, rot)
            place_base = slot.add(offset)

            App.Console.PrintMessage(f"[UnistrutWB] offset: {offset}\n")
            App.Console.PrintMessage(f"[UnistrutWB] place_base: {place_base}\n")

            obj.Placement = App.Placement(place_base, rot)

            if "HostProfile" not in obj.PropertiesList:
                obj.addProperty("App::PropertyString", "HostProfile", "Unistrut")

            obj.HostProfile = channel.Name if channel else ""

            doc.recompute()
            dlg.accept()

        btns.accepted.connect(ok)
        btns.rejected.connect(dlg.reject)
        dlg.exec_()

Gui.addCommand("Unistrut_AddFitting", _CmdAddFitting())
