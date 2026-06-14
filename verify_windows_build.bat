@echo off
setlocal enabledelayedexpansion

echo ==========================================================
echo  Windows Build Verification Script
echo ==========================================================
echo.

set "OUTPUT_DIR=dist"
set "WINDOWS_PYTHON_DIR=%OUTPUT_DIR%\python\windows"
set "LINUX_PYTHON_DIR=%OUTPUT_DIR%\python" :: Assuming Linux builds are in dist/python

echo --- Checking Generated Windows Python Wheels ---
if exist "%WINDOWS_PYTHON_DIR%" (
    echo Listing files in '%WINDOWS_PYTHON_DIR%':
    dir "%WINDOWS_PYTHON_DIR%\*.whl" /b
) else (
    echo ❌ ERROR: Windows Python build directory not found: '%WINDOWS_PYTHON_DIR%'
    echo Please run 'build_windows.bat' first.
    goto :eof
)

echo.
echo --- Manual Comparison Instructions ---
echo To cross-verify the quality with your Linux builds, you should:
echo 1. Transfer your Linux-built Python wheels (from the '%LINUX_PYTHON_DIR%' folder)
echo    to this Windows machine, perhaps into a temporary folder like '.\dist\python\linux_builds'.
echo 2. Visually compare the file names. You should have:
echo    - For each Python version (3.10, 3.11, 3.12) that built successfully:
echo    - 4 .whl files for each SKU: ice_community, ice_developer_pro, ice_enterprise, ice_unlimited.
echo    - Total of 12 .whl files if all Python versions built.
echo 3. Compare file sizes: The Windows (.whl) and Linux (.whl) files for the same SKU
echo    and Python version should have *similar* (but not necessarily identical) sizes.
echo    Differences are expected due to different compilers (MSVC vs GCC) and OS packaging.
echo 4. (Advanced) Extract and Compare Metadata:
echo    - A .whl file is a zip archive. You can rename it to .zip and open it.
echo    - Compare the 'PKG-INFO' file inside the Windows .whl with its Linux counterpart.
echo    - The contents (version, dependencies) should be identical.
echo 5. (Functional Test) For true quality verification, install a Windows .whl in a clean
echo    Windows Python environment and run your project's Python test suite against it.
echo    Compare these test results with the results from running the same test suite
echo    against a Linux .whl installed in a Linux Python environment.

echo.
echo ==========================================================
echo ✅ Verification script finished.
echo ==========================================================
pause
goto :eof
