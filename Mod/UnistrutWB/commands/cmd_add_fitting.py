# -*- coding: utf-8 -*-
import FreeCAD as App
import FreeCADGui as Gui

from ..core.loader import Catalog
from ..core.fittings import build_fitting_shape, add_mate_markers

try:
    from PySide2 import QtWidgets
except Exception:
    from PySide import QtGui as QtWidgets  # type: ignore

class _CmdAddFitting:
    def GetResources(self):
        return {"MenuText": "Add Fitting", "ToolTip": "Place a fitting from datastore (placeholder geometry in v0.1)"}

    def Activated(self):
        cat = Catalog.load()
        dlg = QtWidgets.QDialog()
        dlg.setWindowTitle("Unistrut: Add Fitting")
        layout = QtWidgets.QVBoxLayout(dlg)

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

            doc.recompute()
            dlg.accept()

        btns.accepted.connect(ok)
        btns.rejected.connect(dlg.reject)
        dlg.exec_()

Gui.addCommand("Unistrut_AddFitting", _CmdAddFitting())
