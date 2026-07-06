from setuptools import setup, find_packages
import platform

# Read requirements
with open("requirements.txt", "r") as f:
    requirements = [
        line.strip() for line in f 
        if line.strip() and not line.startswith("#") and not line.startswith("-e") and not line.startswith("./")
    ]

setup(
    name="ice-engine",
    version="3.0.0",
    description="Infinite Context Engine - Embedded Memory OS",
    author="Dopove",
    # Remove ext_modules as we are building the shared library separately
    packages=find_packages(),
    # Include the compiled shared library as package data
    package_data={
        'ice.core.rcc_ffi': ['*.so', '*.dll', '*.dylib'],
    },
    install_requires=requirements,
    python_requires='>=3.10',
    entry_points={
        'console_scripts': [
            'ice=ice.cli:main',
        ],
    },
)
