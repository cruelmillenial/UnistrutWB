# -*- coding: utf-8 -*-
import FreeCADGui as Gui
from ..core.bom import export_csv

try:
    from PySide2 import QtWidgets
except Exception:
    from PySide import QtGui as QtWidgets  # type: ignore

class _CmdBOMExport:
    def GetResources(self):
        return {"MenuText": "BOM Export", "ToolTip": "Export BOM/Cut list as CSV"}

    def Activated(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(None, "Save BOM CSV", "unistrut_bom.csv", "CSV (*.csv)")
        if not path:
            return
        export_csv(path)
        QtWidgets.QMessageBox.information(None, "Unistrut BOM Export", f"Saved:\n{path}")

Gui.addCommand("Unistrut_BOMExport", _CmdBOMExport())
