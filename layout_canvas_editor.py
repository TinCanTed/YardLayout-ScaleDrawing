import tkinter as tk
from tkinter import messagebox
from file_handler import save_layout_to_file

class LayoutCanvas(tk.Frame):
    def __init__(self, master, layout, source_filename):
        super().__init__(master)
        self.master = master
        self.layout = layout
        self.source_filename = source_filename
        self.modified = False

        # Setup canvas
        self.canvas = tk.Canvas(self, width=850, height=650, bg="white")
        self.canvas.pack()

        self.canvas.tag_bind("draggable", "<ButtonPress-1>", self.on_drag_start)
        self.canvas.tag_bind("draggable", "<B1-Motion>", self.on_drag_move)
        self.canvas.tag_bind("draggable", "<ButtonRelease-1>", self.on_drag_release)

        self.drag_data = {"tag": None, "offset_x": 0, "offset_y": 0}
        self.draw_objects()

        # Track window close
        self.master.protocol("WM_DELETE_WINDOW", self.on_close)

    def draw_objects(self):
        # Draw all layout objects here...
        pass

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
        if tag:
            items = self.canvas.find_withtag(tag)
            if items:
                bbox = self.canvas.bbox(items[0])
                x = bbox[0] / 10  # Assuming 10px per foot, adjust as needed
                y = bbox[1] / 10
                self.layout.update_object_position(tag.replace("_", " ").title(), x, y)
                self.modified = True  # Mark as changed
        self.drag_data["tag"] = None

    def on_close(self):
        if self.modified:
            if messagebox.askyesno("Save Changes", "Save changes to layout?"):
                save_layout_to_file(self.layout, self.source_filename)
        self.master.destroy()

    def set_show_distance_guides(self, on: bool) -> None:
        """Toggle showing shed-to-property distance guides (placeholder)."""
        print(f"[DEBUG] Distance guides {'enabled' if on else 'disabled'} (not yet implemented)")
    

# You would call this from main.py like so:
# window = tk.Tk()
# editor = LayoutCanvas(window, layout, "filename.json")
# editor.pack(fill="both", expand=True)
# window.mainloop()

def prompt_object_inclusion():
    def ask(prompt):
        response = input(prompt + " (type 'y' to include, press Enter to skip): ").strip().lower()
        return response in ('y', 'yes')

    print("\nSelect which objects to include in your layout.")
    print("Leave the input blank (just press Enter) to skip adding that object.\n")

    include_house = ask("Include house?")
    include_well = ask("Include well?")
    include_septic = ask("Include septic tank?")

    return {
        'house': include_house,
        'well': include_well,
        'septic': include_septic
    }
# Example usage:
# included_objects = prompt_object_inclusion()
# if included_objects['house']:
#     # Create house...
# if included_objects['well']:
#     # Create well...
# if included_objects['septic']:
#     # Create septic tank...
