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
from ui_palette import HEX, role_for
COLOR_DEBUG = True  # turn to false when done testing
if COLOR_DEBUG:
    print(f"[COLOR DEBUG] HEX keys = {list(HEX.keys())}")

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
        self.on_layout_changed = None  # callback hook set by the window

        self.canvas.tag_bind("draggable", "<ButtonPress-1>", self.on_drag_start)
        self.canvas.tag_bind("draggable", "<B1-Motion>", self.on_drag_move)
        self.canvas.tag_bind("draggable", "<ButtonRelease-1>", self.on_drag_release)
        master.bind("r", self.rotate_shed)
        master.bind("+", self.zoom_in)
        master.bind("-", self.zoom_out)
        master.bind("=", self.zoom_in)

    def feet_to_pixels(self, feet):
        return feet * self.feet_to_pixel_ratio

    def pixels_to_feet(self, px: float) -> float:
        """Inverse of feet_to_pixels for deltas (no margin involved)."""
        # How many pixels is 1 foot?
        px_per_ft = float(self.feet_to_pixels(1.0))
        return 0.0 if px_per_ft == 0 else (px / px_per_ft)
    

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

        # Draw all objects using the unified palette
        self._draw_rect(self.layout.house)
        self._draw_rect(self.layout.shed)
        self._draw_point(self.layout.well)
        self._draw_point(self.layout.septic)

        # Refresh guides after everything is drawn
        self.redraw_distance_guides()

        # NEW: object-to-object guides (colored)
        self._draw_shed_object_distances()

    def _draw_rect(self, obj: Optional[RectangleObject]):
        if obj is None or obj.x is None or obj.y is None:
            return

        width = obj.width
        height = obj.height
        x1 = self.feet_to_pixels(obj.x) + MARGIN_PX
        y1 = self.feet_to_pixels(self.layout.left - obj.y - obj.height) + MARGIN_PX
        x2 = x1 + self.feet_to_pixels(width)
        y2 = y1 + self.feet_to_pixels(height)

        name_l = (obj.name or "").lower()
        tag = name_l.replace(" ", "_")

        # role tag for selection/rules
        role = role_for(obj.name)
        role_tags = (role,) if role else tuple()

        fill_color = HEX.get(role or name_l, "gray")
        if COLOR_DEBUG:
            print(f"[COLOR DEBUG] RECT name='{obj.name}' role='{role}' fill={fill_color}")
        # rectangle + label
        self.canvas.create_rectangle(
            x1, y1, x2, y2,
            fill=fill_color,
            tags=("draggable", tag) + role_tags
        )
        self.canvas.create_text(
            (x1 + x2) / 2, (y1 + y2) / 2,
            text=obj.name,
            fill="white",
            tags=("draggable", tag) + role_tags
        )

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

    def _draw_point(self, obj: Optional[PointObject]):
        if obj is None or obj.x is None or obj.y is None:
            return

        x = self.feet_to_pixels(obj.x) + MARGIN_PX
        y = self.feet_to_pixels(self.layout.left - obj.y) + MARGIN_PX
        r = 6

        name_l = (obj.name or "").lower()
        tag = name_l.replace(" ", "_")

        role = role_for(obj.name)
        role_tags = (role,) if role else tuple()

        fill_color = HEX.get(role or name_l, "gray")
        if COLOR_DEBUG:
            print(f"[COLOR DEBUG] POINT name='{obj.name}' role='{role}' fill={fill_color}")

        self.canvas.create_oval(
            x - r, y - r, x + r, y + r,
            fill=fill_color,
            tags=("draggable", tag) + role_tags
        )
        self.canvas.create_text(
            x, y - 10,
            text=obj.name,
            fill="black",
            tags=("draggable", tag) + role_tags
        )
 
        # Refresh guides after everything is drawn
        self.redraw_distance_guides()

    # --- Distance helpers (feet, top-based Y like our canvas drawing) ---

    def _rect_ft(self, obj):
        """Return (L,T,R,B) in feet for a rectangle object using top-based Y."""
        L = obj.x
        R = obj.x + obj.width
        T = self.layout.left - (obj.y + obj.height)
        B = self.layout.left - obj.y
        return L, T, R, B

    def _nearest_rect_point_ft(self, rect, px, py):
        """Nearest points between rect (L,T,R,B) and a point (px,py) in feet."""
        L, T, R, B = rect
        # clamp point to rect
        qx = min(max(px, L), R)
        qy = min(max(py, T), B)
        return (qx, qy, px, py)

    def _nearest_rect_rect_ft(self, A, Bx):
        """Nearest points between rect A (L,T,R,B) and rect B (L,T,R,B)."""
        LA, TA, RA, BA = A
        LB, TB, RB, BB = Bx

        # delta on each axis (if overlap, delta = 0, else separation)
        if RA < LB:
            dx = LB - RA
            ax = RA
            bx = LB
        elif RB < LA:
            dx = LA - RB
            ax = LA
            bx = RB
        else:
            dx = 0
            ax = bx = max(LA, LB) if min(RA, RB) >= max(LA, LB) else (LA + RA) / 2  # any overlap x

        if BA < TB:
            dy = TB - BA
            ay = BA
            by = TB
        elif BB < TA:
            dy = TA - BB
            ay = TA
            by = BB
        else:
            dy = 0
            ay = by = max(TA, TB) if min(BA, BB) >= max(TA, TB) else (TA + BA) / 2  # any overlap y

        # If overlapping both axes, pick a small vertical segment (visual)
        if dx == 0 and dy == 0:
            ay = by = max(TA, TB)  # same y
            ax = (max(LA, LB) + min(RA, RB)) / 2
            bx = ax
        return (ax, ay, bx, by)

    def _ft_to_px(self, x_ft, y_ft):
        """Feet (top-based) -> canvas pixels (origin top-left of yard)."""
        return (
            self.feet_to_pixels(x_ft) + MARGIN_PX,
            self.feet_to_pixels(y_ft) + MARGIN_PX
        )

    def _draw_obj_distance_line(self, x1_ft, y1_ft, x2_ft, y2_ft, color_hex, label):
        """Draw a colored line + label between two ft points (top-based)."""
        x1, y1 = self._ft_to_px(x1_ft, y1_ft)
        x2, y2 = self._ft_to_px(x2_ft, y2_ft)
        # line
        self.canvas.create_line(x1, y1, x2, y2, fill=color_hex, width=2, tags=("guide_objdist",))
        # label at midpoint, slightly offset
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        self.canvas.create_text(mx, my - 10, text=label, fill=color_hex, font=("Arial", 10, "bold"),
                                tags=("guide_objdist",))

    def _draw_shed_object_distances(self):
        """Draw colored distances from Shed to Well, Septic, House."""
        shed = getattr(self.layout, "shed", None)
        if not shed or shed.x is None:
            return

        # Colors
        col_house  = HEX["house"]
        col_well   = HEX["well"]
        col_septic = HEX["septic"]

        # Rect for shed
        sL, sT, sR, sB = self._rect_ft(shed)

        # Shed <-> Well (point)
        well = getattr(self.layout, "well", None)
        if well and well.x is not None:
            wx = well.x
            wy = self.layout.left - well.y  # point Y in top-based feet
            qx, qy, px, py = self._nearest_rect_point_ft((sL, sT, sR, sB), wx, wy)
            dist = ((qx - px) ** 2 + (qy - py) ** 2) ** 0.5
            self._draw_obj_distance_line(qx, qy, px, py, col_well, f"Well {dist:.1f} ft")

        # Shed <-> Septic (point)
        septic = getattr(self.layout, "septic", None)
        if septic and septic.x is not None:
            sx = septic.x
            sy = self.layout.left - septic.y
            qx, qy, px, py = self._nearest_rect_point_ft((sL, sT, sR, sB), sx, sy)
            dist = ((qx - px) ** 2 + (qy - py) ** 2) ** 0.5
            self._draw_obj_distance_line(qx, qy, px, py, col_septic, f"Septic {dist:.1f} ft")

        # Shed <-> House (rect)
        house = getattr(self.layout, "house", None)
        if house and house.x is not None:
            hL, hT, hR, hB = self._rect_ft(house)
            ax, ay, bx, by = self._nearest_rect_rect_ft((sL, sT, sR, sB), (hL, hT, hR, hB))
            dist = ((ax - bx) ** 2 + (ay - by) ** 2) ** 0.5
            self._draw_obj_distance_line(ax, ay, bx, by, col_house, f"House {dist:.1f} ft")

    # schedule a guides redraw on the next Tk tick (coalesces rapid drags)
    def request_guide_redraw(self):
        """Coalesce rapid drags into a single guide redraw on next Tk tick."""
        job = getattr(self, "_guide_redraw_job", None)
        if job:
            self.after_cancel(job)
            self._guide_redraw_job = None
        self._guide_redraw_job = self.after(0, self.redraw_distance_guides)    

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
        # cancel any pending redraw so we reschedule cleanly on move
        if getattr(self, "_guide_redraw_job", None):
            self.after_cancel(self._guide_redraw_job)
            self._guide_redraw_job = None

        closest = self.canvas.find_closest(event.x, event.y)
        if not closest:
            return

        item_id = closest[0]
        tags = self.canvas.gettags(item_id)

        """
        # choose a role tag we care about
        drag_role = None
        for t in tags:
        if t in ("shed", "house", "well", "septic"):
            drag_role = t
            break
        if not drag_role:
            # fall back to any non-generic tag (skip "draggable")
            for t in tags:
                if t != "draggable":
                    drag_role = t
                    break

        if not drag_role:
            return  # nothing draggable we know

        self._drag_role = drag_role
        self._drag_item = item_id

        # remember pointer offset relative to the item's bbox top-left
        bx1, by1, bx2, by2 = self.canvas.bbox(item_id)
        self.drag_data["offset_x"] = event.x - bx1
        self.drag_data["offset_y"] = event.y - by1
        """
        # Prefer known roles
        role_tag = next((t for t in tags if t in ("shed","house","well","septic")), None)
        if role_tag is None or role_tag == "rotate_shed":
            # fall back to any non-generic tag, but skip rotate glyph
            role_tag = next((t for t in tags if t not in ("draggable","rotate_shed")), None)

        if not role_tag:
            return

        self.drag_data["tag"] = role_tag
        bx1, by1, bx2, by2 = self.canvas.bbox(item_id)
        self.drag_data["offset_x"] = event.x - bx1
        self.drag_data["offset_y"] = event.y - by1
        
    def on_drag_move(self, event):
        tag = self.drag_data["tag"]
        if tag:
            items = self.canvas.find_withtag(tag)
            if not items:
                return

            # current bbox BEFORE this move
            bbox = self.canvas.bbox(items[0])
            dx = event.x - self.drag_data["offset_x"] - bbox[0]
            dy = event.y - self.drag_data["offset_y"] - bbox[1]
            # 1) move all canvas items for this tag
            for item in items:
                self.canvas.move(item, dx, dy)

            # 2) update the underlying layout in FEET (so guides recompute correctly)
            if tag in ("shed", "house", "well", "septic"):
                dfx = self.pixels_to_feet(dx)
                dfy = self.pixels_to_feet(dy)

                obj = getattr(self.layout, tag, None)
                if obj is not None and obj.x is not None and obj.y is not None:
                    obj.x += dfx
                    obj.y += dfy
                # NOTE: Your y is bottom-based feet (Front distance). Positive dy (down)
                # increases pixels and correctly increases obj.y, so += dfy is right.

        # 3) Live redraw (throttled) if enabled
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

        if callable(getattr(self, "on_layout_changed", None)):
            try:
                self.on_layout_changed()
            except Exception as e:
                print("[WARN] on_layout_changed callback failed:", e)
        
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
        self.px_per_ft = self.feet_to_pixel_ratio   # keep px/ft in sync
        self.update_canvas_dimensions()
        self.draw_objects()

    def zoom_out(self, _event=None):
        self.feet_to_pixel_ratio /= 1.1
        self.px_per_ft = self.feet_to_pixel_ratio   # keep px/ft in sync
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

    def _bbox_union(self, item_ids):
        """Union bbox for a list of canvas items."""
        boxes = [self.canvas.bbox(i) for i in item_ids if self.canvas.bbox(i)]
        if not boxes:
            return None
        x1 = min(b[0] for b in boxes)
        y1 = min(b[1] for b in boxes)
        x2 = max(b[2] for b in boxes)
        y2 = max(b[3] for b in boxes)
        return (x1, y1, x2, y2)

    def _shed_body_bbox_px(self):
        """BBox of the shed rectangle(s) only (exclude rotate glyph / labels)."""
        items = self.canvas.find_withtag("shed")
        rects = [i for i in items if self.canvas.type(i) == "rectangle"]
        return self._bbox_union(rects)

    def _shed_distances_ft(self):
        """Return exact (left_ft, right_ft, front_ft, back_ft) from the layout model."""
        s = self.layout.shed
        if not s or s.x is None or s.y is None or s.width is None or s.height is None:
            return None
        # Model meaning (based on your form):
        # x = distance from LEFT property line to shed LEFT edge
        # y = distance from FRONT property line (top) to shed FRONT edge
        left_ft  = max(0.0, s.x)
        right_ft = max(0.0, self.layout.front - (s.x + s.width))
        front_ft = max(0.0, s.y)
        back_ft  = max(0.0, self.layout.left - (s.y + s.height))
        return (left_ft, right_ft, front_ft, back_ft)


    def set_show_distance_guides(self, on: bool) -> None:
        """Toggle showing shed→property distance guides."""
        self.show_distance_guides = bool(on)
        self.redraw_distance_guides()

    def redraw_distance_guides(self) -> None:
        """Draw light dashed lines + ft labels from shed to property edges."""
        # Clear previous guides
        self.canvas.delete("distance_guide")
        self.canvas.delete("guide_objdist")

        if not getattr(self, "show_distance_guides", False):
            return

        # Need the shed and the property bounds (in pixels) to place the lines
        # Use shed RECTANGLE bbox only (exclude rotate glyph / labels)
        shed_bb = self._shed_body_bbox_px() or self._find_bbox_px("shed")
        if not shed_bb:
            return
        sx1, sy1, sx2, sy2 = shed_bb
        shed_cx = (sx1 + sx2) / 2
        shed_cy = (sy1 + sy2) / 2

        prop_bb = self._find_bbox_px(["property", "boundary"]) or self._property_bbox_from_layout()
        px1, py1, px2, py2 = prop_bb

        # Exact distances in FEET for labels
        if self.live_guide_updates:
            # derive from current pixel geometry (top=back, bottom=front)
            left_ft  = self._feet(max(0, sx1 - px1))
            right_ft = self._feet(max(0, px2 - sx2))
            back_ft  = self._feet(max(0, sy1 - py1))   # top segment
            front_ft = self._feet(max(0, py2 - sy2))   # bottom segment
        else:
            d = self._shed_distances_ft()
            if not d:
                return
            left_ft, right_ft, front_ft, back_ft = d

        # Helpers: draw lines in px; label with ft
        def draw_h_guide(x_start, x_end, y, dist_ft: float):
            line_id = self.canvas.create_line(
                x_start, y, x_end, y, dash=(4, 3), width=1, fill="#BFBFBF",
                tags=("distance_guide",)
            )
            self.canvas.tag_lower(line_id)
            if dist_ft > 0:
                midx = (x_start + x_end) / 2
                self.canvas.create_text(
                    midx, y - 8, text=f"{dist_ft:.1f} ft",
                    font=("TkDefaultFont", 8), fill="#666666", anchor="s",
                    tags=("distance_guide",)
                )

        def draw_v_guide(x, y_start, y_end, dist_ft: float):
            line_id = self.canvas.create_line(
                x, y_start, x, y_end, dash=(4, 3), width=1, fill="#BFBFBF",
                tags=("distance_guide",)
            )
            self.canvas.tag_lower(line_id)
            if dist_ft > 0:
                midy = (y_start + y_end) / 2
                self.canvas.create_text(
                    x + 8, midy, text=f"{dist_ft:.1f} ft",
                    font=("TkDefaultFont", 8), fill="#666666", anchor="w",
                    tags=("distance_guide",)
                )

        # Horizontal guides: left / right (unchanged)
        draw_h_guide(px1, sx1, shed_cy, left_ft)
        draw_h_guide(sx2, px2, shed_cy, right_ft)

        # Vertical guides: SWAP which labels go top vs bottom
        # Top segment (py1..sy1) should show BACK
        draw_v_guide(shed_cx, py1, sy1, back_ft)
        # Bottom segment (sy2..py2) should show FRONT
        draw_v_guide(shed_cx, sy2, py2, front_ft)

        # --- NEW: colored shed→object guides ---
        if getattr(self, "show_object_distances", True):
            self._draw_shed_object_distances() 


    def rotate_shed_by_click(self, _event):
        self.rotate_shed(_event)
