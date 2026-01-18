"""
Mate/snap helpers.

v0.1: "align selected object A's Placement to object B" by matching their local axes.
Upgrade:
- use LCS/datum planes
- align to channel hole/slot pitch (from mapping_hole_series.json) when available
"""
from __future__ import annotations
from typing import Tuple
import FreeCAD as App

def snap_placement(src_obj, dst_obj) -> None:
    if src_obj is None or dst_obj is None:
        raise ValueError("Need two objects")
    src_obj.Placement = dst_obj.Placement
