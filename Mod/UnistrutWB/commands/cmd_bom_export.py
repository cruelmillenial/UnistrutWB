# -*- coding: utf-8 -*-
import FreeCADGui as Gui
from ..core import bom

try:
    from PySide import QtGui as QtWidgets  # type: ignore
except Exception:
    from PySide2 import QtWidgets

class _CmdBOMExport:
    def GetResources(self):
        return {"MenuText": "BOM Export", "ToolTip": "Export BOM/Cut list as CSV"}

    def Activated(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(None, "Save BOM CSV", "unistrut_bom.csv", "CSV (*.csv)")
        if not path:
            return
        bom.export_csv(path)
        QtWidgets.QMessageBox.information(None, "Unistrut BOM Export", f"Saved:\n{path}")

Gui.addCommand("Unistrut_BOMExport", _CmdBOMExport())
