# -*- coding: utf-8 -*-
import FreeCAD as App
import FreeCADGui as Gui
import Part

from ..core.loader import Catalog
from ..core.fittings import build_fitting_shape, add_mate_markers

try:
    from PySide2 import QtWidgets
except Exception:
    from PySide import QtGui as QtWidgets  # type: ignore

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
        shape = build_splice_plate(SPLICE_PLATE_4H)
        obj = doc.addObject("Part::Feature", "SplicePlate")
        obj.Shape = shape
    
        # Minimal metadata for BOM (MVP)
        obj.addProperty("App::PropertyString", "UnistrutType", "UnistrutWB", "Type tag")
        obj.UnistrutType = "fitting"
        obj.addProperty("App::PropertyString", "FittingId", "UnistrutWB", "Fitting ID")
        obj.FittingId = SPLICE_PLATE_4H["id"]

        # MVP placement: drop near origin or near selection if present
        obj.Placement = App.Placement(App.Vector(0, 0, 0), App.Rotation())
        doc.recompute()


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

            doc.recompute()
            dlg.accept()

        btns.accepted.connect(ok)
        btns.rejected.connect(dlg.reject)
        dlg.exec_()

Gui.addCommand("Unistrut_AddFitting", _CmdAddFitting())
