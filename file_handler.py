import os
import sys
import json
from  layout_data import LayoutData
from typing import Any

SAVE_DIR = os.path.expanduser("~/gui_scale_drawing/layouts")
os.makedirs(SAVE_DIR, exist_ok=True)

def resource_path(relative_path):
    """Get absolute path to resource (for dev and PyInstaller bundle)"""
    base_path = getattr(sys, "_MEIPASS", os.path.abspath("."))
    return os.path.join(base_path, relative_path)


def save_layout_to_file(layout: Any, filename: str):
    """Save either a LayoutData object (with .to_dict) or a raw dict to JSON safely."""
    # Build data first (may raise if to_dict missing)
    if hasattr(layout, "to_dict"):
        data = layout.to_dict()
    elif isinstance(layout, dict):
        data = layout
    else:
        raise TypeError("save_layout_to_file expects a LayoutData with .to_dict() or a dict.")

    # Only after we have data, open and write
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def load_layout_from_file(path):
    """Load a layout from a .json file at the given path and return (layout, path)."""
    full_path = resource_path(path)
    with open(full_path, "r") as f:
        data = json.load(f)
        layout = LayoutData.from_dict(data)
        return layout, path

