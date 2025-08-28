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

        # === Distance guides state ===
        self.show_distance_guides = getattr(self, "show_distance_guides", False)
        self.px_per_ft = self.feet_to_pixel_ratio      # reuse your existing scale
        self.live_guide_updates = False                # OFF by default
        self._guide_redraw_job = None                  # throttle handle




        self.draw_grid()
        self.draw_objects()
        self.draw_legend()
        # draw distance guides
        self.after(0, lambda: self.set_show_distance_guides(True))


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


        # Draw a visible boundary rectangle for the property
        prop_left_px   = MARGIN_PX
        prop_top_px    = MARGIN_PX
        prop_right_px  = MARGIN_PX + self.feet_to_pixels(self.layout.front)  # X spans "front" feet
        prop_bottom_px = MARGIN_PX + self.feet_to_pixels(self.layout.left)   # Y spans "left" feet (your height)

        prop_rect_id = self.canvas.create_rectangle(
            prop_left_px, prop_top_px, prop_right_px, prop_bottom_px,
            outline="black", width=2, fill="",
            tags=("property", "boundary")
        )
        self.canvas.tag_lower(prop_rect_id)  # keep it behind objects
    

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
            # NEW: role tag (for guides/rules). Extend as you add more object types.
            role = None
            name_l = obj.name.lower()
            if name_l == "shed":
                role = "shed"
            elif name_l == "house":
                role = "house"
            elif name_l == "septic":
                role = "septic"
            elif name_l == "well":
                role = "well"

            role_tags = (role,) if role else tuple()

            # Include the role tag on ALL shed items so bbox("shed") works
            self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, tags=("draggable", tag) + role_tags)
            self.canvas.create_text((x1+x2)/2, (y1+y2)/2, text=obj.name, fill="white", tags=("draggable", tag) + role_tags)

            if name_l == "shed":
                cx = (x1 + x2) / 2
                cy = y1 - 15
                self.canvas.create_text(
                    cx, cy,
                    text="↻",
                    fill="blue",
                    font=("Arial", 14, "bold"),
                    tags=("draggable", tag, "rotate_shed") + role_tags
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
        # Refresh guides after everything is drawn
        self.redraw_distance_guides()

    def set_live_guide_updates(self, on: bool) -> None:
        """Toggle live redraw of distance guides during drag."""
        self.live_guide_updates = bool(on)
        if self.live_guide_updates and self.show_distance_guides:
            if self._guide_redraw_job:
                self.after_cancel(self._guide_redraw_job)
                self._guide_redraw_job = None
            self._guide_redraw_job = self.after(0, self.redraw_distance_guides)   

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

        # Live redraw (throttled) if enabled
        if self.live_guide_updates and self.show_distance_guides:
            if self._guide_redraw_job:
                self.after_cancel(self._guide_redraw_job)
        # ~30 fps (33ms). Adjust if needed.
        self._guide_redraw_job = self.after(33, self.redraw_distance_guides)

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
            # NEW: finalize guides even if nothing moved (optional)
            if self._guide_redraw_job:
                self.after_cancel(self._guide_redraw_job)
                self._guide_redraw_job = None
            self.redraw_distance_guides()
            self.drag_data["tag"] = None
            return

        self.layout.update_object_position(name, new_x, new_y)
        print(f"[DEBUG] Updated {tag} to unflipped x={new_x}, y={new_y}")
        save_layout_to_file(self.layout, self.filename)
        
        if hasattr(self, "_guide_redraw_job") and self._guide_redraw_job:
            self.after_cancel(self._guide_redraw_job)
            self._guide_redraw_job = None
        self.redraw_distance_guides()

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

     # ===== Distance Guides: helpers and API =====

    def _feet(self, px: float) -> float:
        # Convert pixels to feet using your active scale
        return px / float(self.px_per_ft)

    def _find_bbox_px(self, tag_candidates):
        """
        Return (x1, y1, x2, y2) for the first tag that exists, else None.
        tag_candidates can be a string or list/tuple of strings.
        """
        if isinstance(tag_candidates, (list, tuple)):
            for t in tag_candidates:
                bb = self.canvas.bbox(t)
                if bb:
                    return bb
            return None
        return self.canvas.bbox(tag_candidates)

    def _property_bbox_from_layout(self):
        """Compute property bbox (px) from layout.front (width) and layout.left (height)."""
        x1 = MARGIN_PX
        y1 = MARGIN_PX
        x2 = MARGIN_PX + self.feet_to_pixels(self.layout.front)
        y2 = MARGIN_PX + self.feet_to_pixels(self.layout.left)
        return (x1, y1, x2, y2)

    def set_show_distance_guides(self, on: bool) -> None:
        """Toggle showing shed→property distance guides."""
        self.show_distance_guides = bool(on)
        self.redraw_distance_guides()

    def redraw_distance_guides(self) -> None:
        """Draw light dashed lines + ft labels from shed to property edges."""
        # Clear previous guides
        self.canvas.delete("distance_guide")

        if not self.show_distance_guides:
            return

        # Shed bbox — requires shed items carry the "shed" tag
        shed_bb = self._find_bbox_px("shed")
        if not shed_bb:
            return
        sx1, sy1, sx2, sy2 = shed_bb
        shed_cx = (sx1 + sx2) / 2
        shed_cy = (sy1 + sy2) / 2

        # Property bbox: prefer tagged rect, else compute from layout
        prop_bb = self._find_bbox_px(["property", "boundary"])
        if not prop_bb:
            prop_bb = self._property_bbox_from_layout()
        px1, py1, px2, py2 = prop_bb

        # Edge-to-edge distances (px; clamp ≥ 0)
        d_left_px  = max(0, sx1 - px1)
        d_right_px = max(0, px2 - sx2)
        d_front_px = max(0, sy1 - py1)  # "front" = top edge
        d_back_px  = max(0, py2 - sy2)  # "back"  = bottom edge

        # Draw helpers
        def draw_h_guide(x_start, x_end, y, dist_px):
            line_id = self.canvas.create_line(
                x_start, y, x_end, y,
                dash=(4, 3), width=1, fill="#BFBFBF",
                tags=("distance_guide",)
            )
            self.canvas.tag_lower(line_id)
            if dist_px > 0:
                midx = (x_start + x_end) / 2
                self.canvas.create_text(
                    midx, y - 8,
                    text=f"{self._feet(dist_px):.1f} ft",
                    font=("TkDefaultFont", 8),
                    fill="#666666",
                    anchor="s",
                    tags=("distance_guide",)
                )

        def draw_v_guide(x, y_start, y_end, dist_px):
            line_id = self.canvas.create_line(
                x, y_start, x, y_end,
                dash=(4, 3), width=1, fill="#BFBFBF",
                tags=("distance_guide",)
            )
            self.canvas.tag_lower(line_id)
            if dist_px > 0:
                midy = (y_start + y_end) / 2
                self.canvas.create_text(
                    x + 8, midy,
                    text=f"{self._feet(dist_px):.1f} ft",
                    font=("TkDefaultFont", 8),
                    fill="#666666",
                    anchor="w",
                    tags=("distance_guide",)
                )

        # Left / Right / Front / Back guides
        draw_h_guide(px1, sx1, shed_cy, d_left_px)
        draw_h_guide(sx2, px2, shed_cy, d_right_px)
        draw_v_guide(shed_cx, py1, sy1, d_front_px)
        draw_v_guide(shed_cx, sy2, py2, d_back_px)   

    def rotate_shed_by_click(self, _event):
        self.rotate_shed(_event)

