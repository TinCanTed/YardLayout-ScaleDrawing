"""
layout_data.py

Defines data structures used for representing a yard layout, including
objects like the house, shed, well, and septic tank. Also provides
methods to convert data to/from dictionaries and handle JSON file I/O.
"""

import json
from dataclasses import dataclass, asdict, field
from typing import Optional, Dict

# Normalize any name to a canonical role if possible
try:
    # If ui_palette is available, reuse its normalizer
    from ui_palette import role_for  # returns "house" | "shed" | "well" | "septic" | None
except Exception:
    # Fallback (keeps layout_data independent)
    def role_for(name: str) -> str | None:
        if not name:
            return None
        s = str(name).strip().lower()
        if "house" in s:
            return "house"
        if "shed" in s:
            return "shed"
        if "well" in s:
            return "well"
        if "septic" in s:
            return "septic"
        return None


@dataclass
class RectangleObject:
    """
    Represents a rectangular object in the layout, such as a house or shed.

    Attributes:
        name (str): The name of the object.
        width (float): Width in feet.
        height (float): Height in feet.
        x (Optional[float]): X-coordinate (in feet) from the left boundary.
        y (Optional[float]): Y-coordinate (in feet) from the top boundary.
    """
    name: str
    width: float
    height: float
    x: Optional[float] = None
    y: Optional[float] = None

    def to_dict(self):
        """Converts the object to a dictionary."""
        return asdict(self)

@dataclass
class PointObject:
    """
    Represents a point-like object in the layout, such as a well or septic tank.

    Attributes:
        name (str): The name of the object.
        x (Optional[float]): X-coordinate (in feet).
        y (Optional[float]): Y-coordinate (in feet).
    """
    name: str
    x: Optional[float] = None
    y: Optional[float] = None

    def to_dict(self):
        """Converts the object to a dictionary."""
        return asdict(self)

@dataclass
class LayoutData:
    """
    Represents the entire layout, including boundaries and all objects.

    Attributes:
        front (float): Distance to front boundary in feet.
        back (float): Distance to back boundary in feet.
        left (float): Distance to left boundary in feet.
        right (float): Distance to right boundary in feet.
        house (RectangleObject): House dimensions and position.
        shed (RectangleObject): Shed dimensions and position.
        well (PointObject): Well position.
        septic (PointObject): Septic tank position.
    """
    front: float
    back: float
    left: float
    right: float
    house: Optional[RectangleObject]
    shed: Optional[RectangleObject]
    well:  Optional[PointObject]  = field(default_factory=lambda: PointObject(name="Well"))
    septic: Optional[PointObject] = field(default_factory=lambda: PointObject(name="Septic Tank"))

    def to_dict(self):
        """Serialize the layout and omit objects that aren't included."""
        objs = {}

        def include_rect(r):
            return (
                r is not None
                and r.x is not None and r.y is not None
                and r.width is not None and r.height is not None
                and r.width > 0 and r.height > 0
            )

        def include_point(p):
            return p is not None and p.x is not None and p.y is not None

        if include_rect(self.house):
            objs["house"] = self.house.to_dict()
        if include_rect(self.shed):
            objs["shed"] = self.shed.to_dict()
        if include_point(self.well):
            objs["well"] = self.well.to_dict()
        if include_point(self.septic):
            objs["septic"] = self.septic.to_dict()

        return {
            "boundary": {
            "front": self.front,
            "back": self.back,
            "left": self.left,
            "right": self.right
        },
        "objects": objs
    }
    
    @staticmethod
    def from_dict(data: Dict):
        """
        Creates a LayoutData object from a dictionary (objects may be omitted).
        """
        b = data["boundary"]
        o = data.get("objects", {})

        house  = RectangleObject(**o["house"])  if "house"  in o else None
        shed   = RectangleObject(**o["shed"])   if "shed"   in o else None
        well   = PointObject(**o["well"])       if "well"   in o else None
        septic = PointObject(**o["septic"])     if "septic" in o else None

        return LayoutData(
            front=b["front"],
            back=b["back"],
            left=b["left"],
            right=b["right"],
            house=house,
            shed=shed,
            well=well,
            septic=septic,
        )

    def save_to_json(self, filepath: str):
        """
        Saves the layout to a JSON file.

        Args:
            filepath (str): Path to the output JSON file.
        """
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=4)

    @staticmethod
    def load_from_json(filepath: str):
        """
        Loads layout data from a JSON file.

        Args:
            filepath (str): Path to the JSON file.

        Returns:
            LayoutData: The loaded layout.
        """
        with open(filepath, 'r') as f:
            data = json.load(f)
            return LayoutData.from_dict(data)

    def resolve_obj(self, name_or_role: str):
        """
        Resolve an object by canonical role ('house'/'shed'/'well'/'septic')
        or by exact display name (e.g., 'Septic Tank'). Returns the object or None.
        """
        r = role_for(name_or_role)
        if r:
            return getattr(self, r, None)

        target_name = str(name_or_role)
        for obj in (self.house, self.shed, self.well, self.septic):
            if obj is not None and getattr(obj, "name", None) == target_name:
                return obj
        return None

    def update_object_position(self, name: str, x: float, y: float):
        """
        Update by display name (e.g., 'Septic Tank') OR by role alias ('septic').
        """
        obj = self.resolve_obj(name)
        if obj is None:
            raise ValueError(f"Unknown object name: {name}")
        obj.x = x
        obj.y = y


    def edit_dimensions(self, name: str, width: float, height: float):
        """
        Edit dimensions of a rectangular object by display name or role.
        """
        obj = self.resolve_obj(name)
        if obj is None or not isinstance(obj, RectangleObject):
            raise ValueError(f"Unknown rectangle object: {name}")
        obj.width = width
        obj.height = height

