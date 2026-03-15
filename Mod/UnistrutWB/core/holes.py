import Part
import FreeCAD as App


def apply_hole_series(
    solid,
    series,
    length_mm,
    *,
    width_mm=41.3,
    thickness_mm=1.9,
):
    """
    Apply a simple web slot series to a channel.

    Coordinate convention:
    - X = channel length
    - Y = channel width
    - Z = channel height

    This cuts slots through the web thickness (+Z), centered across width (Y).
    """

    pitch = float(series["pitch_mm"])
    offset = float(series.get("offset_mm", pitch / 2.0))

    # support either slot-style or round-hole-style input
    slot_len = float(series.get("slot_length_mm", series.get("diameter_mm", 14.0)))
    slot_w = float(series.get("slot_width_mm", series.get("diameter_mm", 14.0)))

    y_center = float(series.get("y_center_mm", width_mm / 2.0))
    eps = 0.05

    slots = []

    x = offset
    while x <= (length_mm - offset + 1e-6):
        slot = Part.makeBox(
            slot_len,
            slot_w,
            thickness_mm + 2 * eps,
        )
        slot.Placement = App.Placement(
            App.Vector(
                x - slot_len / 2.0,
                y_center - slot_w / 2.0,
                -eps,
            ),
            App.Rotation(),
        )
        slots.append(slot)
        x += pitch

    if not slots:
        return solid

    tool = Part.makeCompound(slots)
    return solid.cut(tool)