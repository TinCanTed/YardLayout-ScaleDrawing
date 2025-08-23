import tkinter as tk
import tkinter.messagebox as msg
import json

from layout_canvas import LayoutCanvas

def display_layout_canvas(layout, filename):
    root = tk.Tk()
    root.title("Yard Layout Viewer")
    canvas_frame = LayoutCanvas(root, layout, filename)
    canvas_frame.pack(fill="both", expand=True)
    root.mainloop()

    # Silent save after canvas closes
    if filename and filename.endswith(".json"):
        with open(filename, 'w') as f:
            json.dump(layout.to_dict(), f, indent=2)
        msg.showinfo("Saved", "Changes to the layout have been saved.")

