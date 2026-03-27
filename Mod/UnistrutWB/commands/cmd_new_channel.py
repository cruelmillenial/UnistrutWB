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

        btns = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        layout.addWidget(btns)

        def ok():
            pid = combo.currentText()
            prof = cat.get_profile(pid)
            shp = build_channel(prof, float(length.value()), mode.currentText().lower())

            doc = App.ActiveDocument or App.newDocument("UnistrutWB")
            obj = doc.addObject("Part::Feature", f"U_{pid}")
            obj.Shape = shp

            obj.addProperty("App::PropertyString", "UnistrutType", "Unistrut").UnistrutType = "profile"
            obj.addProperty("App::PropertyString", "ProfileId", "Unistrut").ProfileId = pid
            obj.addProperty("App::PropertyLength", "Length", "Unistrut").Length = float(length.value())
            obj.addProperty("App::PropertyString", "Finish", "Unistrut").Finish = finish.text().strip() or "EG"
            obj.addProperty("App::PropertyString", "Mode", "Unistrut").Mode = mode.currentText()

            if "SlotCenters" not in obj.PropertiesList:
                obj.addProperty(
                    "App::PropertyVectorList",
                    "SlotCenters",
                    "Unistrut",
                    "Computed slot center points",
                )

            geom = prof.get("geometry") or {}
            series = resolve_piercing_spec(prof)

            centers = []
            if series:
                centers = compute_slot_centers(
                    series,
                    float(length.value()),
                    width_mm=float(geom["width"]["mm"]),
                )

            obj.SlotCenters = [App.Vector(x, y, z) for (x, y, z) in centers]

            doc.recompute()
            dlg.accept()

        btns.accepted.connect(ok)
        btns.rejected.connect(dlg.reject)
        dlg.exec_()


Gui.addCommand("Unistrut_NewChannel", _CmdNewChannel())
