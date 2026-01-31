from UnistrutWB.core import profiles
import importlib
importlib.reload(profiles)

p = {"geometry": {"width":{"mm":41.275}, "height":{"mm":20.6375}, "thickness":{"mm":1.905}}}

s = profiles.build_channel(p, 1000.0, mode="simple")
d = profiles.build_channel(p, 1000.0, mode="detailed")

print("simple BB:", s.BoundBox.XLength, s.BoundBox.YLength, s.BoundBox.ZLength)
print("detail BB:", d.BoundBox.XLength, d.BoundBox.YLength, d.BoundBox.ZLength)
print("delta V:", d.Volume - s.Volume)
