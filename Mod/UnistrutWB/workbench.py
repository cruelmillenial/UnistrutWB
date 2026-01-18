# -*- coding: utf-8 -*-
import FreeCADGui as Gui

class UnistrutWorkbench(Gui.Workbench):
    MenuText = "UnistrutWB"
    ToolTip = "Unistrut catalog-driven metal framing workbench"
    Icon = ""

    def Initialize(self):
        # Import commands (register with FreeCADGui)
        from .commands import cmd_new_channel, cmd_add_fitting, cmd_snap_mate, cmd_bom_export  # noqa: F401

        self.list = [
            "Unistrut_NewChannel",
            "Unistrut_AddFitting",
            "Unistrut_SnapMate",
            "Unistrut_BOMExport",
        ]
        self.appendToolbar("UnistrutWB", self.list)
        self.appendMenu("UnistrutWB", self.list)

    def GetClassName(self):
        return "Gui::PythonWorkbench"
