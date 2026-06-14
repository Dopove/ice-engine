from setuptools import setup, find_packages, Extension

# Define the C-extension for ice_core
ice_core_extension = Extension(
    'ice.core.ice_core',
    sources=['ice/core/rcc_ffi/ice_core.c'],
    include_dirs=['ice/core/rcc_ffi'],
    extra_compile_args=['-std=c11', '-Wall', '-Wextra', '-pedantic', '-D_POSIX_C_SOURCE=200809L'],
)

# Read requirements, skipping comments and local file paths that pip install -e . can't parse
with open("requirements.txt", "r") as f:
    requirements = [
        line.strip() for line in f 
        if line.strip() and not line.startswith("#") and not line.startswith("-e") and not line.startswith("./")
    ]

# Dynamically find all subpackages of raganything
rag_packages = ['raganything'] + ['raganything.' + p for p in find_packages(where='RAG-Anything/raganything')]

setup(
    name="ice-engine",
    version="3.0.0",
    description="Infinite Context Engine - Embedded Memory OS",
    author="Dopove",
    # Include both 'ice' and 'raganything' as top-level packages
    packages=find_packages(include=['ice', 'ice.*']) + rag_packages,
    # Map 'raganything' to its actual directory
    package_dir={
        'raganything': 'RAG-Anything/raganything'
    },
    ext_modules=[ice_core_extension],
    install_requires=requirements,
    python_requires='>=3.10',
    entry_points={
        'console_scripts': [
            'ice=ice.cli:main',
        ],
    },
)
