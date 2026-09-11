from setuptools import setup, find_packages
from setuptools.command.build_py import build_py as _build_py
from setuptools.dist import Distribution
import platform
import os
import shutil
import subprocess

RCC_DIR = os.path.join("ice", "core", "rcc_ffi")
RCC_SRC = os.path.join(RCC_DIR, "ice_core.c")

# ponytail: three targets, one small dispatch table -- no build-system plugin,
# no per-OS Extension() subclassing. Upgrade path: cibuildwheel, if this ever
# needs to support more than "cross-compile the three desktop OSes from CI".


def _host_target() -> str:
    return {"Windows": "windows", "Darwin": "darwin"}.get(platform.system(), "linux")


def _lib_filename(target: str) -> str:
    return {"windows": "ice_core.dll", "darwin": "libice_core.dylib"}.get(target, "libice_core.so")


def _compile_native_lib(target: str) -> None:
    """
    Compiles ice/core/rcc_ffi/ice_core.c into the plain shared library
    ice/core/rcc_ffi/wrapper.py actually loads via ctypes.CDLL (libice_core.so
    / libice_core.dylib / ice_core.dll, searched next to wrapper.py itself).

    This is deliberately NOT built as a setuptools Extension()/ext_modules --
    ice_core.c has no Python C-API calls, so building it as a Python
    extension module produces an unimportable artifact (no PyInit_ symbol)
    under a filename (ice_core.cpython-3xx-...so) wrapper.py never looks for.
    A plain shared-library compile matches what the runtime loader expects.

    ICE_BUILD_TARGET overrides the host OS for cross-compiling a target this
    CI has no matching runner for (macOS, via zig, from a Linux runner).
    """
    out_path = os.path.join(RCC_DIR, _lib_filename(target))
    common = ["-std=c11", "-O2", "-Wall", "-Wextra", "-D_POSIX_C_SOURCE=200809L", "-I", RCC_DIR]
    have_zig = shutil.which("zig") is not None

    if target == "windows":
        if shutil.which("cl") and not have_zig:
            cmd = ["cl", "/LD", "/O2", "/W3", RCC_SRC, f"/Fe:{out_path}"]
        elif have_zig:
            cmd = ["zig", "cc", "-target", "x86_64-windows-gnu", "-shared", *common, "-o", out_path, RCC_SRC]
        else:
            cmd = ["cl", "/LD", "/O2", "/W3", RCC_SRC, f"/Fe:{out_path}"]
    elif target == "darwin":
        if have_zig:
            cmd = ["zig", "cc", "-target", "x86_64-macos", "-dynamiclib", *common, "-o", out_path, RCC_SRC]
        else:
            cmd = ["cc", "-dynamiclib", *common, "-o", out_path, RCC_SRC]
    else:  # linux
        cc = "cc" if shutil.which("cc") else ("gcc" if shutil.which("gcc") else None)
        if cc:
            cmd = [cc, "-shared", "-fPIC", *common, "-o", out_path, RCC_SRC]
        elif have_zig:
            cmd = ["zig", "cc", "-shared", "-fPIC", *common, "-o", out_path, RCC_SRC]
        else:
            raise RuntimeError("No C compiler (cc/gcc) or zig found to build the native core.")

    print(f"[ICE build] Compiling native core for target={target}: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)


class BuildPyWithNativeLib(_build_py):
    def run(self):
        target = os.environ.get("ICE_BUILD_TARGET", "").lower() or _host_target()
        _compile_native_lib(target)
        super().run()


class BinaryDistribution(Distribution):
    """
    Tells bdist_wheel this wheel is platform-specific (has a native binary
    payload) even though there's no real ext_modules entry -- otherwise it
    tags the wheel py3-none-any, and the linux/macos/windows wheels (each
    bundling a different libice_core.*) would all get the same, wrong,
    "universal" filename.
    """
    def has_ext_modules(self):
        return True


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
    packages=find_packages(),
    package_data={"ice.core.rcc_ffi": ["libice_core.so", "libice_core.dylib", "ice_core.dll"]},
    include_package_data=True,
    distclass=BinaryDistribution,
    cmdclass={"build_py": BuildPyWithNativeLib},
    install_requires=requirements,
    python_requires='>=3.11',
    entry_points={
        'console_scripts': [
            'ice=ice.cli:main',
        ],
    },
)
