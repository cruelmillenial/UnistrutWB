# -*- coding: utf-8 -*-
import FreeCAD as App
import FreeCADGui as Gui

from ..core.loader import Catalog
from ..core.profiles import build_channel
from ..core.holes import resolve_piercing_spec, compute_slot_centers

try:
    from PySide import QtGui as QtWidgets
except Exception:
    from PySide2 import QtWidgets


def _next_profile_authoring_placement(
    doc,
    width_mm: float,
    gap_mm: float = 25.0,
) -> App.Placement:
    """
    Viewer-only authoring convenience.

    New channel profile objects should not spawn directly inside earlier
    channel profile objects. This is intentionally not Assembly placement,
    mating, constraint solving, or mechanical design intent.
    """
    if doc is None:
        return App.Placement()

    profile_count = 0
    for existing in getattr(doc, "Objects", []):
        if getattr(existing, "UnistrutType", "") == "profile":
            profile_count += 1

    if profile_count <= 0:
        return App.Placement()

    step_mm = max(float(width_mm), 1.0) + float(gap_mm)
    return App.Placement(
        App.Vector(0, profile_count * step_mm, 0),
        App.Rotation(),
    )


class _CmdNewChannel:
    def GetResources(self):
        return {
            "MenuText": "New Channel",
            "ToolTip": "Create a parametric Unistrut channel from datastore",
        }

    def Activated(self):
        cat = Catalog.load()
        dlg = QtWidgets.QDialog()
        dlg.setWindowTitle("Unistrut: New Channel")

        layout = QtWidgets.QVBoxLayout(dlg)

        combo = QtWidgets.QComboBox()
        combo.addItems(cat.list_profiles())
        layout.addWidget(combo)

        length = QtWidgets.QDoubleSpinBox()
        length.setRange(1.0, 100000.0)
        length.setValue(1000.0)
        length.setSuffix(" mm")
        layout.addWidget(length)

        mode = QtWidgets.QComboBox()
        mode.addItems(["simple", "detailed"])
        layout.addWidget(mode)

        finish = QtWidgets.QLineEdit("EG")
        finish.setPlaceholderText("Finish code (e.g., EG, HG, GR)")
        layout.addWidget(finish)

        piercing = QtWidgets.QComboBox()
        piercing.addItem("Profile default", "__profile__")
        piercing.addItem("Plain / solid", "__plain__")
        piercing.addItem("T slotted", "T")
        layout.addWidget(piercing)

        hole_clearance = QtWidgets.QLineEdit("0.5")
        hole_clearance.setPlaceholderText("Hole / clearance size in inches, metadata only")
        layout.addWidget(hole_clearance)

        btns = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        layout.addWidget(btns)

        def ok():
            pid = combo.currentText()
            prof = cat.get_profile(pid)
            geom = prof.get("geometry") or {}
            selected_piercing = piercing.currentData()

            prof_for_channel = dict(prof)
            geom_for_channel = dict(geom)

            if selected_piercing == "__plain__":
                piercing_for_channel = dict(geom_for_channel.get("piercing") or {})
                piercing_for_channel["series"] = None
                piercing_for_channel["template"] = None
                piercing_for_channel["overrides"] = {}
                geom_for_channel["piercing"] = piercing_for_channel
            elif selected_piercing not in ("__profile__", None):
                piercing_for_channel = dict(geom_for_channel.get("piercing") or {})
                piercing_for_channel["series"] = selected_piercing
                piercing_for_channel["template"] = None
                piercing_for_channel["overrides"] = {}
                geom_for_channel["piercing"] = piercing_for_channel

            prof_for_channel["geometry"] = geom_for_channel
            shp = build_channel(prof_for_channel, float(length.value()), mode.currentText().lower())

            doc = App.ActiveDocument or App.newDocument("UnistrutWB")

            try:
                width_mm = float(geom["width"]["mm"])
            except Exception:
                width_mm = 50.0
            obj = doc.addObject("Part::Feature", f"U_{pid}")
            obj.Label = f"U_{pid}"
            obj.Shape = shp
            obj.Placement = _next_profile_authoring_placement(doc, width_mm)

            obj.addProperty("App::PropertyString", "UnistrutType", "Unistrut").UnistrutType = "profile"
            obj.addProperty("App::PropertyString", "ProfileId", "Unistrut").ProfileId = pid
            obj.addProperty("App::PropertyLength", "Length", "Unistrut").Length = float(length.value())
            obj.addProperty("App::PropertyString", "Finish", "Unistrut").Finish = finish.text().strip() or "EG"
            obj.addProperty("App::PropertyString", "Mode", "Unistrut").Mode = mode.currentText()
            obj.addProperty("App::PropertyString", "PiercingPreset", "Unistrut").PiercingPreset = piercing.currentData()
            obj.addProperty("App::PropertyString", "HoleClearanceIn", "Unistrut").HoleClearanceIn = hole_clearance.text().strip()

            if "SlotCenters" not in obj.PropertiesList:
                obj.addProperty(
                    "App::PropertyVectorList",
                    "SlotCenters",
                    "Unistrut",
                    "Computed slot center points",
                )

            series = resolve_piercing_spec(prof_for_channel)

            centers = []
            if series and "slot_pattern" in series:
                centers = compute_slot_centers(
                    series,
                    float(length.value()),
                    width_mm=float(geom_for_channel["width"]["mm"]),
                )

            obj.SlotCenters = [App.Vector(x, y, z) for (x, y, z) in centers]

            doc.recompute()
            dlg.accept()

        btns.accepted.connect(ok)
        btns.rejected.connect(dlg.reject)
        dlg.exec_()


Gui.addCommand("Unistrut_NewChannel", _CmdNewChannel())
