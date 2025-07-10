import matplotlib.pyplot as plt
import numpy as np
import os
import SimpleITK as sitk
from SimpleITK.SimpleITK import Image
from typing import Tuple

from medview.med_utils import X, Y, Z, AXIAL, CORONAL, SAGITTAL, MODALITY

class MedicalImageReader:
    """
    Handles reading and processing medical images in various formats.
    
    - Reads medical images in multiple formats (DICOM, MetaImage, NIfTI)
    - Extracts 3D image data and metadata (size, spacing, orientation)

    - Calculates how to properly display images in each viewing plane
    - Handles coordinate transformations between different views
    
    SUPPORTED FORMATS:
    - DICOM = Digital Imaging and Communications in Medicine (folder of .dcm files)
    - MetaImage = Single file format (.mha) with header and raw data
    - NIfTI = Neuroimaging Informatics Technology Initiative (.nii/.nii.gz)
    """
    
    def __init__(self, image_path: str, modality:str = MODALITY.CT.value):
        """
        Initialize the image reader with a medical image file or folder.
        
        Args:
            image_path (str): Path to medical image file or folder
            modality: CT / MR; needed if not dicom
        """
        try:
            # Determine file format and read the image
            file_ext = os.path.splitext(image_path)[1].lower()
            self.is_dicom = os.path.isdir(image_path) or file_ext == ".dcm"
            if self.is_dicom:
                # If it's a directory, assume it's a DICOM series
                self.image, self.modality = self.read_dicom(image_path)
            elif file_ext in ['.mha', '.nii', '.gz']:
                self.image = sitk.ReadImage(image_path)
                self.modality = modality # need input from user, missing in file info
            else:
                raise ValueError(f"Unsupported file format: {file_ext}. Supported formats are: DICOM folders, .mha, .nii/.nii.gz")

            print(f"Modality: {self.modality}")

            # Extract metadata - information about the image dimensions, spacing, and orientation
            self.size, self.spacing, self.origin, self.direction = self.get_image_metadata(self.image)
            # Convert to numpy array for easier manipulation (sz, sy, sx order)
            # sz = number of slices in z direction, sy = height, sx = width
            self.image_numpy = self.get_image_numpy(self.image) 
            
            # Calculate viewing parameters for each anatomical plane
            self.view_indices, self.view_signs, self.view_transforms = self.get_view_indices()
            
            # Define the three standard medical views in order
            self.views = [AXIAL, SAGITTAL, CORONAL]

            print(f"Image {image_path} read")
        except Exception as e:
            print(f"Error initializing MedImageReader: {e}")
            raise e
        
    @staticmethod
    def read_dicom(dicom_path: str) -> Image:
        """
        Read a DICOM series from a folder.
        
        DICOM SERIES EXPLAINED:
        - Medical scans are usually saved as multiple files (one per slice)
        - We need to read all files and combine them into one 3D volume
        - SimpleITK handles this automatically by reading the metadata
        
        Args:
            dicom_path (str): Path to folder containing DICOM files
            
        Returns:
            SimpleITK.Image: 3D medical image object
        """
        reader = sitk.ImageFileReader()
            
        if os.path.isdir(dicom_path):
                # For DICOM series, read first file
            series_reader = sitk.ImageSeriesReader()
            dicom_names = series_reader.GetGDCMSeriesFileNames(dicom_path)
            if dicom_names:
                reader.SetFileName(dicom_names[0])
                reader.ReadImageInformation()
                modality = reader.GetMetaData("0008|0060")

            series_reader.SetFileNames(dicom_names)
            return series_reader.Execute(), modality
        else:
            reader.SetFileName(dicom_path)
            reader.ReadImageInformation()
            modality = reader.GetMetaData("0008|0060")
            return reader.Execute(), modality

    def _get_image_modality(self) -> str:
        keys = ["modality", "Modality", "0008|0060"]
        for k in keys:
            if k in self.image.GetMetaDataKeys():
                print(f"Found modality in {k}")
                return self.image.GetMetaData(k)
        return None

    @staticmethod
    def get_image_metadata(image: Image) -> Tuple[tuple, tuple, tuple, tuple]:
        """
        Extract important information about the medical image.
        
        METADATA EXPLAINED:
        - Size: How many pixels/voxels in each direction (width, height, depth)
        - Spacing: Physical distance between pixels (in millimeters)
        - Origin: Where in physical space the image starts
        - Direction: How the image is oriented in 3D space
        
        This information is crucial for displaying images correctly and
        making measurements in real physical units.
        
        Args:
            image (SimpleITK.Image): Medical image object
            
        Returns:
            tuple: (size, spacing, origin, direction) - all in (x, y, z) order
        """
        size = image.GetSize()       # Number of pixels in each direction (sx, sy, sz)
        spacing = image.GetSpacing() # Physical spacing between pixels (sx, sy, sz) 
        origin = image.GetOrigin()   # Physical location of first pixel (sx, sy, sz)
        direction = image.GetDirection() # Orientation matrix (9 values for 3x3 matrix)
        return size, spacing, origin, direction
    
    @staticmethod
    def get_image_numpy(image: Image) -> np.ndarray:
        """
        Convert SimpleITK image to numpy array for easier processing.
        
        COORDINATE ORDER IMPORTANT:
        - SimpleITK uses (z, y, x) order
        - Numpy arrays from SimpleITK are in (z, y, x) order
        - This means: [depth, height, width] or [slice_number, row, column]
        
        Args:
            image (SimpleITK.Image): Medical image object
            
        Returns:
            numpy.ndarray: 3D array with shape (depth, height, width)
        """
        image_np = sitk.GetArrayFromImage(image) # Results in (sz, sy, sx) order
        return image_np

    def get_view_indices(self) -> Tuple[dict, dict, dict]:
        """
        Determine how to map each anatomical view to the image axes.
        
        THE CHALLENGE:
        Medical images can be acquired in any orientation. The scanner might be
        tilted, or the patient positioned differently. We need to figure out
        which axis of our data corresponds to which anatomical direction.
        
        SOLUTION:
        We use the direction matrix (which tells us how the image is oriented)
        to determine which axis best represents each anatomical plane.
        
        Returns:
            tuple: (view_indices, view_signs, view_transforms)
            - view_indices: Which axis (0, 1, or 2) corresponds to each view
            - view_signs: Whether we need to flip the direction (+1 or -1)
            - view_transforms: Detailed transformation info for proper display
        """
        # The direction matrix is 9 numbers that describe orientation
        # We reshape it into a 3x3 matrix for easier manipulation
        direction = np.array(self.direction).reshape(3, 3)
        
        # Define which 3D direction corresponds to each anatomical view
        anatomical_directions = {
            # view : axis
            AXIAL: Z,    # Axial slices are perpendicular to Z-axis (up-down)
            CORONAL: Y,  # Coronal slices are perpendicular to Y-axis (front-back)
            SAGITTAL: X  # Sagittal slices are perpendicular to X-axis (left-right)
        }

        #view_indices stores which index is each view's axis at for this numpy array 
        # EG: {AXIAL: 1, CORONAL: 0, SAGITTAL: 2}
        view_indices = {}    # Which axis to use for each view
        
        view_signs = {}      # Whether to flip the direction
        view_transforms = {} # Detailed transformation parameters
        
        for view, axis in anatomical_directions.items():
            # Calculate how well each axis aligns with the desired anatomical direction
            # Dot product measures alignment: 1 = perfectly aligned, 0 = perpendicular
            dot_products = [np.dot(direction[:, i], axis) for i in range(3)]
            
            # Find the axis that best aligns with this anatomical direction
            primary_axis = np.argmax([abs(dp) for dp in dot_products])
            view_indices[view] = primary_axis
            
            # Determine if we need to flip the direction
            view_signs[view] = np.sign(dot_products[primary_axis])
            
            # Calculate detailed transformation needed for proper display
            view_transforms[view] = self._calculate_view_transform(direction, view, primary_axis)
        
        return view_indices, view_signs, view_transforms

    def _get_target_orientations(self, view: str) -> Tuple[np.ndarray, np.ndarray]:
        """
        Returns the target orientation vectors for the specified anatomical view.

        args: 
            view : str
                One of 'axial', 'coronal', or 'sagittal'. This determines the plane 
                of visualization and thus the axes along which to orient the image.

        returns: 

            Tuple[np.ndarray, np.ndarray]
                A tuple of two numpy arrays representing the in-plane orientation 
                directions for the view

        The direction of the vectors is chosen to match standard radiological conventions:

        """
        if view == AXIAL:
            # For axial view: X=left-right (+left), Y=anterior-posterior (+posterior)
            return X, -Y  # Left direction, Posterior direction (negative Y)
        elif view == CORONAL:
            # For coronal view: X=left-right (+left), Y=superior-inferior (+superior)
            return X, Z   # Left direction, Superior direction
        else:  # SAGITTAL
            # For sagittal view: X=anterior-posterior (+anterior), Y=superior-inferior (+superior)
            return Y, Z   # Anterior direction, Superior direction

    def _calculate_view_transform(self, direction:np.ndarray , view: str,
                                   primary_axis: int) -> dict: 
        """
        Calculate the transformation required to correctly orient a given anatomical view.

        Args:
            direction (np.ndarray): A 3x3 direction cosine matrix representing the orientation 
                of the image in physical space.
            view (str): The anatomical view ('axial', 'coronal', or 'sagittal').
            primary_axis (int): The axis index (0, 1, or 2) along which slicing occurs for the view.

        Returns:
            dict: A dictionary containing the following keys:
                - 'transpose' (bool): Whether to transpose the image (swap X and Y).
                - 'flip_x' (bool): Whether to flip the image horizontally.
                - 'flip_y' (bool): Whether to flip the image vertically.
                - 'x_axis' (int): The index of the axis used as display X.
                - 'y_axis' (int): The index of the axis used as display Y.
        """

        axes = [0, 1, 2]  # All three axes in (sx, sy, sz) order
        axes.remove(primary_axis)  # Remove the axis we're slicing through
        axis1, axis2 = axes  # The remaining two axes form our 2D view
        
        # Get the actual direction vectors for these two axes
        dir1 = direction[:, axis1]  # Direction of first axis
        dir2 = direction[:, axis2]  # Direction of second axis
        
        # Get the target orientations for this medical view
        target_x, target_y = self._get_target_orientations(view)
        
        # Test both possible mappings to see which aligns better
        # Option 1: map axis1 to display X, axis2 to display Y
        score1_x = abs(np.dot(dir1, target_x))  # How well axis1 aligns with target X
        score1_y = abs(np.dot(dir2, target_y))  # How well axis2 aligns with target Y
        score1_total = score1_x + score1_y
        
        # Option 2: map axis2 to display X, axis1 to display Y (transpose)
        score2_x = abs(np.dot(dir2, target_x))  # How well axis2 aligns with target X
        score2_y = abs(np.dot(dir1, target_y))  # How well axis1 aligns with target Y
        score2_total = score2_x + score2_y
        
        # Choose the mapping with better alignment
        if score1_total >= score2_total:
            # Use standard mapping: axis1->X, axis2->Y
            transpose = False
            flip_x = np.dot(dir1, target_x) < 0  # Flip X if pointing wrong way
            flip_y = np.dot(dir2, target_y) < 0  # Flip Y if pointing wrong way
            x_axis, y_axis = axis1, axis2
        else:
            # Use transposed mapping: axis2->X, axis1->Y
            transpose = True
            flip_x = np.dot(dir2, target_x) < 0  # Flip X if pointing wrong way
            flip_y = np.dot(dir1, target_y) < 0  # Flip Y if pointing wrong way
            x_axis, y_axis = axis2, axis1

        return {
            'transpose': transpose,  # Whether to swap X and Y axes
            'flip_x': flip_x,       # Whether to flip horizontally
            'flip_y': flip_y,       # Whether to flip vertically
            'x_axis': x_axis,       # Which original axis becomes display X
            'y_axis': y_axis        # Which original axis becomes display Y
        }

    def extract_slice_with_orientation(self, view: str, 
                                       slice_idx: int) -> Tuple[np.ndarray, float]:
        """
        Extract a 2D image slice from the 3D volume for a given anatomical view 
        and apply the necessary transformations (transpose, flips) to orient it 
        according to medical imaging conventions.

        Args:
            view (str): The anatomical view ('axial', 'coronal', or 'sagittal').
            slice_idx (int): The index of the slice to extract along the view axis.

        Returns:
            Tuple[np.ndarray, float]: 
                - A 2D numpy array representing the transformed image slice.
                - A float representing the pixel aspect ratio for correct display.
        """
        dim_idx = self.view_indices[view]
        transform = self.view_transforms[view]
        
        # Extract the raw 2D slice data based on view
        if dim_idx == 2:  # (slicing through Z-axis)
            img_data = self.image_numpy[slice_idx, :, :] # shape: (Y, X)
            aspect = self.spacing[1] / self.spacing[0]   # sy / sx
        elif dim_idx == 1:  # (slicing through Y-axis)
            img_data = self.image_numpy[:, slice_idx, :] # shape: (Z, X)
            aspect = self.spacing[2] / self.spacing[0]   # sz / sx
        else:  # (slicing through X-axis)
            img_data = self.image_numpy[:, :, slice_idx] # shape: (Z, Y)
            aspect = self.spacing[2] / self.spacing[1]   # sz / sy
        
        # Apply transformations to orient the slice correctly
        
        # Step 1: Transpose if needed (swap X and Y axes)
        if transform['transpose']:
            img_data = np.transpose(img_data)
            aspect = 1.0 / aspect  # Invert aspect ratio when transposing
        
        # Step 2: Apply flips to match medical conventions
        if transform['flip_x']:
            img_data = np.flip(img_data, axis=1)  # Flip horizontally
        if transform['flip_y']:
            img_data = np.flip(img_data, axis=0)  # Flip vertically
        
        return img_data, aspect


if __name__ == "__main__":
    # dicom series 
    image_path = "data/demo_dicom"

    reader = MedicalImageReader(os.path.join(os.getcwd(), image_path))
    print("shape", reader.image_numpy.shape)
    print("spacing", reader.spacing)
    print("origin", reader.origin)
    print("direction", reader.direction)

    view = SAGITTAL
    slice_number = 0
    img, aspect = reader.extract_slice_with_orientation(view, slice_number)
    plt.imshow(img, cmap='gray', aspect=aspect)
    plt.title(f"{view.capitalize()} view, slice {slice_number}")
    plt.axis('off')
    plt.show()