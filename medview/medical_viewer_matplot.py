import argparse
import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.image import AxesImage
from matplotlib.widgets import Slider
from matplotlib.widgets import Button
from matplotlib.backend_bases import MouseEvent
from medview.med_utils import CT_WINDOW_TYPE, CT_WINDOW_LEVELS, AXIAL, CORONAL, SAGITTAL
from medview.medical_image_reader import MedicalImageReader
import numpy as np
import os



class MedicalViewerMatplot:
    """
    Medical DICOM Image Viewer with Multi-Planar Reconstruction (MPR)

    This class creates an interactive viewer for medical images (like CT scans or MRIs)
    that allows you to see the same 3D volume from three different perspectives simultaneously.

    MEDICAL IMAGING BASICS:
    - Medical scans create 3D volumes made up of many 2D slices (like pages in a book)
    - We can view these volumes from three standard medical perspectives:
        * Axial (horizontal slices, like looking down at someone lying on their back)
        * Sagittal (side view slices, like looking at someone's profile)
        * Coronal (front/back view slices, like looking at someone face-to-face)

    KEY FEATURES:
    - Proper anatomical orientation following medical conventions
    - Scroll through slices in any view
    - Click on any view to see the corresponding location in other views
    - Interactive crosshairs that synchronize between all three views

    COORDINATE SYSTEMS:
    - Medical images have specific orientation conventions (which way is "up", "left", etc.)
    - The code handles transformations to display images correctly according to medical standards
    - Crosshairs help you see exactly where you are in 3D space across all views

    SUPPORTED FILE FORMATS:
    - DICOM series (folder containing multiple .dcm files)
    - MetaImage (.mha) single file format
    - NIfTI (.nii/.nii.gz) single file format
    """

    def __init__(self, image_reader: MedicalImageReader):
        """
        Initialize the medical viewer.

        Args:
            image_reader (ImageReader): Configured image reader with loaded medical imaging data
        """
        self.image_reader = image_reader

        # Get dimensions of the 3D volume
        self.depth, self.height, self.width = self.image_reader.image_numpy.shape

        # Define information for each view including axis labels and titles
        self.slice_info = {
            AXIAL: {
                "axis_labels": ("Right <- -> Left", "Posterior <- -> Anterior"),
                "title": "Axial View (Transverse)",
            },
            CORONAL: {
                "axis_labels": ("Right <- -> Left", "Inferior <- -> Superior"),
                "title": "Coronal View (Front-Back)",
            },
            SAGITTAL: {
                "axis_labels": ("Anterior <- -> Posterior", "Inferior <- -> Superior"),
                "title": "Sagittal View (Left-Right)",
            },
        }

        # Initialize tracking variables
        self.current_slices = {
            view: 0 for view in self.image_reader.views
        }  # Current slice in each view
        self.crosshairs = {
            view: {"h": None, "v": None} for view in self.image_reader.views
        }  # Crosshair lines
        self.clicked_coords = {
            view: None for view in self.image_reader.views
        }  # Last clicked coordinates
        self.current_3d_coords = None  # x, y, z                                           # Current 3D position

        # Store references to sliders and axes for synchronization
        self.sliders = []
        self.axes = []
        if self.image_reader.modality == "CT":
            self.CT_window_type = CT_WINDOW_TYPE.GENERAL
            self.CT_window = CT_WINDOW_LEVELS[self.CT_window_type]
            self.CT_window_level = (self.CT_window[1] + self.CT_window[0]) / 2
            self.CT_window_width = self.CT_window[1] - self.CT_window[0]
        else:
            self.CT_window_type = None
            self.CT_window = None

    def create_view(self, ax: Axes, slice_idx: int, view: str) -> AxesImage:
        """
        Create or update a single view of the medical image.

        WHAT THIS DOES:
        1. Extract the correct 2D slice from the 3D volume
        2. Apply proper medical orientation
        3. Display the slice with appropriate labels and formatting
        4. Set up coordinate display functionality
        5. Redraw crosshairs if they exist

        Args:
            ax (matplotlib.axes.Axes): The matplotlib axis to draw on
            slice_idx (int): Which slice to display
            view (str): Which anatomical view this is (axial / coronal / saggital)

        Returns:
            matplotlib.image.AxesImage: The displayed image object
        """
        # Store current slice index for this view
        self.current_slices[view] = slice_idx

        # Get properly oriented slice data and aspect ratio
        img_data, aspect = self.image_reader.extract_slice_with_orientation(
            view, slice_idx
        )

        if self.image_reader.modality == "CT":
            min_value, max_value = self.CT_window
            img_data = np.clip(img_data, min_value, max_value)
            img_data = (img_data - min_value) / (max_value - min_value)

        # Clear the axis and create new image display
        ax.clear()

        # Create the grayscale image display
        im = ax.imshow(img_data, cmap="gray", aspect=aspect, origin="lower")

        # Set up the display appearance
        ax.set_title(self.slice_info[view]["title"], color="White", fontsize=12)
        ax.set_xlabel(self.slice_info[view]["axis_labels"][0], color="white")
        ax.set_ylabel(self.slice_info[view]["axis_labels"][1], color="white")
        ax.tick_params(axis="both", colors="white")
        ax.set_facecolor("black")

        # Redraw crosshairs if we have current 3D coordinates
        if self.current_3d_coords is not None:
            self.draw_crosshair_for_view(ax, view, self.current_3d_coords)

        # Set up coordinate and value display when hovering
        def format_coord(x, y):
            """
            Function called when mouse hovers over the image.
            Shows display coordinates, original 3D coordinates, and pixel value.
            """
            # Convert float coordinates to integers
            display_x, display_y = int(x), int(y)

            # Convert display coordinates back to original 3D coordinates
            original_coords = self.map_display_to_original_coords(
                view, display_x, display_y, slice_idx
            )

            # Get the pixel value at this location
            try:
                value = img_data[display_y, display_x]
                if self.image_reader.modality == "CT":
                    # Convert normalized value back to HU
                    value = value * (self.CT_window_width) + (
                        self.CT_window_level - self.CT_window_width / 2
                    )
                    value = f"{value:.1f} HU"
                else:
                    value = f"{value:.1f}"
            except IndexError:
                value = None  # Outside image bounds

            # Format the information string
            return f"Display: ({display_x}, {display_y}) Original: ({original_coords[0]}, {original_coords[1]}, {original_coords[2]}) Value: {value}"

        # Attach the coordinate formatter to this axis
        ax.format_coord = format_coord
        return im

    def map_display_to_original_coords(self, view, display_x, display_y, slice_idx):

        transform = self.image_reader.view_transforms[view]
        dim_idx = self.image_reader.view_indices[view]

        # Start with display coordinates
        x, y = display_x, display_y

        # Step 1: Determine which original axes correspond to current x,y after all transforms
        # We need to work backwards through the transformations

        # First, determine the base axes for this view (before any transforms)
        if dim_idx == 2:  # axial view (slicing through Z)
            base_x_axis, base_y_axis = 0, 1  # X, Y axes
            base_max_x = self.image_reader.image_numpy.shape[2] - 1  # width
            base_max_y = self.image_reader.image_numpy.shape[1] - 1  # height
        elif dim_idx == 1:  # coronal view (slicing through Y)
            base_x_axis, base_y_axis = 0, 2  # X, Z axes
            base_max_x = self.image_reader.image_numpy.shape[2] - 1  # width
            base_max_y = self.image_reader.image_numpy.shape[0] - 1  # depth
        else:  # sagittal view (slicing through X)
            base_x_axis, base_y_axis = 1, 2  # Y, Z axes
            base_max_x = self.image_reader.image_numpy.shape[1] - 1  # height
            base_max_y = self.image_reader.image_numpy.shape[0] - 1  # depth

        # Determine current axis assignments after transpose
        if transform["transpose"]:
            # After transpose: display_x corresponds to base_y_axis, display_y to base_x_axis
            # current_x_axis, current_y_axis = base_y_axis, base_x_axis
            current_max_x, current_max_y = base_max_y, base_max_x
        else:
            # No transpose: display_x corresponds to base_x_axis, display_y to base_y_axis
            # current_x_axis, current_y_axis = base_x_axis, base_y_axis
            current_max_x, current_max_y = base_max_x, base_max_y

        # Step 2: Undo flips using the correct axis assignments
        if transform["flip_x"]:
            x = current_max_x - x
        if transform["flip_y"]:
            y = current_max_y - y

        # Step 3: Undo transpose if it was applied
        if transform["transpose"]:
            x, y = y, x  # Swap coordinates back

        # Step 4: Map 2D display coordinates back to 3D coordinates
        original_coords = [0, 0, 0]  # Will hold [x, y, z] in original space

        if dim_idx == 2:  # axial view (slicing through Z)
            original_coords[0] = x  # Display X -> original X
            original_coords[1] = y  # Display Y -> original Y
            original_coords[2] = slice_idx  # Slice number -> original Z
        elif dim_idx == 1:  # coronal view (slicing through Y)
            original_coords[0] = x  # Display X -> original X
            original_coords[1] = slice_idx  # Slice number -> original Y
            original_coords[2] = y  # Display Y -> original Z
        else:  # sagittal view (slicing through X)
            original_coords[0] = slice_idx  # Slice number -> original X
            original_coords[1] = x  # Display X -> original Y
            original_coords[2] = y  # Display Y -> original Z

        return tuple(original_coords)

    def coords_3d_to_display(
        self, view: str, coords_3d: tuple[int, int, int]
    ) -> tuple[int, int]:
        """
        Convert 3D coordinates to 2D display coordinates for a specific view.

        Args:
            view (str): Which anatomical view to convert for
            coords_3d (tuple): (x, y, z) coordinates in original 3D space

        Returns:
            tuple: (display_x, display_y) coordinates for this view
        """
        x, y, z = coords_3d

        # Get view parameters
        dim_idx = self.image_reader.view_indices[view]
        transform = self.image_reader.view_transforms[view]

        # Step 1: Map 3D coordinates to the 2D plane of this view
        if dim_idx == 2:
            display_x, display_y = x, y
            max_x = self.image_reader.image_numpy.shape[2] - 1  # width
            max_y = self.image_reader.image_numpy.shape[1] - 1  # height
        elif dim_idx == 1:
            display_x, display_y = x, z
            max_x = self.image_reader.image_numpy.shape[2] - 1  # width
            max_y = self.image_reader.image_numpy.shape[0] - 1  # depth
        else:
            display_x, display_y = y, z
            max_x = self.image_reader.image_numpy.shape[1] - 1  # height
            max_y = self.image_reader.image_numpy.shape[0] - 1  # depth

        # Step 2: Apply transpose if needed (swap X and Y)
        if transform["transpose"]:
            display_x, display_y = display_y, display_x
            max_x, max_y = max_y, max_x

        # Step 3: Apply flips
        if transform["flip_x"]:
            display_x = max_x - display_x

        if transform["flip_y"]:
            display_y = max_y - display_y
        # print(f"View: {view}, Display: {display_x}, {display_y}, max: {max_x}, {max_y}")
        return display_x, display_y

    def get_slice_index_for_view(
        self, view: str, coords_3d: tuple[int, int, int]
    ) -> int:
        """
        Determine which slice to show in a view for given 3D coordinates.

        When you click on one view, we want to update the other views to show
        slices that pass through the same 3D point. Each view slices through
        a different axis of the 3D volume.

        EXAMPLES:
        - Axial view slices through Z-axis -> use Z coordinate as slice number
        - Coronal view slices through Y-axis -> use Y coordinate as slice number
        - Sagittal view slices through X-axis -> use X coordinate as slice number

        Args:
            view (str): Which anatomical view
            coords_3d (tuple): (x, y, z) coordinates in original 3D space

        Returns:
            int: Slice index to display in this view
        """
        x, y, z = coords_3d
        dim_idx = self.image_reader.view_indices[view]

        if dim_idx == 2:  # axial view - slicing through Z-axis
            return z
        elif dim_idx == 1:  # coronal view - slicing through Y-axis
            return y
        else:  # sagittal view - slicing through X-axis
            return x

    def draw_crosshair_for_view(
        self, ax: Axes, view: str, coords_3d: tuple[int, int, int]
    ):
        """
        Draw crosshair lines on a specific view at the given 3D coordinates.

        CROSSHAIRS EXPLAINED:
        Crosshairs are horizontal and vertical lines that intersect at a point
        of interest. In medical imaging, they help you see exactly where you
        are in 3D space by showing the same location across all views.

        1. Convert 3D coordinates to display coordinates for this view
        2. Remove any existing crosshairs
        3. Draw new horizontal and vertical lines
        4. Store references to the lines for future removal

        Args:
            ax (matplotlib.axes.Axes): The axis to draw crosshairs on
            view (str): Which anatomical view this is (axial / coronal / saggital)
            coords_3d (tuple): (x, y, z) coordinates in original 3D space
        """
        # Convert 3D coordinates to 2D display coordinates for this view
        display_coords = self.coords_3d_to_display(view, coords_3d)
        if display_coords is None:
            return  # Cannot display crosshairs for this coordinate

        display_x, display_y = display_coords

        # Remove existing crosshairs if any
        if self.crosshairs[view]["h"] is not None:
            try:
                self.crosshairs[view]["h"].remove()  # Remove horizontal line
                self.crosshairs[view]["v"].remove()  # Remove vertical line
            except:
                pass  # Lines might already be removed

        # Create new crosshair lines
        h_line = ax.axhline(
            y=display_y, color="yellow", linestyle="dashed", alpha=0.7, linewidth=1
        )
        v_line = ax.axvline(
            x=display_x, color="yellow", linestyle="dashed", alpha=0.7, linewidth=1
        )

        # Store references to the lines so we can remove them later
        self.crosshairs[view]["h"] = h_line
        self.crosshairs[view]["v"] = v_line

    def synchronize_views(
        self, clicked_view: str, coords_3d: tuple[int, int, int]
    ) -> None:
        """
        Update all views to show the same 3D location.

        When you click on one view, we want all other views to update to show
        slices that pass through the same 3D point. This lets you explore
        the same anatomical location from multiple perspectives.

        1. Store the 3D coordinates
        2. For each view, calculate which slice should be displayed
        3. Update the slider positions (which triggers view updates)
        4. Ensure slice indices are within valid bounds

        Args:
            clicked_view (str): The view that was clicked on
            coords_3d (tuple): (x, y, z) coordinates to synchronize to
        """
        self.current_3d_coords = coords_3d

        # Update slider positions for all views (including the clicked one)
        for i, view in enumerate(self.image_reader.views):
            if view != clicked_view:  # Don't update the view that was clicked
                # Calculate which slice should be displayed for these coordinates
                slice_idx = self.get_slice_index_for_view(view, coords_3d)

                # Make sure slice index is within valid range
                dim_idx = self.image_reader.view_indices[view]
                max_slices = self.image_reader.size[dim_idx] - 1
                slice_idx = max(0, min(slice_idx, max_slices))

                # Update the slider (this automatically triggers the update callback)
                self.sliders[i].set_val(slice_idx)

    def on_click(self, event: MouseEvent, view: str, ax: Axes) -> None:
        """
        Handle mouse click events on any view.

        When you click on an image:
        1. We get the (x, y) coordinates where you clicked
        2. We convert these to 3D coordinates in the original image
        3. We synchronize all views to show this same 3D location
        4. We draw crosshairs on all views at this location

        This allows interactive exploration of the 3D volume.

        Args:
            event: Matplotlib mouse event object
            view (str): Which view was clicked on
            ax (matplotlib.axes.Axes): The axis that was clicked on
        """
        # Only process clicks that are actually on the image
        if event.inaxes != ax:
            return

        # Get clicked coordinates (convert to integers)
        x, y = int(event.xdata), int(event.ydata)
        self.clicked_coords[view] = (x, y)

        # Get current slice index for this view
        current_slice = self.current_slices[view]

        # Convert display coordinates back to 3D coordinates
        coords_3d = self.map_display_to_original_coords(
            view, x, y, current_slice
        )

        print(f"Clicked on {view} view at display ({x}, {y}), 3D coords: {coords_3d}")

        # Synchronize all views to show this 3D location
        self.synchronize_views(view, coords_3d)

    def on_scroll(self, event: MouseEvent, view: str, ax: Axes) -> None:
        """
        Handle mouse scroll events to navigate through slices.

        Scrolling the mouse wheel over any view allows you to quickly
        navigate through slices in that view. This is faster than using
        the slider for quick exploration.

        - Scroll up: Move to next slice (higher slice number)
        - Scroll down: Move to previous slice (lower slice number)

        Args:
            event: Matplotlib scroll event object
            view (str): Which view was scrolled on
            ax (matplotlib.axes.Axes): The axis that was scrolled on
        """
        # Only process scrolls that are actually over the image
        if event.inaxes != ax:
            return

        # Find which slider corresponds to this view
        slider_idx = self.image_reader.views.index(view)
        slider = self.sliders[slider_idx]

        # Get current slider value and define step size
        current_val = slider.val
        step = 1  # Move one slice at a time

        # Update value based on scroll direction
        if event.button == "up":
            new_val = min(current_val + step, slider.valmax)
        else:  # event.button == 'down'
            new_val = max(current_val - step, slider.valmin)

        # Update slider value (this triggers the update function automatically)
        slider.set_val(new_val)

        # Update current_3d_coords based on the new slice value
        if self.current_3d_coords is not None:
            x, y, z = self.current_3d_coords
            dim_idx = self.image_reader.view_indices[view]

            # Update the coordinate corresponding to the slice dimension
            if dim_idx == 2:  # axial view - update Z
                self.current_3d_coords = (x, y, new_val)
            elif dim_idx == 1:  # coronal view - update Y
                self.current_3d_coords = (x, new_val, z)
            else:  # sagittal view - update X
                self.current_3d_coords = (new_val, y, z)

            # Use synchronize_views to update all views
            self.synchronize_views(view, self.current_3d_coords)

        # Refresh the display
        ax.figure.canvas.draw_idle()

    def view_dicom_series(self) -> None:
        """
        Create and display the main interactive viewer window.

        This function creates the complete user interface including:
        - Three side-by-side image displays (axial, sagittal, coronal)
        - Vertical sliders for each view to navigate through slices
        - Mouse interaction handlers (click, scroll)
        - Initial crosshairs at the center of the volume
        - CT window type buttons (if modality is CT)

        LAYOUT:
        [Axial View] [Slider] [Sagittal View] [Slider] [Coronal View] [Slider]
        [CT Window Buttons] (if CT modality)
        """
        # Create figure with three subplots for the three medical views
        fig, axes = plt.subplots(1, 3, figsize=(15, 5))
        fig.patch.set_facecolor("#353535")  # Dark background
        plt.subplots_adjust(left=0.1, bottom=0.15, right=0.9, top=0.9, wspace=0.3)
        fig.canvas.manager.set_window_title("Medical Image Viewer (MPR)")

        # Store axes reference for later use
        self.axes = axes

        # Initialize storage for sliders
        slider_axes = []
        sliders = []

        # Print debugging information about the image
        print("=== IMAGE INFORMATION ===")
        print(
            "Array shape (depth, height, width):", self.image_reader.image_numpy.shape
        )
        print("Pixel spacing (x, y, z):", self.image_reader.spacing)
        print(
            "View indices (which axis for each view):", self.image_reader.view_indices
        )
        print(
            "View transforms (orientation corrections):",
            self.image_reader.view_transforms,
        )
        print("========================")

        # Calculate positions for each subplot (needed for slider placement)
        subplot_positions = []
        for ax in axes:
            pos = ax.get_position()  # Get position of each subplot
            subplot_positions.append(pos)

        # Create a slider for each view
        for i, view in enumerate(self.image_reader.views):
            # Get position of current subplot
            pos = subplot_positions[i]

            # Create vertical slider positioned to the right of the subplot
            slider_ax = plt.axes(
                [
                    pos.x1 + 0.01,  # Just to the right of the subplot
                    pos.y0,  # Aligned with bottom of subplot
                    0.02,  # Slider width (thin)
                    pos.height,  # Same height as subplot
                ],
                facecolor="White",
            )

            # Determine the valid range for this view's slider
            dim_idx = self.image_reader.view_indices[view]
            max_slices = self.image_reader.size[dim_idx] - 1

            # Start at the middle slice for better initial view
            middle_slice = max_slices // 2

            print(
                f"{view} view: using dimension {dim_idx}, max slices: {max_slices}, starting at slice: {middle_slice}"
            )

            # Create the slider widget
            slider = Slider(
                slider_ax,
                f"{view.capitalize()}\nSlice",  # Label
                0,  # Minimum value
                max_slices,  # Maximum value
                valinit=middle_slice,  # Initial value
                valfmt="%0.0f",  # Format (integer)
                orientation="vertical",  # Vertical orientation
                color="gray",  # Track color (background)
                facecolor="gray",  # Handle color
                alpha=0.8,
            )
            slider.label.set_color("white")
            slider.valtext.set_color("white")

            slider_axes.append(slider_ax)
            sliders.append(slider)

            # Set background color for each subplot
            axes[i].set_facecolor("white")

            # Connect mouse click events to each view
            axes[i].figure.canvas.mpl_connect(
                "button_press_event",
                lambda event, v=view, a=axes[i]: self.on_click(event, v, a),
            )

            # Connect mouse scroll events to each view
            axes[i].figure.canvas.mpl_connect(
                "scroll_event",
                lambda event, v=view, a=axes[i]: self.on_scroll(event, v, a),
            )

        # Store sliders reference for synchronization
        self.sliders = sliders

        def update(val):
            """
            Callback function called whenever any slider changes.
            Updates all views to show their current slice numbers.

            Args:
                val: Slider value (automatically provided by matplotlib)
            """
            # Update all views with their current slice numbers
            for i, view in enumerate(self.image_reader.views):
                slice_num = int(sliders[i].val)
                self.create_view(axes[i], slice_num, view)

                # If we have current 3D coordinates, redraw crosshairs
                if self.current_3d_coords is not None:
                    self.draw_crosshair_for_view(axes[i], view, self.current_3d_coords)

            # Refresh the display
            fig.canvas.draw_idle()

        # Connect all sliders to the update function
        for slider in sliders:
            slider.on_changed(update)

        # Initialize all views with their starting slices
        update(0)

        # Set initial crosshairs at the center of the volume
        # This gives users a reference point to start exploring
        center_x = self.width // 2
        center_y = self.height // 2
        center_z = self.depth // 2
        self.current_3d_coords = (center_x, center_y, center_z)
        print(
            f"Setting initial crosshairs at center: ({center_x}, {center_y}, {center_z})"
        )

        # Draw initial crosshairs on all views
        for i, view in enumerate(self.image_reader.views):
            self.draw_crosshair_for_view(axes[i], view, self.current_3d_coords)

        # Add CT window type buttons if modality is CT
        if self.image_reader.modality == "CT":
            # Calculate total width needed for all buttons
            num_buttons = len(CT_WINDOW_TYPE)
            button_width = 0.12
            spacing = 0.015
            total_width = num_buttons * button_width + (num_buttons - 1) * spacing

            # Center the button group
            start_x = (1.0 - total_width) / 2

            # Create a new axes for the buttons
            button_ax = plt.axes([0.1, 0.02, 0.8, 0.05])  # Position at bottom of figure
            button_ax.set_axis_off()  # Hide the axes

            # Create buttons for each window type
            buttons = []
            for i, window_type in enumerate(CT_WINDOW_TYPE):
                x_pos = start_x + i * (button_width + spacing)

                button = Button(
                    plt.axes([x_pos, 0.01, button_width, 0.06]),
                    window_type.value.capitalize() + " Window",
                    color="lightgray",
                    hovercolor="white",
                )

                # Style the button text
                button.label.set_fontsize(10)
                button.label.set_fontweight("bold")
                button.label.set_color("black")

                button.on_clicked(
                    lambda event, wt=window_type: self._on_window_type_click(wt)
                )
                buttons.append(button)

        # Display the interactive viewer
        plt.show()

    def _on_window_type_click(self, window_type: CT_WINDOW_TYPE) -> None:
        """
        Handle CT window type button clicks.

        Args:
            window_type (CT_WINDOW_TYPE): The selected window type
        """
        # Update window parameters
        self.CT_window_type = window_type
        self.CT_window = CT_WINDOW_LEVELS[window_type]
        self.CT_window_level = (self.CT_window[1] + self.CT_window[0]) / 2
        self.CT_window_width = self.CT_window[1] - self.CT_window[0]

        # Update all views
        for i, view in enumerate(self.image_reader.views):
            slice_num = int(self.sliders[i].val)
            self.create_view(self.axes[i], slice_num, view)

            # Redraw crosshairs if they exist
            if self.current_3d_coords is not None:
                self.draw_crosshair_for_view(self.axes[i], view, self.current_3d_coords)

        # Refresh the display
        plt.draw()


def main():
    parser = argparse.ArgumentParser(description="Medical DICOM/NIfTI/MHA Image Viewer with MPR")
    parser.add_argument("image_path", type=str, help="Path to the medical image file (DICOM folder, .nii, .nii.gz, or .mha)")
    parser.add_argument("--modality", type=str, default=None, help="Modality type (e.g., CT, MRI). Optional. If not provided, will be inferred if possible.")
    args = parser.parse_args()

    image_path = args.image_path
    modality = args.modality
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"File or directory not found: {image_path}")

    if modality is not None:
        image_reader = MedicalImageReader(image_path, modality=modality)
    else:
        image_reader = MedicalImageReader(image_path)

    print("Creating medical viewer...")

    # Create the interactive viewer
    medical_viewer = MedicalViewerMatplot(image_reader)

    # Start the interactive viewer
    medical_viewer.view_dicom_series()


if __name__ == "__main__":
    main()
