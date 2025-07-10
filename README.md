# Medical Image Viewer (Matplotlib MPR)

A powerful, interactive medical image viewer for DICOM, NIfTI, and MetaImage files, supporting Multi-Planar Reconstruction (MPR) directly using Matplotlib(pyton).

## Features
- View 3D medical images from three anatomical planes: Axial, Coronal, Sagittal
- Scroll through slices in any view (mouse wheel or slider)
- Click to synchronize crosshairs and views at any 3D location
- Interactive crosshairs across all views
- CT windowing controls (for CT images)
- Supports DICOM series (folder), NIfTI (.nii, .nii.gz), and MetaImage (.mha)

## Requirements
- Python 3.8+
- matplotlib
- numpy
- SimpleITK (for image reading)


Install requirements (if not already):
```bash
pip install matplotlib numpy SimpleITK pydicom
```

## Usage

```bash
python medical_viewer_matplot.py <image_path> [--modality MODALITY]
```

- `<image_path>`: Path to a DICOM folder, .nii, .nii.gz, or .mha file
- `--modality`: (Optional) Specify modality (e.g., CT, MRI). If not provided, will be inferred if possible.

### Example: View a NIfTI file
```bash
python medical_viewer_matplot.py /path/to/image.nii.gz
```

### Example: View a DICOM series (folder)
```bash
python medical_viewer_matplot.py /path/to/dicom_folder --modality CT
```

## Controls
- **Scroll**: Use mouse wheel or vertical slider to move through slices
- **Click**: Click on any view to synchronize all views at that 3D location
- **CT Window**: For CT images, use the window buttons to change window/level

## Notes
- For DICOM, provide the path to the folder containing the DICOM files (not a single file)
- For NIfTI or MetaImage, provide the path to the file
- The viewer will print image info and open an interactive window

## Troubleshooting
- If you see errors about missing files or series, check your path and file types
- For DICOM, ensure the folder contains valid DICOM files

## License
MIT 