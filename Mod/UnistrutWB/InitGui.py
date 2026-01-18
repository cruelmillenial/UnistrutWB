import os
import sys
import FreeCAD as App
import FreeCADGui as Gui

# Snap-safe base path
user_mod = os.path.join(App.ConfigGet("UserAppData"), "Mod")

# Candidate paths that might contain the UnistrutWB package
candidates = [
    user_mod,                                   # .../common/Mod
    os.path.join(user_mod, "UnistrutWB"),       # .../common/Mod/UnistrutWB
]

for p in candidates:
    if p not in sys.path:
        sys.path.insert(0, p)

# Try imports in both possible layouts
UnistrutWorkbench = None

try:
    # Flat layout: .../Mod/UnistrutWB/workbench.py
    from UnistrutWB.workbench import UnistrutWorkbench
except Exception:
    # Nested layout: .../Mod/UnistrutWB/UnistrutWB/workbench.py
    from UnistrutWB.UnistrutWB.workbench import UnistrutWorkbench

wb = UnistrutWorkbench()
name = getattr(wb, "Name", wb.__class__.__name__)
if name not in Gui.listWorkbenches():
    Gui.addWorkbench(wb)