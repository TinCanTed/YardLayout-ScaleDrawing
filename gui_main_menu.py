#ruff check . gui_main_menu.py
import tkinter as tk
import re
import os
import sys
import subprocess
from tkinter import ttk, messagebox, filedialog
from typing import Optional
from layout_data import LayoutData, RectangleObject, PointObject
from pathlib import Path
from file_handler import load_layout_from_file, save_layout_to_file
from layout_canvas import LayoutCanvas
from print_export import export_to_pdf

# ---- App version (safe in frozen EXE) ----
APP_VERSION = "1.0.0"  # set your release version here

# ---- Stable, user-visible data root: Documents\ScaleDrawing ----
def get_user_data_root() -> Path:
    # Windows: C:\Users\<User>\Documents\ScaleDrawing
    # (Works fine on macOS/Linux too: ~/Documents/ScaleDrawing)
    docs = Path(os.environ.get("USERPROFILE", str(Path.home()))) / "Documents"
    base = docs / "ScaleDrawing"
    base.mkdir(parents=True, exist_ok=True)
    return base

def get_layouts_dir() -> Path:
    d = get_user_data_root() / "layouts"
    d.mkdir(parents=True, exist_ok=True)
    return d

def get_prints_dir() -> Path:
    d = get_user_data_root() / "print"
    d.mkdir(parents=True, exist_ok=True)
    return d

def ensure_app_dirs():
    get_layouts_dir()
    get_prints_dir()

def pdf_path_for_layout(json_path: str | Path) -> Path:
    """Return the corresponding PDF path in the print/ dir for a given layout.json path"""
    json_path = Path(json_path)
    return get_prints_dir() / f"{json_path.stem}.pdf"

ICON_PATH =  "gui_icon.ico"

def open_editor_window(root, layout, file_path):
    win = tk.Toplevel(root)
    win.title(f"Layout Editor — v{APP_VERSION}")
    try:
        win.iconbitmap(ICON_PATH)
    except Exception:
        pass

    # ✅ Enable normal Windows chrome buttons
    win.resizable(True, True)   # allow maximize
    win.minsize(640, 480)       # optional: don’t let it shrink too small

    # (Optional) start maximized
    try:
        win.state("zoomed")     # Windows
    except Exception:
        pass

    # Make it a true child of the menu so it stays on top
    # win.transient(root)

    # --- Keyboard toggle (F11) ---
    def _toggle_maximize(event=None):
        win.state("normal" if win.state() == "zoomed" else "zoomed")

    win.bind("<F11>", _toggle_maximize)

    # continue building editor...

    # Create the editor frame (LayoutCanvas) with hard error surfacing
    try:
        editor = LayoutCanvas(win, layout, file_path)
    except Exception as e:
        try:
            import traceback
            tb = traceback.format_exc()
        except Exception:
            tb = ""
        messagebox.showerror(
            "Editor Error (LayoutCanvas)",
            f"{e}\n\nDetails:\n{tb}"
        )
        try:
            win.destroy()
        except Exception:
            pass
        return None

    editor.pack(fill="both", expand=True)

    # Show & raise the window BEFORE withdrawing the menu
    try:
        win.update_idletasks()
        # center-ish
        sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
        ww, wh = max(600, min(sw - 100, 1000)), max(400, min(sh - 100, 800))
        x, y = (sw - ww) // 2, (sh - wh) // 3
        win.geometry(f"{ww}x{wh}+{x}+{y}")
    except Exception:
        pass

    # Bring it to the front
    try:
        win.attributes("-topmost", True)
        win.update()
        win.attributes("-topmost", False)
        win.lift()
        win.focus_force()
    except Exception:
        pass

    # Only now hide the menu
    try:
        root.withdraw()
    except Exception:
        pass

    # Close handler restores the menu
    def on_close():
        try:
            win.destroy()
        finally:
            try:
                root.deiconify()
                root.lift()
                root.focus_force()
            except Exception:
                pass

    win.protocol("WM_DELETE_WINDOW", on_close)

    # Avoid aggressive modal grabs for now (they can cause "invisible" hangs in some environments)
    # If you want modal behavior, you can re-enable grab_set after we confirm the window reliably shows.
    # try:
    #     win.grab_set()
    # except Exception:
    #     pass

    return win

# ==== UI THEME (shared) ====
APP_FONT_BASE   = ("Segoe UI", 13)
APP_FONT_HEADER = ("Segoe UI Semibold", 14)
APP_DIALOG_SIZE = "680x640"   # global dialog size

def apply_ttk_styles(root: tk.Misc) -> None:
    style = ttk.Style(root)
    style.configure("App.TLabel",        font=APP_FONT_BASE)
    style.configure("App.Header.TLabel", font=APP_FONT_HEADER)
    style.configure("App.TEntry",        font=APP_FONT_BASE)
    style.configure("App.TCheckbutton",  font=APP_FONT_BASE)
    style.configure("App.TButton",       font=APP_FONT_BASE)

class ButtonBar(tk.Frame):
    """Centered wide buttons for OK/Cancel/etc."""
    def __init__(self, parent, buttons):
        super().__init__(parent)
        for text, cmd in buttons:
            b = tk.Button(self, text=text, font=APP_FONT_BASE, width=14, command=cmd)
            b.pack(side="left", padx=10)

# ---------- Create New Layout dialog ----------
class NewLayoutDialog(tk.Toplevel):
    def __init__(self, parent: tk.Misc, initial: Optional[LayoutData] = None):
        super().__init__(parent)
        import tkinter.font as tkfont
        self.form_font = tkfont.Font(family="Segoe UI", size=14)  # bump to 14 if you want bigger
        self.initial = initial # <- store the layout to pre-fill from
        self.title("Edit Layout" if initial else "Create New Layout")
        self.geometry(APP_DIALOG_SIZE)     # use global constant
        self.minsize(720, 960)
        self.resizable(True, True)
        self.result: Optional[LayoutData] = None

        try:
            # --- Build UI start ---
    

            # Root grid
            self.columnconfigure(0, weight=1)
            self.rowconfigure(0, weight=1)

            # Content frame
            content = ttk.Frame(self, padding=14)
            content.grid(row=0, column=0, sticky="nsew")
            content.columnconfigure(0, weight=0)  # labels
            content.columnconfigure(1, weight=1)  # fields

            self.entries = {}     # label_text -> ttk.Entry
            self.check_vars = {}  # name -> tk.BooleanVar
            r = 0

            # Boundaries
            ttk.Label(content, text="Boundaries (feet) — required",
                      style="App.Header.TLabel").grid(row=r, column=0, columnspan=2,
                                                      sticky="w", pady=(0, 8))
            r += 1
            r = self._row(content, r, "Front Property Line (ft)", key="front")
            r = self._row(content, r, "Back Property Line (ft)",  key="back")
            r = self._row(content, r, "Left Property Line (ft)",  key="left")
            r = self._row(content, r, "Right Property Line (ft)", key="right")
            # <--- add vertical spacer row before next section
            ttk.Label(content, text="").grid(row=r, column=0, pady=6)
            r += 1

            # ---------- House ----------
            self.check_vars["House"] = tk.BooleanVar(
                value=True if self.initial is None else bool(self.initial.house)
            )

            house_cb = tk.Checkbutton(
                content,
                text="Include House",
                variable=self.check_vars["House"],
                command=self._toggle_house,     # wires to the toggle method below
                font=self.form_font
            )
            house_cb.grid(row=r, column=0, columnspan=2, sticky="w", pady=(0, 4))
            r += 1

            # A dedicated frame to hold all "House" inputs
            self.house_frame = ttk.Frame(content)
            self.house_frame.grid(row=r, column=0, columnspan=2, sticky="w")
            self.house_frame.columnconfigure(0, weight=0)  # label col
            self.house_frame.columnconfigure(1, weight=0)  # entry col (lets entries expand)
            # build the House rows *inside* the frame
            hr = 0
            hr = self._row(self.house_frame, hr, "House Width (left to right) (ft)", key="house_width")
            hr = self._row(self.house_frame, hr, "House Depth (front to back) (ft)", key="house_height")
            hr = self._row(self.house_frame, hr, "House distance from left property line (ft)", key="house_x")
            hr = self._row(self.house_frame, hr, "House distance from front property line (ft)", key="house_y")
            r += 1

            # spacer before Shed
            ttk.Label(content, text="").grid(row=r, column=0, pady=6)
            r += 1

            # ---------- Shed ----------
            self.check_vars["Shed"] = tk.BooleanVar(
            value=False if self.initial is None else bool(self.initial.shed)
            )

            shed_cb = tk.Checkbutton(
                content,
                text="Include Shed",
                variable=self.check_vars["Shed"],
                command=self._toggle_shed,
                font=self.form_font
            )
            shed_cb.grid(row=r, column=0, columnspan=2, sticky="w", pady=(0, 4))
            r += 1

            # Frame to hold all Shed inputs
            self.shed_frame = ttk.Frame(content)
            self.shed_frame.grid(row=r, column=0, columnspan=2, sticky="w")
            self.shed_frame.columnconfigure(0, weight=0)  # label col
            self.shed_frame.columnconfigure(1, weight=0)  # entry col

            # Build Shed rows *inside* the frame
            sr = 0
            sr = self._row(self.shed_frame, sr, "Shed Width (left to right) (ft)",        key="shed_width")
            sr = self._row(self.shed_frame, sr, "Shed Depth (front to back) (ft)",        key="shed_height")
            sr = self._row(self.shed_frame, sr, "Shed distance from left property line (ft)",  key="shed_x")
            sr = self._row(self.shed_frame, sr, "Shed distance from front property line (ft)", key="shed_y")
            r += 1  # move to next grid row in 'content'

            # spacer before Well
            ttk.Label(content, text="").grid(row=r, column=0, pady=6)
            r += 1

            
            # ---------- Well ----------
            self.check_vars["Well"] = tk.BooleanVar(
                value=False if self.initial is None else bool(self.initial.well)
            )

            well_cb = tk.Checkbutton(
                content,
                text="Include Well",
                variable=self.check_vars["Well"],
                command=self._toggle_well,
                font=self.form_font
            )
            well_cb.grid(row=r, column=0, columnspan=2, sticky="w", pady=(0, 4))
            r += 1

            # Frame to hold all Well inputs
            self.well_frame = ttk.Frame(content)
            self.well_frame.grid(row=r, column=0, columnspan=2, sticky="w")
            self.well_frame.columnconfigure(0, weight=0)  # label col
            self.well_frame.columnconfigure(1, weight=0)  # entry col

            # Build Well rows *inside* the frame
            wr = 0
            wr = self._row(self.well_frame, wr, "Well distance from left property line (ft)", key="well_x")
            wr = self._row(self.well_frame, wr, "Well distance from front property line (ft)", key="well_y")
            r += 1  # move to next grid row in 'content'

            # spacer before Septic
            ttk.Label(content, text="").grid(row=r, column=0, pady=6)
            r += 1
            

            
            # ---------- Septic ----------
            self.check_vars["Septic Tank"] = tk.BooleanVar(
                value=False if self.initial is None else bool(getattr(self.initial, "septic", getattr(self.initial, "septic_tank", None)))
            )

            septic_cb = tk.Checkbutton(
                content,
                text="Include Septic Tank",
                variable=self.check_vars["Septic Tank"],
                command=self._toggle_septic,
                font=self.form_font
            )
            septic_cb.grid(row=r, column=0, columnspan=2, sticky="w", pady=(0, 4))
            r += 1

            # Frame to hold all Septic inputs
            self.septic_frame = ttk.Frame(content)
            self.septic_frame.grid(row=r, column=0, columnspan=2, sticky="w")
            self.septic_frame.columnconfigure(0, weight=0)  # label col
            self.septic_frame.columnconfigure(1, weight=0)  # entry col

            # Build Septic rows *inside* the frame
            pr = 0
            pr = self._row(self.septic_frame, pr, "Tank distance from left property line (ft)", key="septic_x")
            pr = self._row(self.septic_frame, pr, "Tank distance from front property line (ft)", key="septic_y")
            # <--- add vertical spacer row before next section
            ttk.Label(content, text="").grid(row=r, column=0, pady=6)
            r += 1  # move to next grid row in 'content'

            # Buttons (centered)
            btn_text = "Save" if initial else "Create"
            btns = ButtonBar(content, [
                ("Cancel", self._cancel),
                (btn_text, self._create),
            ])

            btns.grid(row=r, column=0, columnspan=2, sticky="e", pady=(16, 0))  

            # Initial toggles 
            self._toggle_house()
            self._toggle_shed()
            self._toggle_well()
            self._toggle_septic()

            # Modal
            self.transient(self.master)
            self.grab_set()
            self.protocol("WM_DELETE_WINDOW", self._cancel)
            self.wait_visibility()
            self.focus_set()

            # --- build UI end ---

        # Wrap the form build in a try/except to surface the real error for debugging
        except Exception as e:
            messagebox.showerror("Dialog Error", f"Failed to build form:\n{e}")
            return    

    # helpers
    def _row(self, parent, row, label_text, key=None):
        # label
        ttk.Label(parent, text=label_text, font=self.form_font).grid(
            row=row, column=0, sticky="w", padx=(0, 10)
        )
        # allow up to 5 digits, optional decimal point + up to 2 decimals
        v_re = re.compile(r"^\d{0,5}(\.\d{0,2})?$")
        vcmd = (self.register(lambda P: (P == "") or bool(v_re.match(P))), "%P")

        # short numeric entry: ~5 chars, right aligned, no stretching
        entry = ttk.Entry(
            parent,
            font=self.form_font,
            width=6,
            justify="right",
            validate="key",
            validatecommand=vcmd,
        )
        entry.grid(row=row, column=1, sticky="w")

        # Store by label (for display lookups) and by stable key (for logic)
        self.entries[label_text] = entry
        if key:
            self.entries[key] = entry 


        # prefill in Edit mode
        if key and self.initial:
            val = self._get_initial_by_key(key, self.initial)
            if val is not None:
                entry.insert(0, str(val))

        return row + 1

    def _get_initial_by_key(self, key: str, ld: LayoutData):
        # Boundaries
        if key == "front":
            return ld.front
        if key == "back":
            return ld.back
        if key == "left":
            return ld.left
        if key == "right":
            return ld.right

        # House (RectangleObject)
        if key == "house_width":
            return ld.house.width if ld.house else None
        if key == "house_height":
            return ld.house.height if ld.house else None
        if key == "house_x":
            return ld.house.x if ld.house else None
        if key == "house_y":
            return ld.house.y if ld.house else None

        # Shed (RectangleObject)
        if key == "shed_width":
            return ld.shed.width if ld.shed else None
        if key == "shed_height":
            return ld.shed.height if ld.shed else None
        if key == "shed_x":
            return ld.shed.x if ld.shed else None
        if key == "shed_y":
            return ld.shed.y if ld.shed else None

        # Well (PointObject)
        if key == "well_x":
            return ld.well.x if ld.well else None
        if key == "well_y":
            return ld.well.y if ld.well else None

        # Septic (RectangleObject) — change attribute name if your LayoutData uses 'septic_tank'
        septic = getattr(ld, "septic", None)  # or "septic_tank"
        if key == "septic_x":
            return septic.x if septic else None
        if key == "septic_y":
            return septic.y if septic else None

        return None
    
    def _toggle_house(self):
        if self.check_vars["House"].get():
            self.house_frame.grid()         # show
        else:
            self.house_frame.grid_remove()  #hide

    def _toggle_shed(self):
        if self.check_vars["Shed"].get():
            self.shed_frame.grid()         # show
        else:
            self.shed_frame.grid_remove()  # hide

    def _toggle_well(self):
        if self.check_vars["Well"].get():
            self.well_frame.grid()         # show
        else:
            self.well_frame.grid_remove()  # hide

    def _toggle_septic(self):
        if self.check_vars["Septic Tank"].get():
            self.septic_frame.grid()         # show
        else:
            self.septic_frame.grid_remove()  # hide

    def _cancel(self):
        self.result = None
        self.destroy()

    def _req(self, name: str) -> float:
        """
        Fetch a required numeric field by stable key (preferred) or label text.
        Raises ValueError if empty; KeyError if the field isn't found.
        """
        entry = self.entries.get(name)
        if entry is None:
            raise KeyError(f"Field not found: {name}")
        v = entry.get().strip()
        if v == "":
            raise ValueError(f"{name} is required.")
        return float(v)

    def _create(self):
        try:
            # Required boundaries
            front = self._req("front")
            back  = self._req("back")
            left  = self._req("left")
            right = self._req("right")

            # Optional objects based on checkboxes
            house = None
            if self.check_vars["House"].get():
                house = RectangleObject(
                    name="House",
                    width=self._req("house_width"),
                    height=self._req("house_height"),
                    x=self._req("house_x"),
                    y=self._req("house_y"),
                )

            shed = None
            if self.check_vars["Shed"].get():
                shed = RectangleObject(
                    name="Shed",
                    width=self._req("shed_width"),
                    height=self._req("shed_height"),
                    x=self._req("shed_x"),
                    y=self._req("shed_y"),
                )

            well = None
            if self.check_vars["Well"].get():
                well = PointObject(
                    name="Well",
                    x=self._req("well_x"),
                    y=self._req("well_y"),
                )

            septic = None
            if self.check_vars["Septic Tank"].get():
                septic = PointObject(
                    name="Septic Tank",
                    x=self._req("septic_x"),
                    y=self._req("septic_y"),
                )                    

            self.result = LayoutData(
                front=front, back=back, left=left, right=right,
                house=house, shed=shed, well=well, septic=septic
            )
            self.destroy()

        except (ValueError, KeyError) as e:
            mode = "Edit Layout" if self.initial else "Create Layout"
            messagebox.showerror(f"{mode} - Invalid input", str(e), parent=self)
            return


# Accept an optional initial layout to pre-fill the form
def prompt_for_new_layout(initial: Optional[LayoutData] = None) -> Optional[LayoutData]:
    root = tk._default_root  # or your main Tk instance
    dlg = NewLayoutDialog(root, initial=initial)  # pass it into the dialog
    root.wait_window(dlg)
    return dlg.result

# ---------- App state ----------
current_file_path: Optional[str] = None
current_layout_data: Optional[LayoutData] = None

# ---------- Button handlers ----------
def on_create_new():
    global current_layout_data, current_file_path
    layout = prompt_for_new_layout()
    if layout is None:
        return  # user cancelled

    path = filedialog.asksaveasfilename(
        title="Save New Layout",
        initialdir=str(get_layouts_dir()),
        defaultextension=".json",
        filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
    )
    if not path:
        return  # user cancelled

    try:
        save_layout_to_file(layout, path)  # write JSON to disk

        # Update app state
        current_layout_data = layout
        current_file_path = path

        # --- Auto-generate PDF into print/ ---
        try:
            out_pdf = pdf_path_for_layout(current_file_path)
            export_to_pdf(current_layout_data, str(out_pdf))  # adjust if your signature differs
        except Exception as e:
            # Non-fatal: JSON saved OK; just warn about PDF
            messagebox.showwarning("PDF Export",
                                   f"Saved layout.json but failed to create PDF:\n{e}")
        win = open_editor_window(root, current_layout_data, current_file_path)
        if win is None:
            return

        try:
            win.update()
            win.deiconify()
            win.lift()
            win.focus_force()
        except Exception:
            pass

        root.wait_window(win)

    except Exception as e:
        messagebox.showerror("Save Error", f"Failed to save layout:\n{e}")

def on_open_existing():
    global current_layout_data, current_file_path
    path = filedialog.askopenfilename(
        title="Open layout JSON",
        initialdir=str(get_layouts_dir()),
        filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
    )
    if not path:
        return

    try:
        result = load_layout_from_file(path)
        # Handle both return styles: (layout, path) or just layout
        if isinstance(result, tuple) and len(result) == 2:
            current_layout_data, current_file_path = result
        else:
            current_layout_data = result
            current_file_path = path
        win = open_editor_window(root, current_layout_data, current_file_path)
        if win is None:
            return

        try:
            win.update()
            win.deiconify()
            win.lift()
            win.focus_force()
        except Exception:
            pass

        root.wait_window(win)

    except Exception as e:
        messagebox.showerror("Load Error", f"Failed to load layout:\n{e}")

def on_edit_layout():
    global current_layout_data, current_file_path

    # Always ask the user to pick a file to edit
    path = filedialog.askopenfilename(
        title="Choose a layout to edit",
        initialdir=str(get_layouts_dir()),
        filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
    )
    if not path:
        return  # user cancelled

    # Load the chosen file
    try:
        result = load_layout_from_file(path)
        if isinstance(result, tuple) and len(result) == 2:
            layout, file_path = result
        else:
            layout, file_path = result, path
    except Exception as e:
        messagebox.showerror("Load Error", f"Failed to load layout:\n{e}")
        return

    # Open the same form, pre-filled with the chosen layout
    updated = prompt_for_new_layout(initial=layout)
    if updated is None:
        return  # user cancelled the edit dialog

    # Save changes back to the chosen file
    try:
        save_layout_to_file(updated, file_path)
    except Exception as e:
        messagebox.showerror("Save Error", f"Failed to save layout:\n{e}")
        return

    # Update app state
    current_layout_data = updated
    current_file_path = file_path

    # --- Auto-generate PDF into print/ ---
    try:
        out_pdf = pdf_path_for_layout(current_file_path)
        export_to_pdf(current_layout_data, str(out_pdf))  # adjust if your signature differs
    except Exception as e:
        # Non-fatal: JSON saved OK; just warn about PDF
        messagebox.showwarning("PDF Export",
                                f"Saved layout.json but failed to create PDF:\n{e}")

    # Open the editor window with the updated data
    win = open_editor_window(root, current_layout_data, current_file_path)
    if win is None:
        return

    try:
        win.update()
        win.deiconify()
        win.lift()
        win.focus_force()
    except Exception:
        pass

    root.wait_window(win)

def open_pdf(path: str) -> None:
    try:
        if os.name == "nt":                 # Windows
            os.startfile(path)
        elif sys.platform == "darwin":      # macOS
            subprocess.run(["open", path], check=False)
        else:                               # Linux
            subprocess.run(["xdg-open", path], check=False)
    except Exception as e:
        messagebox.showerror("Open PDF", f"Could not open PDF:\n{e}")

def on_print_pdf():
    # always show the picker; don’t require a loaded layout
    ensure_app_dirs()  # makes 'print/' if missing
    path = filedialog.askopenfilename(
        title="Choose a PDF to view/print",
        initialdir=str(get_prints_dir()),
        filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
    )
    if not path:
        return
    open_pdf(path)

def on_exit():
    root.destroy()

# ---------- Main window ----------
ensure_app_dirs()       # make sure layouts/ and print/ exist
root = tk.Tk()
apply_ttk_styles(root)  # apply shared fonts/styles once

root.title(f"Scale Drawing Menu v{APP_VERSION}")
root.geometry("400x420")
root.resizable(False, False)
try:
    root.iconbitmap(ICON_PATH)
except Exception:
    pass

MENU_FONT_BTN   = APP_FONT_BASE

ttk.Label(root, text="🧰 Scale Drawing Program", style="App.Header.TLabel").pack(pady=20)
tk.Button(root, text="🆕  Create New Layout",    width=32, font=MENU_FONT_BTN, command=on_create_new).pack(pady=6)
tk.Button(root, text="📂  Open Existing Layout", width=32, font=MENU_FONT_BTN, command=on_open_existing).pack(pady=6)
tk.Button(root, text="✏️  Edit Layout",          width=32, font=MENU_FONT_BTN, command=on_edit_layout).pack(pady=6)
tk.Button(root, text="🖨️  Print PDF",        width=32, font=MENU_FONT_BTN, command=on_print_pdf).pack(pady=6)
tk.Button(root, text="❌  Exit",                  width=32, font=MENU_FONT_BTN, command=on_exit).pack(pady=18)

root.mainloop()

