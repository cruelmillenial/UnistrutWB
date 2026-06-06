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


CHANNEL_VIEWER_GAP_MM = 25.0


def _existing_profile_count(doc):
    if doc is None:
        return 0
    count = 0
    for existing in doc.Objects:
        if getattr