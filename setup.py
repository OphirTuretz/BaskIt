"""Setup file for BaskIt package."""
from setuptools import setup, find_packages

setup(
    name="baskit",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        # Add your dependencies from requirements.txt here
        "pytest>=8.1.1",
    ],
    python_requires=">=3.8",
) 