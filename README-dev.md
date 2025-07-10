# MedView Developer Guide

## Project Summary
MedView is a Python package for interactive visualization and exploration of medical images (DICOM, NIfTI, MHA) with multi-planar reconstruction (MPR) support. This guide is for developers who want to clone, set up, and run the project locally.

---

## Prerequisites
- Python 3.7+
- Git

---

## Setup Instructions

1. **Clone the Repository**
   ```bash
   git clone <your-repo-url>
   cd medview-python
   ```

2. **Create and Activate a Virtual Environment**
   ```bash
   python3 -m venv med-venv
   source med-venv/bin/activate
   ```

3. **Install the Package and Dependencies**
   ```bash
   pip install --upgrade pip
   pip install -e .
   ```

---

## Running the Medical Viewer

After installation, you can launch the viewer from the command line:

```bash
medview <image_path> [--modality MODALITY]
```
- `<image_path>`: Path to a DICOM folder, `.nii`, `.nii.gz`, or `.mha` file
- `--modality`: (Optional) Specify modality, e.g., `CT`, `MRI`

**Example:**
```bash
medview data/sample.nii.gz --modality CT
```

---

## Using MedView in Jupyter Notebooks

1. **Install Jupyter (if needed):**
   ```bash
   pip install notebook ipympl
   ```
2. **Start Jupyter Notebook:**
   ```bash
   jupyter notebook
   ```
3. **Example Usage in a Notebook:**
   ```python
   from medview.medical_viewer_matplot import MedicalViewerMatplot
   from medview.medical_image_reader import MedicalImageReader

   reader = MedicalImageReader("data/sample.nii.gz", modality="CT")
   viewer = MedicalViewerMatplot(reader)
   viewer.view_dicom_series()
   ```

---

## Notes
- All build artifacts, virtual environments, and cache files are git-ignored.
- For development, use `pip install -e .` to reflect code changes immediately.
- For questions or contributions, please open an issue or pull request.
