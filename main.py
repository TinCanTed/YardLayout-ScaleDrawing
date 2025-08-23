import sys
import os
import platform
import subprocess
from layout_data import LayoutData, RectangleObject, PointObject
from file_handler import load_layout_from_file, save_layout_to_file
from editor import run_editor
from viewer import display_layout_canvas
from print_export import export_to_pdf
from layout_canvas_editor import prompt_object_inclusion

def prompt_float(label):
    while True:
        entry = input(f"{label}: ").strip().lower()
        if entry == 'b':
            return 'BACK'
        elif entry == 'r':
            return 'RESTART'
        elif entry == 'q':
            print("Quitting program.")
            sys.exit()
        try:
            return float(entry)
        except ValueError:
            print("Invalid number. Please enter a number, 'b', 'r', or 'q'.")

def get_layout_from_user():
    print("\n💡 Tip: Enter 'b' to go back, 'r' to restart, or 'q' to quit during input.")
    included_objects = prompt_object_inclusion()

    def collect_inputs(labels):
        values = []
        index = 0
        while index < len(labels):
            val = prompt_float(labels[index])
            if val == 'BACK':
                if index > 0:
                    index -= 1
                    values.pop()
                else:
                    print("Already at the first question.")
            elif val == 'RESTART':
                return 'RESTART'
            else:
                values.append(val)
                index += 1
        return values

    while True:
        print("\nEnter property boundary dimensions (in feet):")
        result = collect_inputs([
            "Left boundary",
            "Right boundary",
            "Front boundary",
            "Back boundary"
        ])
        if result == 'RESTART':
            continue

        # Assign values in order entered
        left, right, front, back = result

        layout = LayoutData(
            left=left,
            right=right,
            front=front,
            back=back,
            house=RectangleObject("House", 0, 0, 0, 0),
            shed=RectangleObject("Shed", 0, 0, 0, 0)
        )

        if included_objects['house']:
            print("\nEnter house dimensions (in feet):")
            result = collect_inputs([
                "House width (left to right)",
                "House depth (front to back)",
                "Distance from left propert line to house",
                "Distance from front property line to house"
            ])
            if result == 'RESTART':
                continue
            house_width, house_height, house_x, house_y = result
            layout.house = RectangleObject("House", house_width, house_height, house_x, house_y)

        if included_objects['well']:
            print("\nEnter well location:")
            result = collect_inputs([
                "Distance from left property line to well",
                "Distance from front property line to well"
            ])
            if result == 'RESTART':
                continue
            well_x, well_y = result
            #well_y = front - well_y  <==REMOVE
            layout.well = PointObject("Well", well_x, well_y)

        if included_objects['septic']:
            print("\nEnter septic tank location:")
            result = collect_inputs([
                "Distance from left property line to septic",
                "Distance from front property linen to septic"
            ])
            if result == 'RESTART':
                continue
            septic_x, septic_y = result
            #septic_y = front - septic_y <==REMOVE
            layout.septic = PointObject("Septic Tank", septic_x, septic_y)

        print("\nEnter shed dimensions and placement:")
        result = collect_inputs([
            "Shed width (left to right)",
            "Shed length (depth, front to back)",
            "Distance from left property line to shed",
            "Distance from front property line to shed"
        ])
        if result == 'RESTART':
            continue

        shed_width, shed_height, shed_x, shed_y = result
        layout.shed = RectangleObject("Shed", shed_width, shed_height, shed_x, shed_y)

        return layout

def main():
    layout = None
    filename = ""

    while True:
        print("\nMain Menu:")
        print("1. Create new layout")
        print("2. Load layout from file")
        print("3. Edit layout objects")
        print("4. Print existing PDF layout")
        print("5. Exit")

        choice = input("Select an option: ").strip()

        if choice == "1":
            layout = get_layout_from_user()

            from tkinter import filedialog
            filename = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON files", "*.json")],
                title="Save new layout as...",
                initialdir=os.path.expanduser("~/gui_scale_drawing/layouts")
            )

            if not filename:
                print("Save canceled.")
                continue

            save_layout_to_file(layout, filename)
            display_layout_canvas(layout, filename)
            auto_export_pdf(layout, filename)

        elif choice == "2":
            from tkinter import filedialog

            file_path = filedialog.askopenfilename(
                defaultextension=".json",
                filetypes=[("JSON files", "*.json")],
                title="Select layout to load",
                initialdir=os.path.expanduser("~/gui_scale_drawing/layouts")
            )
            if file_path:
                try:
                    layout, filename = load_layout_from_file(file_path)
                    print("Layout loaded successfully.")
                    display_layout_canvas(layout, filename)
                    auto_export_pdf(layout, filename)
                except Exception as e:
                    print(f"Error loading file: {e}")
            else:
                print("No file selected.")

        elif choice == "3":
            from tkinter import filedialog
            file_path = filedialog.askopenfilename(
                defaultextension=".json",
                filetypes=[("JSON files", "*.json")],
                title="Select layout to edit",
                initialdir=os.path.expanduser("~/gui_scale_drawing/layouts")
            )
            if file_path:
                try:
                    layout, filename = load_layout_from_file(file_path)
                    run_editor(layout, filename)
                    save_layout_to_file(layout, filename)

                    view_now = input("Would you like to view the updated layout now? (y/n): ").strip().lower()
                    if view_now == 'y':
                        display_layout_canvas(layout, filename)

                    auto_export_pdf(layout, filename)
                    print("Changes saved successfully.")

                except Exception as e:
                    print(f"Error loading or editing file: {e}")
            else:
                print("No file selected.")

        elif choice == "4":
            from tkinter import filedialog
            pdf_path = filedialog.askopenfilename(
                defaultextension=".pdf",
                filetypes=[("PDF files", "*.pdf")],
                title="Select PDF layout to print",
                initialdir=os.path.expanduser("~/gui_scale_drawing/print")
            )
            if pdf_path:
                open_pdf(pdf_path)
            else:
                print("No PDF file selected.")

        elif choice == "5":
            print("Exiting. Have a great day, Charlie!")
            break

        else:
            print("Invalid choice. Please try again.")

def auto_export_pdf(layout, filename):
    export_dir = os.path.expanduser("~/gui_scale_drawing/print")
    os.makedirs(export_dir, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(filename))[0]
    pdf_path = os.path.join(export_dir, base_name + ".pdf")
    export_to_pdf(layout, pdf_path)

def open_pdf(pdf_path):
    try:
        if hasattr(os, "startfile"):
            os.startfile(pdf_path)  # type: ignore[attr-defined]
        elif platform.system() == "Darwin":
            subprocess.run(["open", pdf_path])
        else:
            subprocess.run(["xdg-open", pdf_path])
    except Exception as e:
        print(f"Unable to open PDF: {e}")

if __name__ == "__main__":
    main()

