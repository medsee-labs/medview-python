import numpy as np
from enum import Enum

# Constants for the three standard medical viewing planes
AXIAL = "axial"      # Horizontal slices (looking down from above)
CORONAL = "coronal"  # Front-to-back slices (looking from front or back)
SAGITTAL = "sagittal" # Left-to-right slices (looking from the side)

# Standard 3D coordinate system unit vectors
# These represent the basic directions in 3D space
X = np.array([1, 0, 0])   # X direction (left-right in medical images)
Y = np.array([0, 1, 0])   # Y direction (front-back in medical images)  
Z = np.array([0, 0, 1])   # Z direction (up-down in medical images)

class MODALITY(Enum):
    MR = "MR"
    CT = "CT"


class CT_WINDOW_TYPE(Enum):
    CHEST = "chest"
    ABDOMEN = "abdomen"
    BONE = "bone"
    GENERAL = "general"
    BRAIN = "brain"

# Define window levels for CT scans
# (min_value, max_value)
CT_WINDOW_LEVELS = {
    CT_WINDOW_TYPE.BRAIN: (40, 80),
    CT_WINDOW_TYPE.CHEST: (-1000, 300),
    CT_WINDOW_TYPE.ABDOMEN: (-100, 300),
    CT_WINDOW_TYPE.BONE: (400, 1800),
    CT_WINDOW_TYPE.GENERAL: (-1000, 4000),
}

