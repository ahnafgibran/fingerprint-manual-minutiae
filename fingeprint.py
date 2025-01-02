import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk, ImageDraw
import math

# Define colors for minutiae types
ENDING_COLOR = "blue"
BIFURCATION_COLOR = "red"


class FingerprintApp:
    def __init__(self, master):
        self.master = master
        master.title("Fingerprint Minutiae Marking")

        # Initialize variables
        self.image_path = None
        self.image = None
        self.photo = None
        self.minutiae = []  # Store minutiae data (x, y, angle, quality, type)
        self.current_minutiae_type = "ending"  # Default type
        self.current_quality = "not set"

        # Create GUI elements
        self.create_widgets()

    def create_widgets(self):
        # Frame for image display
        self.image_frame = tk.Frame(self.master)
        self.image_frame.pack()

        # Canvas to display the image
        self.canvas = tk.Canvas(self.image_frame, width=500, height=500)
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self.mark_minutiae)

        # --- Control Panel ---
        control_frame = tk.Frame(self.master)
        control_frame.pack()

        # Load Image Button
        tk.Button(control_frame, text="Load Image", command=self.load_image).pack(
            side=tk.LEFT
        )

        # Minutiae Type Selection
        type_label = tk.Label(control_frame, text="Type:")
        type_label.pack(side=tk.LEFT)
        self.type_var = tk.StringVar(value="ending")
        tk.Radiobutton(
            control_frame,
            text="Ending",
            variable=self.type_var,
            value="ending",
            command=self.update_type,
        ).pack(side=tk.LEFT)
        tk.Radiobutton(
            control_frame,
            text="Bifurcation",
            variable=self.type_var,
            value="bifurcation",
            command=self.update_type,
        ).pack(side=tk.LEFT)

        # Quality Selection
        quality_label = tk.Label(control_frame, text="Quality:")
        quality_label.pack(side=tk.LEFT)
        self.quality_var = tk.StringVar(value="not set")
        quality_options = ["not set", "poor", "fair", "good", "very good", "excellent"]
        quality_dropdown = tk.OptionMenu(
            control_frame,
            self.quality_var,
            *quality_options,
            command=self.update_quality,
        )
        quality_dropdown.pack(side=tk.LEFT)

        # Angle Input
        angle_label = tk.Label(control_frame, text="Angle (degrees):")
        angle_label.pack(side=tk.LEFT)
        self.angle_entry = tk.Entry(control_frame, width=5)
        self.angle_entry.pack(side=tk.LEFT)

        # Save Minutiae Button
        tk.Button(control_frame, text="Save Minutiae", command=self.save_minutiae).pack(
            side=tk.LEFT
        )

        # Display current minutiae List
        self.minutiae_list = tk.Listbox(self.master)
        self.minutiae_list.pack(fill="x")

    def load_image(self):
        self.image_path = filedialog.askopenfilename(
            defaultextension=".png",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp *.tif *.tiff")],
        )
        if self.image_path:
            self.image = Image.open(self.image_path)
            self.photo = ImageTk.PhotoImage(self.image)
            self.canvas.config(width=self.image.width, height=self.image.height)
            self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)

    def mark_minutiae(self, event):
        x = event.x
        y = event.y

        # Get angle from input
        try:
            angle = float(self.angle_entry.get())
        except ValueError:
            angle = 0.0  # Default angle if input is invalid

        # Determine color based on type
        color = (
            ENDING_COLOR
            if self.current_minutiae_type == "ending"
            else BIFURCATION_COLOR
        )

        # Draw a small circle on the canvas
        radius = 3  # Radius of the circle
        minutiae_id = self.canvas.create_oval(
            x - radius, y - radius, x + radius, y + radius, fill=color
        )

        # Add minutiae data to the list
        minutiae_data = (
            x,
            y,
            angle,
            self.current_quality,
            self.current_minutiae_type,
            minutiae_id,
        )  # Include minutiae_id
        self.minutiae.append(minutiae_data)

        # Update the minutiae listbox
        self.update_minutiae_listbox()

        # Update minutiae data in the list
        self.minutiae[len(self.minutiae) - 1] = minutiae_data

        # Print minutiae data to console
        print(
            f"Minutiae added: Type={self.current_minutiae_type}, X={x}, Y={y}, Angle={angle}, Quality={self.current_quality}"
        )

    def update_type(self):
        self.current_minutiae_type = self.type_var.get()

    def update_quality(self, quality):
        self.current_quality = quality

    def update_minutiae_listbox(self):
        self.minutiae_list.delete(0, tk.END)  # Clear the listbox
        for x, y, angle, quality, m_type, _ in self.minutiae:
            self.minutiae_list.insert(
                tk.END,
                f"Type: {m_type}, X: {x}, Y: {y}, Angle: {angle}, Quality: {quality}",
            )

    def save_minutiae(self):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt", filetypes=[("Text files", "*.txt")]
        )
        if file_path:
            try:
                with open(file_path, "w") as f:
                    for x, y, angle, quality, m_type, _ in self.minutiae:
                        f.write(f"{m_type},{x},{y},{angle},{quality}\n")
                messagebox.showinfo("Info", "Minutiae saved successfully!")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save minutiae: {e}")
