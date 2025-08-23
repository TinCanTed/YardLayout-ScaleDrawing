"""
layout_canvas.py

Defines the LayoutCanvas class, a Tkinter-based canvas for visualizing and editing
a scale yard layout. Supports rendering of boundaries and objects with drag-and-drop
and object rotation features.
"""

import tkinter as tk
from layout_data import LayoutData, RectangleObject, PointObject
from file_handler import save_layout_to_file
from typing import cast, Union
from typing import Optional

# Grid and zoom configuration
GRID_SPACING_FT = 10
ZOOM = 1.2  # Zoom factor for scaling the layout to fit
MARGIN_PX = 20  # Padding space on top and left for axis labels

class LayoutCanvas(tk.Frame):
    def __init__(self, master, layout: LayoutData, filename: str):
        super().__init__(master)
        self.filename = filename
        canvas_display_width = 850
        canvas_display_height = 650

        total_width_ft = layout.front
        total_height_ft = layout.left

        scale_x = canvas_display_width / total_width_ft
        scale_y = canvas_display_height / total_height_ft
        self.feet_to_pixel_ratio = min(scale_x, scale_y) * ZOOM

        self.canvas_width = int(total_width_ft * self.feet_to_pixel_ratio)
        self.canvas_height = int(total_height_ft * self.feet_to_pixel_ratio)

        self.layout = layout
        self.drag_data = {"tag": None, "offset_x": 0, "offset_y": 0, "start_x": 0, "start_y": 0}

        self.canvas = tk.Canvas(
            self,
            width=self.canvas_width + MARGIN_PX,
            height=self.canvas_height + MARGIN_PX,
            bg="white"
        )
        self.canvas.pack(side="left", fill="both", expand=True)

        self.legend = tk.Canvas(self, width=150, height=self.canvas_height, bg="#f0f0f0")
        self.legend.pack(side="right", fill="y")

        self.draw_grid()
        self.draw_objects()
        self.draw_legend()

        self.canvas.tag_bind("draggable", "<ButtonPress-1>", self.on_drag_start)
        self.canvas.tag_bind("draggable", "<B1-Motion>", self.on_drag_move)
        self.canvas.tag_bind("draggable", "<ButtonRelease-1>", self.on_drag_release)
        master.bind("r", self.rotate_shed)
        master.bind("+", self.zoom_in)
        master.bind("-", self.zoom_out)
        master.bind("=", self.zoom_in)

    def feet_to_pixels(self, feet):
        return feet * self.feet_to_pixel_ratio

    def draw_grid(self):
        spacing_ft = GRID_SPACING_FT
        total_width_ft = self.layout.front
        total_height_ft = self.layout.left

        for ft in range(0, int(total_width_ft) + 1, spacing_ft):
            x = self.feet_to_pixels(ft) + MARGIN_PX
            self.canvas.create_line(x, MARGIN_PX, x, self.canvas_height + MARGIN_PX, fill="#eee")
            self.canvas.create_text(x, MARGIN_PX - 14, text=str(ft), anchor="n", fill="#444", font=("Arial", 8))

        for ft in range(0, int(total_height_ft) + 1, spacing_ft):
            y = self.feet_to_pixels(ft) + MARGIN_PX
            self.canvas.create_line(MARGIN_PX, y, self.canvas_width + MARGIN_PX, y, fill="#eee")
            self.canvas.create_text(MARGIN_PX - 14, y, text=str(ft), anchor="w", fill="#444", font=("Arial", 8))


        # Uncomment the following code to display "Left" "Right" "Front" "Back" labels on the LayoutCanvas for debugging
        #self.canvas.create_text(self.canvas_width / 2, MARGIN_PX / 2, text="Top (Back?)", fill="red", font=("Arial", 10, "bold"))
        #self.canvas.create_text(self.canvas_width / 2, self.canvas_height + MARGIN_PX - 4, text="Bottom (Front?)", fill="red", font=("Arial", 10, "bold"))
        #self.canvas.create_text(MARGIN_PX / 2, self.canvas_height / 2, text="Left", fill="red", font=("Arial", 10, "bold"), angle=90)
        #self.canvas.create_text(self.canvas_width + MARGIN_PX - 4, self.canvas_height / 2, text="Right", fill="red", font=("Arial", 10, "bold"), angle=270)

    def draw_objects(self):
        self.canvas.delete("all")
        self.draw_grid()
        self.draw_legend()

        def draw_rect(obj: Optional[RectangleObject], color):
            if obj is None or obj.x is None or obj.y is None:
                return
            # draw the rectangle
            width = obj.width
            height = obj.height
            x1 = self.feet_to_pixels(obj.x) + MARGIN_PX
            y1 = self.feet_to_pixels(self.layout.left - obj.y - obj.height) + MARGIN_PX
            x2 = x1 + self.feet_to_pixels(width)
            y2 = y1 + self.feet_to_pixels(height)
            tag = obj.name.lower().replace(" ", "_")
            self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, tags=("draggable", tag))
            self.canvas.create_text((x1+x2)/2, (y1+y2)/2, text=obj.name, fill="white", tags=("draggable", tag))

            if obj.name.lower() == "shed":
                cx = (x1 + x2) / 2
                cy = y1 - 15
                self.canvas.create_text(
                    cx, cy,
                    text="↻",
                    fill="blue",
                    font=("Arial", 14, "bold"),
                    tags=("draggable", tag, "rotate_shed")
                )
                self.canvas.tag_bind("rotate_shed", "<Button-1>", self.rotate_shed_by_click)

        def draw_point(obj: Optional[PointObject], color):
            if obj is None or obj.x is None or obj.y is None:
                return
            # draw the point

            x = self.feet_to_pixels(obj.x) + MARGIN_PX
            y = self.feet_to_pixels(self.layout.left - obj.y) + MARGIN_PX
            r = 6
            tag = obj.name.lower().replace(" ", "_")
            self.canvas.create_oval(x - r, y - r, x + r, y + r, fill=color, tags=("draggable", tag))
            self.canvas.create_text(x, y - 10, text=obj.name, fill="black", tags=("draggable", tag))

        draw_rect(self.layout.house, "blue")
        draw_rect(self.layout.shed, "saddlebrown")
        draw_point(self.layout.well, "darkgreen")
        draw_point(self.layout.septic, "gray")

    def draw_legend(self):
        self.legend.delete("all")
        items = [
            ("House", "blue"),
            ("Shed", "saddlebrown"),
            ("Well", "darkgreen"),
            ("Septic Tank", "gray")
        ]
        y = 20
        for name, color in items:
            self.legend.create_rectangle(10, y, 30, y + 20, fill=color)
            self.legend.create_text(35, y + 10, anchor="w", text=name)
            y += 30

    def on_drag_start(self, event):
        closest = self.canvas.find_closest(event.x, event.y)
        if closest:
            tags = self.canvas.gettags(closest[0])
            for tag in tags:
                if tag != "draggable":
                    self.drag_data["tag"] = tag
                    bbox = self.canvas.bbox(closest[0])
                    self.drag_data["offset_x"] = event.x - bbox[0]
                    self.drag_data["offset_y"] = event.y - bbox[1]
                    break

    def on_drag_move(self, event):
        tag = self.drag_data["tag"]
        if tag:
            items = self.canvas.find_withtag(tag)
            if not items:
                return
            bbox = self.canvas.bbox(items[0])
            dx = event.x - self.drag_data["offset_x"] - bbox[0]
            dy = event.y - self.drag_data["offset_y"] - bbox[1]
            for item in items:
                self.canvas.move(item, dx, dy)

    def on_drag_release(self, event):
        tag = self.drag_data["tag"]
        if not tag:
            return

        items = self.canvas.find_withtag(tag)
        if not items:
            return

        bbox = self.canvas.bbox(items[0])
        new_center_x = ((bbox[0] + bbox[2]) / 2 - MARGIN_PX) / self.feet_to_pixel_ratio
        new_center_y = ((bbox[1] + bbox[3]) / 2 - MARGIN_PX) / self.feet_to_pixel_ratio

        name = tag.replace("_", " ").title()
        #obj = getattr(self.layout, tag, None)
        attr_map = {
            "house": "house",
            "shed": "shed",
            "well": "well",
            "septic_tank": "septic"
        }
        attr_name = attr_map.get(tag, tag)
        if attr_name is None:
            return

        obj = cast(Union[RectangleObject, PointObject], getattr(self.layout, attr_name))

        if obj.x is None or obj.y is None:
            return

        if isinstance(obj, PointObject):
            new_x = round(new_center_x, 2)
            new_y = round(self.layout.left - new_center_y, 2)
        elif isinstance(obj, RectangleObject):
            new_x = round(new_center_x - obj.width / 2, 2)
            new_y = round(self.layout.left - new_center_y - obj.height / 2, 2)
        else:
            return

        old_x = round(obj.x, 2) if obj.x is not None else None
        old_y = round(obj.y, 2) if obj.y is not None else None

        if (old_x, old_y) == (new_x, new_y):
            self.drag_data["tag"] = None
            return

        self.layout.update_object_position(name, new_x, new_y)
        print(f"[DEBUG] Updated {tag} to unflipped x={new_x}, y={new_y}")
        save_layout_to_file(self.layout, self.filename)

        self.drag_data["tag"] = None

    def rotate_shed(self, _event):
        shed = self.layout.shed
        if shed.x is None or shed.y is None:
            return

        # Flip Y back to unflipped so rotation math works on real coordinates
        real_y = self.layout.left - shed.y - shed.height

        # Compute center based on unflipped coordinates
        center_x = shed.x + shed.width / 2
        center_y = real_y + shed.height / 2

        # Rotate (swap width and height)
        shed.width, shed.height = shed.height, shed.width

        # Compute new top-left corner based on center
        shed.x = center_x - shed.width / 2
        real_y = center_y - shed.height / 2

        # Flip Y back for canvas display
        shed.y = self.layout.left - real_y - shed.height

        self.draw_objects()

    def update_canvas_dimensions(self):
        total_width_ft = self.layout.front
        total_height_ft = self.layout.left
        self.canvas_width = int(total_width_ft * self.feet_to_pixel_ratio)
        self.canvas_height = int(total_height_ft * self.feet_to_pixel_ratio)
        self.canvas.config(
            width=self.canvas_width + MARGIN_PX,
            height=self.canvas_height + MARGIN_PX
        )

    def zoom_in(self, _event=None):
        self.feet_to_pixel_ratio *= 1.1
        self.update_canvas_dimensions()
        self.draw_objects()

    def zoom_out(self, _event=None):
        self.feet_to_pixel_ratio /= 1.1
        self.update_canvas_dimensions()
        self.draw_objects()

    def rotate_shed_by_click(self, _event):
        self.rotate_shed(_event)

