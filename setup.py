from setuptools import setup, find_packages, Extension
import platform
import os

# Define the C-extension for ice_core
ice_core_extension = Extension(
    'ice.core.ice_core',
    sources=['ice/core/rcc_ffi/ice_core.c'],
    include_dirs=['ice/core/rcc_ffi'],
    # Compile arguments adjusted for different platforms
    extra_compile_args=[]
)

# Platform-specific compiler flags
if platform.system() == "Windows":
    # MSVC-compatible flags for Windows
    ice_core_extension.extra_compile_args = ['/LD', '/O2', '/W3'] # /LD for DLL
elif platform.system() == "Darwin": # macOS
    # Use zig cc for macOS cross-compilation on Linux
    # This assumes 'zig cc' is available and configured to target x86_64-macos
    os.environ['CC'] = 'zig cc -target x86_64-macos'
    os.environ['CXX'] = 'zig c++ -target x86_64-macos'
    ice_core_extension.extra_compile_args = ['-shared', '-std=c11', '-Wall', '-Wextra', '-pedantic', '-D_POSIX_C_SOURCE=200809L']
else: # Linux and other POSIX-like systems
    ice_core_extension.extra_compile_args = ['-shared', '-std=c11', '-Wall', '-Wextra', '-pedantic', '-D_POSIX_C_SOURCE=200809L']


# Read requirements, skipping comments and local file paths that pip install -e . can't parse
with open("requirements.txt", "r") as f:
    requirements = [
        line.strip() for line in f 
        if line.strip() and not line.startswith("#") and not line.startswith("-e") and not line.startswith("./")
    ]

setup(
    name="ice-engine",
    version="3.0.0",
    description="Indexless Context Engine - Embedded Memory OS",
    author="ICE Core Team",
    packages=find_packages(),
    ext_modules=[ice_core_extension],
    install_requires=requirements,
    python_requires='>=3.10',
    entry_points={
        'console_scripts': [
            'ice=ice.cli:main',
        ],
    },
)
