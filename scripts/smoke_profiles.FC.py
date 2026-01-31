from UnistrutWB.core import profiles
import importlib
importlib.reload(profiles)

p = {"geometry": {"width":{"mm":41.275}, "height":{"mm":20.6375}, "thickness":{"mm":1.905}}}

s = profiles.build_channel(p, 1000.0, mode="simple")
d = profiles.build_channel(p, 1000.0, mode="detailed")

p_lipped = {
    "geometry": {
        "width": {"mm": 41.275},
        "height": {"mm": 20.6375},
        "thickness": {"mm": 1.905},
        "profile_spec": {
            "kind": "u_channel_lipped",
            "t": {"mm": 1.905},
            "lip_return": {"mm": 9.525},
            "inside_radius": {"mm": 1.524},  # ignored for now
        },
    }
}
u = profiles.build_channel(p_lipped, 1000.0, mode="simple")
spec = p_lipped["geometry"]["profile_spec"]
print("lip_return_mm:", spec["lip_return"]["mm"])
print("lipped BB:", u.BoundBox.XLength, u.BoundBox.YLength, u.BoundBox.ZLength)
print("lipped V:", u.Volume)
print("simple BB:", s.BoundBox.XLength, s.BoundBox.YLength, s.BoundBox.ZLength)
print("detail BB:", d.BoundBox.XLength, d.BoundBox.YLength, d.BoundBox.ZLength)
print("delta V:", d.Volume - s.Volume)
