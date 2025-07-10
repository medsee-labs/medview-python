from setuptools import setup, find_packages

setup(
    name="medview",
    version="0.1.0",
    description="A medical imaging viewer library",
    author="Chitra Singh",
    packages=find_packages(),
    install_requires=[
        "SimpleITK>=2.2.1",
        "PyQt5",
        "numpy",
        "ipympl",
    ],
    python_requires=">=3.7",
    entry_points={
        "console_scripts": [
            "medview=medview.medical_viewer_matplot:main"
        ]
    },
)