# ui_palette.py
# Single source of truth for object colors in both the editor (Tk) and PDF.

from typing import Tuple

# Hex colors for Tkinter (canvas)
HEX = {
    "house":  "#3380E6",  # ~ (0.20, 0.50, 0.90)
    "shed":   "#804D1A",  # ~ (0.50, 0.30, 0.10)
    "well":   "#00B300",  # ~ (0.00, 0.70, 0.00)
    "septic": "#B30000",  # ~ (0.70, 0.00, 0.00)
}

def _hex_to_rgb01(hex_str: str) -> Tuple[float, float, float]:
    """#RRGGBB -> (r,g,b) in 0..1 floats."""
    s = hex_str.lstrip("#")
    r = int(s[0:2], 16) / 255.0
    g = int(s[2:4], 16) / 255.0
    b = int(s[4:6], 16) / 255.0
    return (r, g, b)

# PDF colors (0..1 floats) derived from HEX so both stay in sync.
PDF = {name: _hex_to_rgb01(hx) for name, hx in HEX.items()}

