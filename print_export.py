from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
import os

PRINT_DIR = os.path.expanduser("~/gui_scale_drawing/print")
os.makedirs(PRINT_DIR, exist_ok=True)


def export_to_pdf(layout, filename):
    page_width, page_height = landscape(letter)  # 11 x 8.5 inches landscape
    margin = 0.5 * inch
    legend_height = 60  # space reserved at the bottom for the legend
    yard_width_ft = layout.front  # Left + Right boundary
    yard_height_ft = layout.left  # Front + Back boundary

    # Adjust scale to fit within page dimensions (minus margins and legend space)
    scale_x = (page_width - 2 * margin) / yard_width_ft
    scale_y = (page_height - 2 * margin - legend_height) / yard_height_ft
    scale = min(scale_x, scale_y)

    def ft_to_pt_x(x):
        return margin + x * scale
    layout_origin_x = margin

    def ft_to_pt_y(y):
        #return margin + legend_height + y * scale # origin at bottom
        return page_height - margin - y * scale # origin at top
    layout_origin_y = ft_to_pt_y(yard_height_ft)
    # Coordinates flipped to match LayoutCanvas (origin top-left).
    # layout_origin_x/y marks upper-left of the layout area.

    c = canvas.Canvas(filename, pagesize=(page_width, page_height))
    c.setLineWidth(0.5)

    # Draw boundary box
    #c.rect(margin, margin + legend_height, yard_width_ft * scale, yard_height_ft * scale)
    c.rect(layout_origin_x, layout_origin_y, yard_width_ft * scale, yard_height_ft * scale)

    # Gridlines
    def draw_pdf_grid():
        spacing_ft = 10
        for ft in range(0, int(yard_width_ft) + 1, spacing_ft):
            x = ft_to_pt_x(ft)
            c.setStrokeColor(colors.lightgrey)
            #c.line(x, margin + legend_height, x, margin + legend_height + yard_height_ft * scale)
            top = ft_to_pt_y(0)  # top of yard
            bottom = ft_to_pt_y(yard_height_ft)  # bottom of yard
            c.line(x, top, x, bottom)

            c.setFillColor(colors.black)
            c.setFont("Helvetica", 6)
            #c.drawCentredString(x, margin + legend_height + yard_height_ft * scale + 2, str(ft))
            label_y = ft_to_pt_y(0) + 5  # 5 points above the layout's top edge
            c.drawCentredString(x, label_y, str(ft))

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
        x = ft_to_pt_x(obj.x)
        y = ft_to_pt_y(layout.left - obj.y - obj.height) 
        w = obj.width * scale
        h = obj.height * scale
        c.setFillColor(color)
        c.rect(x, y, w, -h, fill=1)  # draw upward instead of downward
        c.setFillColorRGB(1, 1, 1)
        c.setFont("Helvetica-Bold", 8)
        c.drawCentredString(x + w / 2, y - h / 2, obj.name)

    def draw_point(obj, color):
        if obj is None or obj.x is None or obj.y is None:
            return  #Skip drawing if coordinates are missing

        x = ft_to_pt_x(obj.x)
        y = ft_to_pt_y(layout.left - obj.y)
        r = 5
        c.setFillColor(color)
        c.circle(x, y, r, fill=1)
        c.setFillColorRGB(0, 0, 0)
        c.drawString(x + 6, y - 4, obj.name)

    draw_rect(layout.house, colors.Color(0.2, 0.5, 0.9))     # Blue
    draw_rect(layout.shed, colors.Color(0.5, 0.3, 0.1))      # Brown
    draw_point(layout.well, colors.Color(0, 0.7, 0))         # Green
    draw_point(layout.septic, colors.Color(0.7, 0, 0))       # Red

    # Draw legend at the bottom with two-column layout
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

    # TEMPORARY AXIS LABELS FOR ORIENTATION (MATCH LayoutCanvas), Remove --> """ before and after """ to use labels.
    
    """
    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(colors.red)

    # Top (Front)
    top_center_x = layout_origin_x + (yard_width_ft * scale) / 2
    c.drawCentredString(top_center_x, layout_origin_y - 12, "Top (Front)")

    # Bottom (Back)
    bottom_center_x = layout_origin_x + (yard_width_ft * scale) / 2
    c.drawCentredString(bottom_center_x, layout_origin_y + yard_height_ft * scale + 14, "Bottom (Back)")

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
    

