from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib import colors
from ui_palette import PDF
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
import os

PDF_COLOR_DEBUG = True  # set False when done

PRINT_DIR = os.path.expanduser("~/gui_scale_drawing/print")
os.makedirs(PRINT_DIR, exist_ok=True)


def export_to_pdf(layout, filename, **_ignored):
    """Accept extra keyword args (e.g., show_distance_guides) for compatibility."""
    page_width, page_height = landscape(letter)  # 11 x 8.5 inches landscape
    margin = 0.5 * inch
    legend_height = 60  # space reserved at the bottom for the legend

    # In this project: width (X) == layout.front, height (Y) == layout.left
    yard_width_ft = layout.front     # Left <-> Right span
    yard_height_ft = layout.left     # Back (top) <-> Front (bottom) span

    # Scale to fit (respect margins and legend space)
    scale_x = (page_width - 2 * margin) / yard_width_ft
    scale_y = (page_height - 2 * margin - legend_height) / yard_height_ft
    scale = min(scale_x, scale_y)

    # Coordinate helpers (origin top-left of page area, to match LayoutCanvas)
    def ft_to_pt_x(x_ft: float) -> float:
        return margin + x_ft * scale

    def ft_to_pt_y(y_ft_from_top: float) -> float:
        # Convert a distance in feet measured DOWN from the yard's top edge
        # to page points (origin at top of page content area).
        return page_height - margin - y_ft_from_top * scale

    # Yard's top-left in page coords; rect drawn downward (positive height)
    layout_origin_x = margin
    layout_origin_y = ft_to_pt_y(yard_height_ft)

    c = canvas.Canvas(filename, pagesize=(page_width, page_height))
    c.setLineWidth(0.5)

    # Draw yard boundary
    c.rect(layout_origin_x, layout_origin_y, yard_width_ft * scale, yard_height_ft * scale)

    # Gridlines & axes labels
    def draw_pdf_grid():
        spacing_ft = 10
        # Vertical lines + top labels
        for ft in range(0, int(yard_width_ft) + 1, spacing_ft):
            x = ft_to_pt_x(ft)
            c.setStrokeColor(colors.lightgrey)
            top = ft_to_pt_y(0)  # top edge of yard
            bottom = ft_to_pt_y(yard_height_ft)  # bottom edge of yard
            c.line(x, top, x, bottom)

            c.setFillColor(colors.black)
            c.setFont("Helvetica", 6)
            label_y = ft_to_pt_y(0) + 5  # just inside the yard area
            c.drawCentredString(x, label_y, str(ft))

        # Horizontal lines + left labels
        for ft in range(0, int(yard_height_ft) + 1, spacing_ft):
            y = ft_to_pt_y(ft)
            c.setStrokeColor(colors.lightgrey)
            c.line(margin, y, margin + yard_width_ft * scale, y)
            c.setFillColor(colors.black)
            c.setFont("Helvetica", 6)
            c.drawRightString(margin - 4, y - 3, str(ft))

    draw_pdf_grid()

    # ==== Draw layout objects ====
    def draw_rect(obj, color):
        # Skip if object or required fields are missing
        if not obj or any(getattr(obj, k, None) is None for k in ("x", "y", "width", "height", "name")):
            return

        x = ft_to_pt_x(obj.x)
        # obj.y is distance from FRONT (bottom) boundary in feet.
        # For the rectangle, its TOP edge (distance from top boundary) is:
        #   top_ft = yard_height_ft - (obj.y + obj.height)
        y = ft_to_pt_y(yard_height_ft - obj.y - obj.height)
        w = obj.width * scale
        h = obj.height * scale

        c.setFillColor(color)
        # Draw upward (negative height) to keep inside the yard box math consistent
        c.rect(x, y, w, -h, fill=1)

        c.setFillColorRGB(1, 1, 1)
        c.setFont("Helvetica-Bold", 8)
        c.drawCentredString(x + w / 2, y - h / 2, obj.name)

    def draw_point(obj, color):
        if not obj or getattr(obj, "x", None) is None or getattr(obj, "y", None) is None or getattr(obj, "name", None) is None:
            return 

        x = ft_to_pt_x(obj.x)
        y = ft_to_pt_y(yard_height_ft - obj.y)
        r = 5
        c.setFillColor(color)
        c.circle(x, y, r, fill=1)
        c.setFillColorRGB(0, 0, 0)
        c.drawString(x + 6, y - 4, obj.name)

    def rect_ft(obj, yard_height_ft):
        L = obj.x
        R = obj.x + obj.width
        T = yard_height_ft - (obj.y + obj.height)
        B = yard_height_ft - obj.y
        return L, T, R, B

    def nearest_rect_point_ft(rect, px, py):
        L, T, R, B = rect
        qx = min(max(px, L), R)
        qy = min(max(py, T), B)
        return (qx, qy, px, py)

    def nearest_rect_rect_ft(A, Bx):
        LA, TA, RA, BA = A
        LB, TB, RB, BB = Bx
        if RA < LB:
            ax, bx = RA, LB
        elif RB < LA:
            ax, bx = LA, RB
        else:
            ax = bx = max(LA, LB) if min(RA, RB) >= max(LA, LB) else (LA + RA) / 2

        if BA < TB:
            ay, by = BA, TB
        elif BB < TA:
            ay, by = TA, BB
        else:
            ay = by = max(TA, TB) if min(BA, BB) >= max(TA, TB) else (TA + BA) / 2

        # overlapping both axes -> small vertical segment
        if (ax == bx) and (ay == by):
            ay = by = max(TA, TB)
        return (ax, ay, bx, by)

    def draw_obj_distance_line(qx_ft, qy_ft, px_ft, py_ft, rgb01, label):
        x1 = ft_to_pt_x(qx_ft) 
        y1 = ft_to_pt_y(qy_ft)
        x2 = ft_to_pt_x(px_ft) 
        y2 = ft_to_pt_y(py_ft)
        c.setStrokeColor(colors.Color(*rgb01))
        c.setFillColor(colors.Color(*rgb01))
        c.setLineWidth(1.2)
        c.line(x1, y1, x2, y2)
        # label
        mx, my = (x1 + x2) / 2.0, (y1 + y2) / 2.0
        c.setFont("Helvetica-Bold", 8)
        c.drawCentredString(mx, my - 8, label)
        # reset if you like:
        c.setStrokeColor(colors.black)
        c.setFillColor(colors.black)

    
    # Objects
    # was: draw_rect(layout.house, colors.Color(0.2, 0.5, 0.9)), now it copies the object colors from the PDF

    if PDF_COLOR_DEBUG and getattr(layout, "septic", None):
        print(f"[PDF COLOR DEBUG] septic PDF color {PDF['septic']}")
    draw_rect(layout.house, colors.Color(*PDF["house"]))
    draw_rect(layout.shed,  colors.Color(*PDF["shed"]))
    draw_point(layout.well,   colors.Color(*PDF["well"]))
    draw_point(layout.septic, colors.Color(*PDF["septic"]))

    # --- Object-to-object distances from Shed ---
    if getattr(layout, "shed", None) and layout.shed.x is not None:
        sL, sT, sR, sB = rect_ft(layout.shed, yard_height_ft)

        # Shed <-> Well
        if getattr(layout, "well", None) and layout.well.x is not None:
            wx, wy = layout.well.x, yard_height_ft - layout.well.y
            qx, qy, px, py = nearest_rect_point_ft((sL, sT, sR, sB), wx, wy)
            dist = ((qx - px)**2 + (qy - py)**2) ** 0.5
            draw_obj_distance_line(qx, qy, px, py, PDF["well"], f"Well {dist:.1f} ft")

        # Shed <-> Septic
        if getattr(layout, "septic", None) and layout.septic.x is not None:
            sx, sy = layout.septic.x, yard_height_ft - layout.septic.y
            qx, qy, px, py = nearest_rect_point_ft((sL, sT, sR, sB), sx, sy)
            dist = ((qx - px)**2 + (qy - py)**2) ** 0.5
            draw_obj_distance_line(qx, qy, px, py, PDF["septic"], f"Septic {dist:.1f} ft")

        # Shed <-> House
        if getattr(layout, "house", None) and layout.house.x is not None:
            hL, hT, hR, hB = rect_ft(layout.house, yard_height_ft)
            ax, ay, bx, by = nearest_rect_rect_ft((sL, sT, sR, sB), (hL, hT, hR, hB))
            dist = ((ax - bx)**2 + (ay - by)**2) ** 0.5
            draw_obj_distance_line(ax, ay, bx, by, PDF["house"], f"House {dist:.1f} ft")
    


    # ==== Distance label helpers (NEAREST boundary edges) ====
    # Arrowhead helper
    def draw_arrowhead(x, y, dx, dy, size=6):
        """
        Draw a small V-shaped arrowhead at (x,y) pointing along vector (dx,dy).
        """
        length = (dx * dx + dy * dy) ** 0.5 or 1.0
        ux, uy = dx / length, dy / length
        # perpendicular
        px, py = -uy, ux
        # two small lines to form a V
        c.line(x, y, x - ux * size + px * (size * 0.6), y - uy * size + py * (size * 0.6))
        c.line(x, y, x - ux * size - px * (size * 0.6), y - uy * size - py * (size * 0.6))

    def draw_dim_line(x1, y1, x2, y2, label, outside_offset=12, label_offset=2):
        """
        Draws a dimension line with arrowheads from (x1,y1) to (x2,y2), places `label`
        near the center. If line is horizontal, it nudges the line outward by outside_offset
        perpendicular to the line (same for vertical).
        """
        if abs(y1 - y2) < 1e-6:
            # Horizontal line – offset outward vertically
            y1o = y1 - outside_offset
            y2o = y2 - outside_offset
            c.setStrokeColor(colors.darkgray)
            c.line(x1, y1o, x2, y2o)
            # Arrowheads
            draw_arrowhead(x1, y1o, x2 - x1, 0)
            draw_arrowhead(x2, y2o, x1 - x2, 0)
            # Label
            cx = (x1 + x2) / 2
            c.setFillColor(colors.black)
            c.setFont("Helvetica", 8)
            c.drawCentredString(cx, y1o - label_offset, label)
        elif abs(x1 - x2) < 1e-6:
            # Vertical line – offset outward horizontally
            x1o = x1 - outside_offset
            x2o = x2 - outside_offset
            c.setStrokeColor(colors.darkgray)
            c.line(x1o, y1, x2o, y2)
            # Arrowheads
            draw_arrowhead(x1o, y1, 0, y2 - y1)
            draw_arrowhead(x2o, y2, 0, y1 - y2)
            # Label (rotated)
            cy = (y1 + y2) / 2
            c.saveState()
            c.translate(x1o - label_offset, cy)
            c.rotate(90)
            c.setFillColor(colors.black)
            c.setFont("Helvetica", 8)
            c.drawCentredString(0, 0, label)
            c.restoreState()
        else:
            # Diagonal (shouldn't occur in our use) – just draw straight
            c.setStrokeColor(colors.darkgray)
            c.line(x1, y1, x2, y2)

    # Compute nearest-edge distances for a rectangle-shaped object
    def rect_nearest_distances_ft(obj):
        # Horizontal distances
        left_ft  = obj.x
        right_ft = yard_width_ft - (obj.x + obj.width)
        # Vertical distances: obj.y is distance from FRONT (bottom)
        front_ft = obj.y
        back_ft  = yard_height_ft - (obj.y + obj.height)
        return left_ft, right_ft, back_ft, front_ft

    # Draw measurement lines for a rectangular object to the nearest yard edges
    def draw_rect_measurements(obj, side_labels_prefix=""):
        # Must have full rectangle data
        if (not obj or any(getattr(obj, k, None) is None for k in ("x","y","width","height"))):
            return
        # Distances in feet (nearest edges)
        left_ft, right_ft, back_ft, front_ft = rect_nearest_distances_ft(obj)

        # Yard edges in page coords
        yard_left_x   = layout_origin_x
        yard_right_x  = layout_origin_x + yard_width_ft * scale
        yard_top_y    = ft_to_pt_y(0)                 #  true top edge of yard
        yard_bottom_y = ft_to_pt_y(yard_height_ft)    #  true bottom edge of yard

        # Object edges in page coords
        obj_left_x   = ft_to_pt_x(obj.x)
        obj_right_x  = ft_to_pt_x(obj.x + obj.width)
        obj_top_y    = ft_to_pt_y(yard_height_ft - (obj.y + obj.height))
        obj_bottom_y = ft_to_pt_y(yard_height_ft - obj.y)

        # Horizontal dimension lines (Left & Right)
        # Left: yard_left -> obj_left
        draw_dim_line(yard_left_x, obj_top_y, obj_left_x, obj_top_y,
                      f"{side_labels_prefix}Left {left_ft:.1f} ft", outside_offset=8, label_offset=2)
        # Right: obj_right -> yard_right
        draw_dim_line(obj_right_x, obj_top_y, yard_right_x, obj_top_y,
                      f"{side_labels_prefix}Right {right_ft:.1f} ft", outside_offset=8, label_offset=2)

        # Vertical dimension lines (Back/top & Front/bottom)
        # Back (top): yard_top -> obj_top
        draw_dim_line(obj_left_x, yard_top_y, obj_left_x, obj_top_y,
                      f"{side_labels_prefix}Back {back_ft:.1f} ft", outside_offset=8, label_offset=2)
        # Front (bottom): obj_bottom -> yard_bottom
        draw_dim_line(obj_left_x, obj_bottom_y, obj_left_x, yard_bottom_y,
                      f"{side_labels_prefix}Front {front_ft:.1f} ft", outside_offset=8, label_offset=2)

        return left_ft, right_ft, back_ft, front_ft

    # Draw and capture shed distances for legend text
    shed_left_ft = shed_right_ft = shed_back_ft = shed_front_ft = None
    if getattr(layout, "shed", None):
        dists = draw_rect_measurements(layout.shed)
        if dists:
            shed_left_ft, shed_right_ft, shed_back_ft, shed_front_ft = dists

    # ==== Legend (two columns) ====
    legend_x = margin
    legend_y = margin + 10

    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica", 9)
    c.drawString(legend_x, legend_y + 28, "Legend:")
    c.drawString(legend_x, legend_y + 14, "Blue = House")
    c.drawString(legend_x, legend_y, "Green = Well")

    col2_x = legend_x + 150
    c.drawString(col2_x, legend_y + 14, "Brown = Shed")
    c.drawString(col2_x, legend_y, "Red = Septic")

    # Shed distances summary (if available)
    if shed_left_ft is not None:
        col3_x = legend_x + 300
        c.setFont("Helvetica", 9)
        c.drawString(col3_x, legend_y + 28, "Shed distances (nearest edges):")
        c.drawString(col3_x, legend_y + 14, f"Left:  {shed_left_ft:.1f} ft")
        c.drawString(col3_x, legend_y,      f"Right: {shed_right_ft:.1f} ft")
        c.drawString(col3_x + 150, legend_y + 14, f"Back:  {shed_back_ft:.1f} ft")
        c.drawString(col3_x + 150, legend_y,      f"Front: {shed_front_ft:.1f} ft")

    # Optional axis labels for orientation (kept commented)
    """
    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(colors.red)
    # Top (Front)
    top_center_x = layout_origin_x + (yard_width_ft * scale) / 2
    c.drawCentredString(top_center_x, layout_origin_y - 12, "Top (Back)")
    # Bottom (Front)
    bottom_center_x = layout_origin_x + (yard_width_ft * scale) / 2
    c.drawCentredString(bottom_center_x, layout_origin_y + yard_height_ft * scale + 14, "Bottom (Front)")
    # Left
    left_center_y = layout_origin_y + (yard_height_ft * scale) / 2
    c.saveState()
    c.translate(layout_origin_x - 16, left_center_y)
    c.rotate(90)
    c.drawCentredString(0, 0, "Left")
    c.restoreState()
    # Right
    right_center_y = layout_origin_y + (yard_height_ft * scale) / 2
    c.saveState()
    c.translate(layout_origin_x + yard_width_ft * scale + 16, right_center_y)
    c.rotate(270)
    c.drawCentredString(0, 0, "Right")
    c.restoreState()
    """

    c.showPage()
    c.save()
    print(f"PDF exported to {os.path.abspath(filename)}")

