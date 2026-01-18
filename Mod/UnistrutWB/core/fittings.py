"""
Fitting placement + placeholder geometry.

For v0.1 we implement a simple "plate" placeholder, plus mate frames encoded as datum
features (visual markers). Later replace with true catalog-derived solids.
"""
from __future__ import annotations
from typing import Dict, Any, Tuple

import FreeCAD as App
import Part

def build_fitting_shape(fitting: Dict[str, Any]) -> Part.Shape:
    # Placeholder: L-plate-ish box
    t = float(fitting["thickness"]["mm"])
    # fixed envelope for visibility
    a = 50.0
    b = 50.0
    plate = Part.makeBox(a, b, t)
    return plate

def add_mate_markers(obj, fitting: Dict[str, Any]) -> None:
    # Visual only: store mate frame names in properties
    if not obj.PropertiesList:
        return
    frames = fitting.get("mate_frames", [])
    obj.addProperty("App::PropertyStringList", "MateFrames", "Unistrut").MateFrames = [f.get("id","") for f in frames]
