import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk, ImageDraw
import math

# Define colors for minutiae types
ENDING_COLOR = "red"
BIFURCATION_COLOR = "green"
ACTIVE_COLOR = "yellow"  # Color for highlighting the active minutiae


class FingerprintApp:
    def __init__(self, master):
        self.master = master
        master.title("Fingerprint Minutiae Marking")

        # Initialize variables
        self.image_path = None
        self.image = None
        self.photo = None
        self.minutiae = (
            []
        )  # Store minutiae data (x, y, angle, quality, type, id, orientation_line_id)
        self.current_minutiae_type = "ending"
        self.current_quality = "not set"
        self.zoom_level = 1.0
        self.original_image = None  # Store the original image for resizing
        self.canvas_width = 500  # Default canvas width
        self.canvas_height = 500  # Default canvas height
        self.active_minutiae_index = (
            None  # Track the index of the currently active minutiae
        )
        self.active_minutiae_circle_id = (
            None  # ID of the yellow circle for active minutiae
        )
        self.editor_mode = False  # Flag to indicate editor mode
        self.dragged_minutiae_index = None  # Index of the minutiae being dragged
        self.dragged_line_end = (
            None  # Which end of the line is being dragged (None, 'start', 'end')
        )

        # Create GUI elements
        self.create_widgets()

    def create_widgets(self):
        # PanedWindow for resizable divider
        self.paned_window = ttk.Panedwindow(self.master, orient=tk.HORIZONTAL)
        self.paned_window.pack(fill=tk.BOTH, expand=1)

        # Frame for image display
        self.image_frame = tk.Frame(self.paned_window)
        self.paned_window.add(self.image_frame, weight=1)

        # Canvas to display the image
        self.canvas = tk.Canvas(
            self.image_frame,
            width=self.canvas_width,
            height=self.canvas_height,
            bg="lightgray",
        )
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Create scrollbars
        self.hbar = tk.Scrollbar(self.image_frame, orient=tk.HORIZONTAL)
        self.hbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.hbar.config(command=self.canvas.xview)
        self.vbar = tk.Scrollbar(self.image_frame, orient=tk.VERTICAL)
        self.vbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.vbar.config(command=self.canvas.yview)

        # Configure canvas to use scrollbars
        self.canvas.config(xscrollcommand=self.hbar.set, yscrollcommand=self.vbar.set)

        # Bind mouse wheel events
        self.canvas.bind(
            "<Control-MouseWheel>", self.zoom
        )  # Ctrl + Mouse Wheel for zooming
        self.canvas.bind("<Button-1>", self.on_canvas_click)  # Handle clicks on canvas
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
        self.canvas.bind(
            "<Double-Button-1>", self.on_canvas_double_click
        )  # Handle double-clicks
        # Bind Ctrl++ and Ctrl+- for zooming
        self.master.bind("<Control-equal>", self.zoom_in)  # Ctrl and +
        self.master.bind("<Control-minus>", self.zoom_out)  # Ctrl and -

        # --- Control Panel ---
        control_frame = tk.Frame(self.paned_window)
        self.paned_window.add(control_frame, weight=0)

        # Load Image Button
        tk.Button(control_frame, text="Load Image", command=self.load_image).pack(
            side=tk.TOP, fill=tk.X
        )

        # Minutiae Type Selection
        type_label = tk.Label(control_frame, text="Type:")
        type_label.pack(side=tk.TOP)
        self.type_var = tk.StringVar(value="ending")
        tk.Radiobutton(
            control_frame,
            text="Ending",
            variable=self.type_var,
            value="ending",
            command=self.update_type,
        ).pack(side=tk.TOP)
        tk.Radiobutton(
            control_frame,
            text="Bifurcation",
            variable=self.type_var,
            value="bifurcation",
            command=self.update_type,
        ).pack(side=tk.TOP)

        # Quality Selection
        quality_label = tk.Label(control_frame, text="Quality:")
        quality_label.pack(side=tk.TOP)
        self.quality_var = tk.StringVar(value="not set")
        quality_options = ["not set", "poor", "fair", "good", "very good", "excellent"]
        quality_dropdown = tk.OptionMenu(
            control_frame,
            self.quality_var,
            *quality_options,
            command=self.update_quality,
        )
        quality_dropdown.pack(side=tk.TOP)

        # Angle Input
        angle_label = tk.Label(control_frame, text="Angle (degrees):")
        angle_label.pack(side=tk.TOP)
        self.angle_entry = tk.Entry(control_frame, width=5)
        self.angle_entry.pack(side=tk.TOP)

        # Save Minutiae Button
        tk.Button(control_frame, text="Save Minutiae", command=self.save_minutiae).pack(
            side=tk.TOP, fill=tk.X
        )

        # Editor Mode Toggle
        self.editor_mode_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            control_frame,
            text="Editor Mode",
            variable=self.editor_mode_var,
            command=self.toggle_editor_mode,
        ).pack(side=tk.TOP)

        # --- Minutiae Listbox Frame ---
        self.listbox_frame = tk.Frame(self.paned_window)
        self.paned_window.add(self.listbox_frame, weight=0)

        # Listbox to display minutiae
        self.minutiae_list = tk.Listbox(self.listbox_frame)
        self.minutiae_list.pack(fill="both", expand=True)
        self.minutiae_list.bind("<Double-Button-1>", self.edit_minutiae)
        self.minutiae_list.bind("<<ListboxSelect>>", self.on_minutiae_select)
        self.minutiae_list.bind("<Delete>", self.delete_minutiae)

        # Create entry widgets for editing (initially hidden)
        self.create_edit_widgets()

    def create_edit_widgets(self):
        # Frame for edit widgets (placed within listbox_frame)
        self.edit_frame = tk.Frame(self.listbox_frame)

        # Labels for edit fields
        tk.Label(self.edit_frame, text="Type:").grid(row=0, column=0)
        tk.Label(self.edit_frame, text="X:").grid(row=1, column=0)
        tk.Label(self.edit_frame, text="Y:").grid(row=2, column=0)
        tk.Label(self.edit_frame, text="Angle:").grid(row=3, column=0)
        tk.Label(self.edit_frame, text="Quality:").grid(row=4, column=0)

        # Entry widgets for editing
        self.edit_type_var = tk.StringVar()
        self.edit_x_entry = tk.Entry(self.edit_frame, width=5)
        self.edit_y_entry = tk.Entry(self.edit_frame, width=5)
        self.edit_angle_entry = tk.Entry(self.edit_frame, width=5)
        self.edit_quality_var = tk.StringVar()

        # Type radio buttons
        tk.Radiobutton(
            self.edit_frame,
            text="Ending",
            variable=self.edit_type_var,
            value="ending",
        ).grid(row=0, column=1)
        tk.Radiobutton(
            self.edit_frame,
            text="Bifurcation",
            variable=self.edit_type_var,
            value="bifurcation",
        ).grid(row=0, column=2)

        # X and Y entry
        self.edit_x_entry.grid(row=1, column=1)
        self.edit_y_entry.grid(row=2, column=1)

        # Angle entry
        self.edit_angle_entry.grid(row=3, column=1)

        # Quality dropdown
        quality_options = ["not set", "poor", "fair", "good", "very good", "excellent"]
        tk.OptionMenu(self.edit_frame, self.edit_quality_var, *quality_options).grid(
            row=4, column=1
        )

        # Update Button
        self.update_button = tk.Button(
            self.edit_frame, text="Update", command=self.update_minutiae
        )
        self.update_button.grid(row=5, column=1)

        # Cancel Button
        self.cancel_button = tk.Button(
            self.edit_frame, text="Cancel", command=self.cancel_edit
        )
        self.cancel_button.grid(row=5, column=2)

        # Bind Enter key to update minutiae in edit mode
        self.edit_x_entry.bind("<Return>", self.update_minutiae_from_entry)
        self.edit_y_entry.bind("<Return>", self.update_minutiae_from_entry)
        self.edit_angle_entry.bind("<Return>", self.update_minutiae_from_entry)

    def load_image(self):
        self.image_path = filedialog.askopenfilename(
            defaultextension=".png",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp *.tif *.tiff")],
        )
        if self.image_path:
            self.original_image = Image.open(self.image_path)
            self.image = self.original_image.copy()
            self.zoom_level = 1.0
            self.display_image()
            self.redraw_minutiae()

    def mark_minutiae(self, event):
        if not self.image:
            return

        # Convert canvas coordinates to image coordinates
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        image_x = int(canvas_x / self.zoom_level)
        image_y = int(canvas_y / self.zoom_level)

        # Check if the point is within the image boundaries
        if 0 <= image_x < self.image.width and 0 <= image_y < self.image.height:
            # Get angle from input
            try:
                angle = int(self.angle_entry.get())
            except ValueError:
                angle = 0  # Default angle if input is invalid

            # Determine color based on type
            color = (
                ENDING_COLOR
                if self.current_minutiae_type == "ending"
                else BIFURCATION_COLOR
            )

            # Draw a small circle on the canvas and store the id
            radius = 3
            zoomed_radius = radius * self.zoom_level
            minutiae_id = self.canvas.create_oval(
                canvas_x - zoomed_radius,
                canvas_y - zoomed_radius,
                canvas_x + zoomed_radius,
                canvas_y + zoomed_radius,
                fill=color,
            )

            # Draw orientation line and store the id
            line_length = 15
            zoomed_line_length = line_length * self.zoom_level
            angle_rad = math.radians(angle)
            line_end_x = canvas_x + zoomed_line_length * math.cos(angle_rad)
            line_end_y = canvas_y - zoomed_line_length * math.sin(
                angle_rad
            )  # Inverted y-axis
            orientation_line_id = self.canvas.create_line(
                canvas_x, canvas_y, line_end_x, line_end_y, fill=color, width=2
            )

            # Add minutiae data to the list
            minutiae_data = (
                image_x,
                image_y,
                angle,
                self.current_quality,
                self.current_minutiae_type,
                minutiae_id,
                orientation_line_id,
            )
            self.minutiae.append(minutiae_data)

            # Update the minutiae listbox
            self.update_minutiae_listbox()

            # Print minutiae data to console
            print(
                f"Minutiae added: Type={self.current_minutiae_type}, X={image_x}, Y={image_y}, Angle={angle}, Quality={self.current_quality}"
            )
        else:
            messagebox.showwarning(
                "Out of Bounds", "Cannot add minutiae outside the image."
            )

    def update_type(self):
        self.current_minutiae_type = self.type_var.get()

    def update_quality(self, quality):
        self.current_quality = quality

    def update_minutiae_listbox(self):
        self.minutiae_list.delete(0, tk.END)
        for (
            x,
            y,
            angle,
            quality,
            m_type,
            minutiae_id,
            orientation_line_id,
        ) in self.minutiae:
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
                    for x, y, angle, quality, m_type, _, _ in self.minutiae:
                        f.write(f"{m_type},{x},{y},{angle},{quality}\n")
                messagebox.showinfo("Info", "Minutiae saved successfully!")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save minutiae: {e}")

    def zoom(self, event):
        if not self.image:
            return

        # Zoom factor based on delta
        zoom_factor = 1.1 if event.delta > 0 else 0.9
        self.zoom_level *= zoom_factor

        # Redraw the image with the new zoom level
        self.display_image()
        self.redraw_minutiae()

    def zoom_in(self, event):
        self.zoom_level *= 1.1
        self.display_image()
        self.redraw_minutiae()

    def zoom_out(self, event):
        self.zoom_level *= 0.9
        self.display_image()
        self.redraw_minutiae()

    def display_image(self):
        if not self.image:
            return

        # Calculate the scaled size of the image
        image_width = int(self.image.width * self.zoom_level)
        image_height = int(self.image.height * self.zoom_level)

        # Resize the image
        self.zoomed_image = self.original_image.resize(
            (image_width, image_height), Image.LANCZOS
        )
        self.photo = ImageTk.PhotoImage(self.zoomed_image)

        # Display the image on the canvas
        if hasattr(self, "image_id"):
            self.canvas.itemconfig(self.image_id, image=self.photo)
        else:
            self.image_id = self.canvas.create_image(
                0, 0, anchor=tk.NW, image=self.photo
            )

        # Update scrollregion to include the whole image
        self.canvas.config(
            scrollregion=(
                0,
                0,
                max(image_width, self.canvas_width),
                max(image_height, self.canvas_height),
            )
        )

    def redraw_minutiae(self):
        if not self.image:
            return

        for (
            i,
            (
                x,
                y,
                angle,
                quality,
                m_type,
                minutiae_id,
                orientation_line_id,
            ),
        ) in enumerate(self.minutiae):
            # Calculate new position based on zoom level
            canvas_x = x * self.zoom_level
            canvas_y = y * self.zoom_level

            # Redraw the minutiae point with updated size
            radius = 3
            zoomed_radius = radius * self.zoom_level
            self.canvas.coords(
                minutiae_id,
                canvas_x - zoomed_radius,
                canvas_y - zoomed_radius,
                canvas_x + zoomed_radius,
                canvas_y + zoomed_radius,
            )

            # Redraw the orientation line
            line_length = 15
            zoomed_line_length = line_length * self.zoom_level
            angle_rad = math.radians(angle)
            line_end_x = canvas_x + zoomed_line_length * math.cos(angle_rad)
            line_end_y = canvas_y - zoomed_line_length * math.sin(
                angle_rad
            )  # Inverted y-axis
            self.canvas.coords(
                orientation_line_id, canvas_x, canvas_y, line_end_x, line_end_y
            )

            # Update color if needed
            color = ENDING_COLOR if m_type == "ending" else BIFURCATION_COLOR
            self.canvas.itemconfig(minutiae_id, fill=color)
            self.canvas.itemconfig(orientation_line_id, fill=color)

            # Redraw the active minutiae circle if this is the active minutiae
            if i == self.active_minutiae_index:
                self.draw_active_minutiae_circle(canvas_x, canvas_y)

    def draw_active_minutiae_circle(self, x, y):
        # Remove the previous circle if it exists
        if self.active_minutiae_circle_id:
            self.canvas.delete(self.active_minutiae_circle_id)

        # Draw a yellow circle around the active minutiae
        radius = 5  # Larger radius for the active circle
        zoomed_radius = radius * self.zoom_level
        self.active_minutiae_circle_id = self.canvas.create_oval(
            x - zoomed_radius,
            y - zoomed_radius,
            x + zoomed_radius,
            y + zoomed_radius,
            outline=ACTIVE_COLOR,
            width=2,
        )

    def edit_minutiae(self, event):
        # Get the selected item index
        selection = self.minutiae_list.curselection()
        if not selection:
            return
        index = selection[0]

        # Update active minutiae index and redraw to show the highlight
        self.active_minutiae_index = index
        self.redraw_minutiae()

        # Get the minutiae data
        (
            x,
            y,
            angle,
            quality,
            m_type,
            minutiae_id,
            orientation_line_id,
        ) = self.minutiae[index]

        # Set the current values to the edit widgets
        self.edit_type_var.set(m_type)
        self.edit_x_entry.delete(0, tk.END)
        self.edit_x_entry.insert(0, str(x))
        self.edit_y_entry.delete(0, tk.END)
        self.edit_y_entry.insert(0, str(y))
        self.edit_angle_entry.delete(0, tk.END)
        self.edit_angle_entry.insert(0, str(angle))
        self.edit_quality_var.set(quality)

        # Place the edit frame at the top of the listbox
        self.edit_frame.pack(side=tk.TOP, fill=tk.X)

        # Store the index of the minutiae being edited
        self.editing_index = index

    def update_minutiae_from_entry(self, event):
        self.update_minutiae()

    def update_minutiae(self):
        try:
            # Get updated values from edit widgets
            updated_type = self.edit_type_var.get()
            updated_x = int(self.edit_x_entry.get())
            updated_y = int(self.edit_y_entry.get())
            updated_angle = int(self.edit_angle_entry.get()) % 360
            updated_quality = self.edit_quality_var.get()

            # Get the existing minutiae ID and orientation line ID
            (
                _,
                _,
                _,
                _,
                _,
                minutiae_id,
                orientation_line_id,
            ) = self.minutiae[self.editing_index]

            # Update minutiae data in the list
            self.minutiae[self.editing_index] = (
                updated_x,
                updated_y,
                updated_angle,
                updated_quality,
                updated_type,
                minutiae_id,
                orientation_line_id,
            )

            # Update the minutiae listbox
            self.update_minutiae_listbox()

            # Remove edit widgets
            self.edit_frame.pack_forget()

            # Redraw image to reflect changes
            self.redraw_minutiae()

        except ValueError:
            messagebox.showerror("Error", "Invalid input for X, Y, or Angle.")

    def cancel_edit(self):
        # Remove edit widgets without updating
        self.edit_frame.pack_forget()

    def delete_minutiae(self, event):
        # Get the selected item index
        selection = self.minutiae_list.curselection()
        if not selection:
            return
        index = selection[0]

        # Confirm deletion
        if messagebox.askyesno(
            "Delete Minutiae", "Are you sure you want to delete this minutiae?"
        ):
            # Get the minutiae data
            (
                _,
                _,
                _,
                _,
                _,
                minutiae_id,
                orientation_line_id,
            ) = self.minutiae[index]

            # Remove from canvas
            self.canvas.delete(minutiae_id)
            self.canvas.delete(orientation_line_id)

            # Remove from the list
            del self.minutiae[index]

            # If the deleted minutiae was the active one, remove the highlight
            if index == self.active_minutiae_index:
                self.active_minutiae_index = None
                if self.active_minutiae_circle_id:
                    self.canvas.delete(self.active_minutiae_circle_id)
                    self.active_minutiae_circle_id = None

            # Update listbox and redraw
            self.update_minutiae_listbox()
            self.redraw_minutiae()

    def on_minutiae_select(self, event):
        # Get the selected item index
        selection = self.minutiae_list.curselection()
        if not selection:
            return
        index = selection[0]

        # Update active minutiae index and redraw to show the highlight
        self.active_minutiae_index = index
        self.redraw_minutiae()

    def toggle_editor_mode(self):
        self.editor_mode = self.editor_mode_var.get()
        print(f"Editor mode set to {self.editor_mode}")

    def on_canvas_double_click(self, event):
        if self.editor_mode:
            canvas_x = self.canvas.canvasx(event.x)
            canvas_y = self.canvas.canvasy(event.y)

            # Find the closest minutiae point
            closest_index = self.find_closest_minutiae(canvas_x, canvas_y)

            if closest_index is not None:
                # Open edit box for the selected minutiae
                self.minutiae_list.selection_clear(0, tk.END)
                self.minutiae_list.selection_set(closest_index)
                self.minutiae_list.activate(closest_index)
                self.edit_minutiae(event)  # Pass the event to edit_minutiae

    def on_canvas_click(self, event):
        if self.editor_mode:
            canvas_x = self.canvas.canvasx(event.x)
            canvas_y = self.canvas.canvasy(event.y)

            # Find the closest minutiae point
            closest_index = self.find_closest_minutiae(canvas_x, canvas_y)

            if closest_index is not None:
                x, y, angle, _, _, minutiae_id, orientation_line_id = self.minutiae[
                    closest_index
                ]
                zoomed_x = x * self.zoom_level
                zoomed_y = y * self.zoom_level
                distance = math.hypot(zoomed_x - canvas_x, zoomed_y - canvas_y)

                # Check if click is close enough to the minutiae point or the orientation line
                if distance <= 10:  # 10 pixels threshold
                    self.dragged_minutiae_index = closest_index
                    self.dragged_line_end = None  # Reset line end being dragged
                    self.active_minutiae_index = closest_index
                    self.redraw_minutiae()

                    # --- Activate the item in the listbox ---
                    self.minutiae_list.selection_clear(0, tk.END)
                    self.minutiae_list.selection_set(closest_index)
                    self.minutiae_list.activate(closest_index)

                # Check if click is close to the orientation line start or end
                elif self.is_near_line_end(
                    canvas_x,
                    canvas_y,
                    minutiae_id,
                    orientation_line_id,
                ):
                    self.dragged_minutiae_index = closest_index
                    self.active_minutiae_index = closest_index
                    self.redraw_minutiae()

                    # --- Activate the item in the listbox ---
                    self.minutiae_list.selection_clear(0, tk.END)
                    self.minutiae_list.selection_set(closest_index)
                    self.minutiae_list.activate(closest_index)

                else:
                    self.dragged_minutiae_index = None
                    self.dragged_line_end = None
                    self.active_minutiae_index = None
                    self.redraw_minutiae()

            else:
                # No minutiae or line end found near the click, deselect active minutiae
                self.active_minutiae_index = None
                self.redraw_minutiae()

        else:
            self.mark_minutiae(event)

    def on_canvas_drag(self, event):
        if self.editor_mode and self.dragged_minutiae_index is not None:
            canvas_x = self.canvas.canvasx(event.x)
            canvas_y = self.canvas.canvasy(event.y)
            image_x = int(canvas_x / self.zoom_level)
            image_y = int(canvas_y / self.zoom_level)

            if self.dragged_line_end:
                # Adjust angle based on drag
                (
                    x,
                    y,
                    _,
                    quality,
                    m_type,
                    minutiae_id,
                    orientation_line_id,
                ) = self.minutiae[self.dragged_minutiae_index]
                dx = canvas_x - (x * self.zoom_level)
                dy = (y * self.zoom_level) - canvas_y  # Inverted y-axis
                new_angle = math.degrees(math.atan2(dy, dx))

                # Correct the angle to be in the range 0-360
                if new_angle < 0:
                    new_angle += 360
                
                new_angle = round(new_angle) % 360

                # Update minutiae data with new angle
                self.minutiae[self.dragged_minutiae_index] = (
                    x,
                    y,
                    new_angle,
                    quality,
                    m_type,
                    minutiae_id,
                    orientation_line_id,
                )
                self.update_minutiae_listbox()
                self.redraw_minutiae()

            else:
                # Check if the new position is within the image boundaries
                if 0 <= image_x < self.image.width and 0 <= image_y < self.image.height:
                    # Drag minutiae point
                    (
                        _,
                        _,
                        angle,
                        quality,
                        m_type,
                        minutiae_id,
                        orientation_line_id,
                    ) = self.minutiae[self.dragged_minutiae_index]
                    self.minutiae[self.dragged_minutiae_index] = (
                        image_x,
                        image_y,
                        angle,
                        quality,
                        m_type,
                        minutiae_id,
                        orientation_line_id,
                    )
                    self.update_minutiae_listbox()
                    self.redraw_minutiae()
                else:
                    messagebox.showwarning(
                        "Out of Bounds", "Cannot move minutiae outside the image."
                    )

    def on_canvas_release(self, event):
        if self.editor_mode:
            self.dragged_minutiae_index = None
            self.dragged_line_end = None

    def find_closest_minutiae(self, canvas_x, canvas_y):
        min_distance = float("inf")
        closest_index = None
        for i, (x, y, _, _, _, _, _) in enumerate(self.minutiae):
            zoomed_x = x * self.zoom_level
            zoomed_y = y * self.zoom_level
            distance = math.hypot(zoomed_x - canvas_x, zoomed_y - canvas_y)
            if distance < min_distance:
                min_distance = distance
                closest_index = i
        return closest_index

    def is_near_line_end(
        self,
        canvas_x,
        canvas_y,
        minutiae_id,
        orientation_line_id,
    ):
        # Get coordinates of the orientation line
        x1, y1, x2, y2 = self.canvas.coords(orientation_line_id)

        # Calculate distance to start and end points of the line
        dist_start = math.hypot(x1 - canvas_x, y1 - canvas_y)
        dist_end = math.hypot(x2 - canvas_x, y2 - canvas_y)

        # Check if within a threshold distance to either end
        threshold = 10
        if dist_start <= threshold:
            self.dragged_line_end = "start"
            return True
        elif dist_end <= threshold:
            self.dragged_line_end = "end"
            return True
        else:
            return False
