from layout_data import LayoutData
from viewer import display_layout_canvas


def run_editor(layout: LayoutData, filename: str):
    def edit_rectangle(obj):
        prompts = {
            'width': f"{obj.name} width",
            'height': f"{obj.name} length",
            'x': f"Distance from left property line to {obj.name.lower()} (ft)",
            'y': f"Distance from front property line to {obj.name.lower()} (ft)"
        }
        print(f"\nEditing {obj.name}:")
        for field in ['width', 'height', 'x', 'y']:
            current = getattr(obj, field)
            prompt = f"{prompts[field]} ({current}): "
            entry = input(prompt).strip()
            if entry:
                try:
                    setattr(obj, field, float(entry))
                except ValueError:
                    print("Invalid value. Keeping previous.")

    def edit_point(obj):
        prompts = {
            'x': f"Distance from left property line to {obj.name.lower()} (ft)",
            'y': f"Distance from front property line to {obj.name.lower()} (ft)"
        }
        print(f"\nEditing {obj.name}:")
        for field in ['x', 'y']:
            current = getattr(obj, field)
            prompt = f"{prompts[field]} ({current}): "
            entry = input(prompt).strip()
            if entry:
                try:
                    setattr(obj, field, float(entry))
                except ValueError:
                    print("Invalid value. Keeping previous.")

    while True:
        print("\nWhich object would you like to edit?")
        print("1. House")
        print("2. Shed")
        print("3. Well")
        print("4. Septic Tank")
        print("5. Back to main menu")
        choice = input("Select an option: ").strip()

        if choice == "1":
            edit_rectangle(layout.house)
            display_layout_canvas(layout, filename)
        elif choice == "2":
            edit_rectangle(layout.shed)
            display_layout_canvas(layout, filename)
        elif choice == "3":
            edit_point(layout.well)
        elif choice == "4":
            edit_point(layout.septic)
        elif choice == "5":
            break
        else:
            print("Invalid option. Please try again.")

