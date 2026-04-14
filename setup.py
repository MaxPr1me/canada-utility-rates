"""
canada-utility-costs: Setup script.

This file lets you install the project as a Python package so imports
work cleanly from any script.  Run:

    pip install -e .

The '-e' flag means "editable" — changes you make to the source files
take effect immediately without reinstalling.
"""

from setuptools import setup, find_packages

setup(
    name="canada-utility-costs",
    version="0.1.0",
    description="Scrape, store, and browse utility rates across Canada",
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=[
        "requests>=2.31.0",
        "beautifulsoup4>=4.12.0",
        "lxml>=4.9.0",
        "pdfplumber>=0.10.0",
        "openpyxl>=3.1.0",
        "pandas>=2.1.0",
        "pydantic>=2.5.0",
        "python-dateutil>=2.8.0",
        "tqdm>=4.66.0",
    ],
)
