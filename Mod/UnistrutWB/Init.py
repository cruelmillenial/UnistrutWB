# -*- coding: utf-8 -*-
# FreeCAD Workbench init (GUI).

import FreeCADGui as Gui
from .workbench import UnistrutWorkbench

Gui.addWorkbench(UnistrutWorkbench())
