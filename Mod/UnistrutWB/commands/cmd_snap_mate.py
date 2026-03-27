# -*- coding: utf-8 -*-
import FreeCADGui as Gui
from ..core.mates import snap_placement

try:
    from PySide import QtGui as QtWidgets  # type: ignore
except Exception:
    from PySide2 import QtWidgets

class _CmdSnapMate:
    def GetResources(self):
        return {"MenuText": "Snap/Mate", "ToolTip": "Snap placement of one object to another (v0.1 simple placement copy)"}

    def Activated(self):
        sel = Gui.Selection.getSelection()
        if len(sel) != 2:
            QtWidgets.QMessageBox.warning(None, "Unistrut Snap/Mate", "Select exactly 2 objects: source then target.")
            return
        src, dst = sel[0], sel[1]
        snap_placement(src, dst)

Gui.addCommand("Unistrut_SnapMate", _CmdSnapMate())
