# TESTING.md

## Purpose
Quick, repeatable checks to ensure **distance labels** (Left/Right/Back/Front) stay correct on the **canvas** and in the **PDF export** (nearest property edges; no “through-the-shed” leakage). Prevents regressions when code changes.

---

## Setup
- Yard: **front = 200**, **left = 300** (width × height in ft)
- Shed (rect): **width = 30**, **height = 10**
- Verify on **canvas**, then **Export to PDF**, and compare results.

Legend for expected distances (in feet):
- **Left**  = `x`
- **Right** = `yard_width - (x + width)` = `200 - (x + 30)`
- **Front** (bottom) = `y`
- **Back**  (top)    = `yard_height - (y + height)` = `300 - (y + 10)`

---

## Core test matrix

| Case | Shed (x, y) | Expected (L, R, B, F) |
|---|---|---|
| A: Center-ish | (85, 145) | L=85, R=85, B=145, F=145 |
| B1: Touch Left | (0, 210) | L=0, R=170, B=80, F=210 |
| B2: Touch Right | (170, 210) | L=170, R=0, B=80, F=210 |
| B3: Touch Back (top) | (110, 290) | L=110, R=60, B=0, F=290 |
| B4: Touch Front (bottom) | (110, 0) | L=110, R=60, B=290, F=0 |
| C1: Corner TL | (0, 290) | L=0, R=170, B=0, F=290 |
| C2: Corner BR | (170, 0) | L=170, R=0, B=290, F=0 |

**Pass criteria (canvas):**
- Numbers match the table above.
- Horizontal dimension lines (Left/Right) draw from **shed top edge** to yard sides.
- **Back** label draws **yard top → shed top**.
- **Front** label draws **shed bottom → yard bottom**.

**Pass criteria (PDF):**
- Same numbers and line placements as canvas.

---

## Manual steps (each case)

1) Set yard to **200 × 300**.
2) Set shed **w=30, h=10**, then place at the case’s `(x, y)`.
3) Observe canvas distances; compare to table.
4) **Export to PDF**:
   - Open the PDF and verify numbers match the canvas.
   - Verify line placements (as in “Pass criteria”).

Repeat for all rows in the test matrix.

---

## Rotation & drag-drop sanity
These catch common edge bugs:

1) Place shed at **(110, 210)**, rotate 90°, drag slightly, rotate back.
   - Distances should still compute as nearest edges (no “hop”/flip mistakes).
2) Save layout → reload → drag a bit → **Export PDF**.
   - Canvas and PDF should match.

---

## After changes checklist (run these every time you modify related code)
- If you edit **`layout_canvas.py`** (guide math/placement), run **canvas** checks for A, B1–B4.
- If you edit **`print_export.py`** (PDF lines/labels), run **PDF** checks for A, B1–B4.
- If you touch **coordinate transforms** or **rotation logic**, add **Rotation & drag-drop sanity**.

---

## Troubleshooting quick hits

- **Front/Back swapped in PDF only** → In `print_export.py`, ensure:
  - `yard_top_y = ft_to_pt_y(0)` and `yard_bottom_y = ft_to_pt_y(yard_height_ft)`
  - `obj_top_y    = ft_to_pt_y(yard_height_ft - (y + h))`
  - `obj_bottom_y = ft_to_pt_y(yard_height_ft - y)`
  - Back dim line: `yard_top_y → obj_top_y`
  - Front dim line: `obj_bottom_y → yard_bottom_y`
- **Crash on export after drag** → Make sure:
  - `export_to_pdf(..., **_ignored)` accepts extra kwargs (e.g., `show_distance_guides`).
  - Draw functions guard `None` objects:
    - `draw_rect` checks `x, y, width, height, name` exist.
    - `draw_point` checks `x, y, name` exist.
- **Numbers differ between canvas and PDF** → Confirm both use:
  - Yard width = `layout.front`, yard height = `layout.left`.
  - Distances computed as in the formulas above (nearest edges).
- **Labels drawn on wrong side** → Check `outside_offset` in `draw_dim_line` and the chosen anchor edges (shed **top** for horizontal lines; shed **left** for verticals is fine as long as yard edges are correct).

---

## Tiny helper (optional): print expected distances
Use in a REPL to sanity-calc numbers quickly.

```python
def dist(yard_w, yard_h, x, y, w, h):
    left = x
    right = yard_w - (x + w)
    back = yard_h - (y + h)
    front = y
    return left, right, back, front

# Examples
print(dist(200, 300, 85, 145, 30, 10))    # (85, 85, 145, 145)
print(dist(200, 300, 0, 210, 30, 10))     # (0, 170, 80, 210)
print(dist(200, 300, 170, 210, 30, 10))   # (170, 0, 80, 210)
print(dist(200, 300, 110, 290, 30, 10))   # (110, 60, 0, 290)
print(dist(200, 300, 110, 0, 30, 10))     # (110, 60, 290, 0)
```

---

## Release hygiene (optional)
When all tests pass:
```powershell
git tag -a v0.7.1 -m "Canvas & PDF distance labels verified"
git push --tags
```
