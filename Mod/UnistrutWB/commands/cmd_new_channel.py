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
            "MenuText": "New