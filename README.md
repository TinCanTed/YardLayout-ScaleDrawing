# GUI Scale Drawing

A Python-based scale drawing tool for planning and visualizing property layouts, complete with drag-and-drop editing, rotation, automatic PDF export, and support for multiple layout objects like houses, sheds, wells, and septic tanks.

---

## 🧰 Features

- 📐 **To-scale grid drawing** (with labeled axes and dimensions)
- 🖱️ **Drag-and-drop object positioning**
- ↩️ **Rotate the shed with a click**
- 📝 **User-friendly prompts for layout dimensions and object placement**
- 💾 **Save/load from `.json` files**
- 🖨️ **Automatic export to landscape PDF**
- ✅ **Layout reflects user perspective: standing at the front looking in**
- 🔁 **Flip logic maintains accurate vertical orientation for front/back input**
- 🪟 **Tkinter-based graphical viewer with zoom in/out controls**

---

## 🗂️ Project Structure


gui_scale_drawing/
├── main.py # Main control center with menu interface
├── layout_data.py # Classes for LayoutData, RectangleObject, PointObject
├── layout_canvas.py # Tkinter canvas for interactive layout drawing
├── file_handler.py # Load/save layout from/to JSON
├── print_export.py # Export to landscape PDF
├── editor.py # Text-based layout editor (optional)
├── viewer.py # Launches LayoutCanvas from menu
├── README.md # You're looking at it!
├── layouts/ # Saved user layouts (.json)
└── print/ # Auto-exported layout PDFs

  
---

## 🚀 Getting Started

### Requirements

- Python 3.11+
- Tkinter (usually included with Python)
- No third-party libraries required!

### Run the app

```bash
python3 main.py

  Choose from the menu to:

    Create a new layout

    Load a saved layout

    Edit a layout

    Print an exported layout

Every layout is automatically exported as a PDF (landscape format) to:
  ~/gui_scale_drawing/print/

  📏 Layout Orientation

    Bottom (Front) of the property is at the bottom of the grid

    Top (Back) of the property is at the top of the grid

    Objects are placed based on distance from the front or left, as if you were standing at the front edge of your property looking in

🧪 Future Plans

    Add more object types (trees, fences, pools)

    Snap-to-grid toggle

    Object resizing handles

    Windows executable (.exe) for non-technical users

🙏 Acknowledgments

Created with ❤️ by Charles & Sam, one bug at a time.






