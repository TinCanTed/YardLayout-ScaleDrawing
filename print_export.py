from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
import os

PRINT_DIR = os.path.expanduser("~/gui_scale_drawing/print")
os.makedirs(PRINT_DIR, exist_ok=True)

def export_to_pdf(layout, filename, show_distance_guides: bool = True):
    page_width, page_height = landscape(letter)  # 11 x 8.5 inches landscape
    margin = 0.5 * inch
    legend_height = 60  # space reserved at the bottom for the legend
    yard_width_ft = layout.front  # Left + Right boundary
    yard_height_ft = layout.left  # Front + Back boundary

    # Adjust scale to fit within page dimensions (minus margins and legend space)
    scale_x = (page_width - 2 * margin) / yard_width_ft
    scale_y = (page_height - 2 * margin - legend_height) / yard_height_ft
    scale = min(scale_x, scale_y)

    # helpers: feet -> points (X is simple; Y is top-origin to match Tk canvas)
    def ft_to_pt_x(x_ft: float) -> float:
        return margin + x_ft * scale

    def ft_to_pt_y(y_ft: float) -> float:
        # origin at top: y=0 is top/front; y increases downward
        return page_height - margin - y_ft * scale

    # origin (top-left of the yard rectangle)
    layout_origin_x = ft_to_pt_x(0)
    layout_origin_y = ft_to_pt_y(yard_height_ft)

    c = canvas.Canvas(filename, pagesize=(page_width, page_height))
    c.setLineWidth(0.5)

    # Property boundary box
    c.rect(layout_origin_x, layout_origin_y, yard_width_ft * scale, yard_height_ft * scale)

    # Gridlines
    def draw_pdf_grid():
        spacing_ft = 10
        # verticals
        for ft in range(0, int(yard_width_ft) + 1, spacing_ft):
            x = ft_to_pt_x(ft)
            c.setStrokeColor(colors.lightgrey)
            top = ft_to_pt_y(0)               # top of yard
            bottom = ft_to_pt_y(yard_height_ft)  # bottom of yard
            c.line(x, top, x, bottom)
            c.setFillColor(colors.black)
            c.setFont("Helvetica", 6)
            label_y = ft_to_pt_y(0) + 5
            c.drawCentredString(x, label_y, str(ft))
        # horizontals
        for ft in range(0, int(yard_height_ft) + 1, spacing_ft):
            y = ft_to_pt_y(ft)
            c.setStrokeColor(colors.lightgrey)
            c.line(margin, y, margin + yard_width_ft * scale, y)
            c.setFillColor(colors.black)
            c.setFont("Helvetica", 6)
            c.drawRightString(margin - 4, y - 3, str(ft))

    draw_pdf_grid()

    # Draw layout objects
    def draw_rect(obj, color):
        if obj is None or obj.x is None or obj.y is None:
            return
        x = ft_to_pt_x(obj.x)
        y = ft_to_pt_y(layout.left - obj.y - obj.height)
        w = obj.width * scale
        h = obj.height * scale
        c.setFillColor(color)
        c.rect(x, y, w, -h, fill=1)  # draw upward instead of downward
        c.setFillColorRGB(1, 1, 1)
        c.setFont("Helvetica-Bold", 8)
        c.drawCentredString(x + w / 2, y - h / 2, obj.name or "")

    def draw_point(obj, color):
        if obj is None or obj.x is None or obj.y is None:
            return
        x = ft_to_pt_x(obj.x)
        y = ft_to_pt_y(layout.left - obj.y)
        r = 5
        c.setFillColor(color)
        c.circle(x, y, r, fill=1)
        c.setFillColorRGB(0, 0, 0)
        c.drawString(x + 6, y - 4, obj.name or "")

    draw_rect(layout.house, colors.Color(0.2, 0.5, 0.9))     # Blue
    draw_rect(layout.shed, colors.Color(0.5, 0.3, 0.1))      # Brown
    draw_point(layout.well, colors.Color(0, 0.7, 0))         # Green
    draw_point(layout.septic, colors.Color(0.7, 0, 0))       # Red

    # --- Distance guides (optional) ---
    if show_distance_guides and layout.shed and layout.shed.x is not None and layout.shed.y is not None:
        # property bounds in points
        prop_left   = layout_origin_x
        prop_top    = layout_origin_y
        prop_right  = layout_origin_x + yard_width_ft * scale
        prop_bottom = ft_to_pt_y(0)  # equal to layout_origin_y + yard_height_ft * scale

        # shed bounds in points
        sx1 = ft_to_pt_x(layout.shed.x)
        sy1 = ft_to_pt_y(layout.left - layout.shed.y - layout.shed.height)
        sx2 = sx1 + layout.shed.width * scale
        sy2 = sy1 - layout.shed.height * scale
        scx = (sx1 + sx2) / 2.0
        scy = (sy1 + sy2) / 2.0

        # distances (points)
        d_left_pt  = max(0.0, sx1 - prop_left)
        d_right_pt = max(0.0, prop_right - sx2)
        d_front_pt = max(0.0, sy1 - prop_top)      # front = top edge
        d_back_pt  = max(0.0, prop_bottom - sy2)   # back  = bottom edge

        def pt_to_ft(pts: float) -> float:
            return pts / scale  # scale is points-per-foot

        # style
        c.setDash(4, 3)
        c.setLineWidth(0.7)
        c.setStrokeGray(0.7)
        c.setFillGray(0.4)
        c.setFont("Helvetica", 8)

        # left guide
        c.line(prop_left, scy, sx1, scy)
        if d_left_pt > 0:
            c.drawString((prop_left + sx1) / 2 - 10, scy + 10, f"{pt_to_ft(d_left_pt):.1f} ft")

        # right guide
        c.line(sx2, scy, prop_right, scy)
        if d_right_pt > 0:
            c.drawString((sx2 + prop_right) / 2 - 10, scy + 10, f"{pt_to_ft(d_right_pt):.1f} ft")

        # front (top) guide
        c.line(scx, prop_top, scx, sy1)
        if d_front_pt > 0:
            c.drawString(scx + 8, (prop_top + sy1) / 2, f"{pt_to_ft(d_front_pt):.1f} ft")

        # back (bottom) guide
        c.line(scx, sy2, scx, prop_bottom)
        if d_back_pt > 0:
            c.drawString(scx + 8, (sy2 + prop_bottom) / 2, f"{pt_to_ft(d_back_pt):.1f} ft")

        c.setDash()  # reset

    # Legend
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

    c.showPage()
    c.save()
    print(f"PDF exported to {os.path.abspath(filename)}")

