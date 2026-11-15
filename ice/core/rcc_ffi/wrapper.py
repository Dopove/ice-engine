# SPDX-License-Identifier: MIT

import ctypes
import os
import sys

# Define the structures to match the C headers
class IceMessage(ctypes.Structure):
    _fields_ = [
        ("role", ctypes.c_char_p),
        ("content", ctypes.c_char_p)
    ]

class IceVector(ctypes.Structure):
    _fields_ = [
        ("data", ctypes.POINTER(ctypes.c_float)),
        ("length", ctypes.c_size_t)
    ]

class IceStringArray(ctypes.Structure):
    _fields_ = [
        ("strings", ctypes.POINTER(ctypes.c_char_p)),
        ("count", ctypes.c_size_t)
    ]

class AssembledPrompt(ctypes.Structure):
    _fields_ = [
        ("messages", ctypes.POINTER(IceMessage)),
        ("count", ctypes.c_size_t),
        ("total_tokens", ctypes.c_size_t)
    ]

_lib = None

def get_lib():
    global _lib
    if _lib is not None:
        return _lib

    # Determine the library name based on the OS
    if sys.platform == "win32":
        lib_name = "ice_core.dll"
    elif sys.platform == "darwin":
        lib_name = "libice_core.dylib"
    else:
        lib_name = "libice_core.so"

    # Search for the library in the current directory or a lib/ directory
    search_paths = [
        os.path.join(os.path.dirname(__file__), lib_name),
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "build_wheel_pkg", lib_name),
        lib_name
    ]

    for path in search_paths:
        if os.path.exists(path):
            try:
                _lib = ctypes.CDLL(path)
                break
            except Exception as e:
                print(f"Warning: Failed to load {path}: {e}")
    
    if _lib is None:
        raise RuntimeError(
            f"❌ CRITICAL ERROR: RCC Core Library '{lib_name}' could not be loaded. "
            f"ICE V3 requires the Resonant C Compiler (RCC) core for hardware stability. "
            f"Please ensure ICE was built with rgcc."
        )

    # Define argument and return types for the FFI functions
    _lib.rcc_free_string_array.argtypes = [ctypes.POINTER(IceStringArray)]
    _lib.rcc_free_string_array.restype = None

    _lib.rcc_assemble_prompt.argtypes = [
        ctypes.POINTER(IceMessage), ctypes.c_size_t,
        ctypes.POINTER(IceMessage), ctypes.c_size_t,
        ctypes.POINTER(IceStringArray), ctypes.POINTER(IceStringArray),
        ctypes.c_char_p, ctypes.c_int
    ]
    _lib.rcc_assemble_prompt.restype = ctypes.POINTER(AssembledPrompt)

    _lib.rcc_free_assembled_prompt.argtypes = [ctypes.POINTER(AssembledPrompt)]
    _lib.rcc_free_assembled_prompt.restype = None

    _lib.rcc_save_message.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p]
    _lib.rcc_save_message.restype = ctypes.c_int

    _lib.rcc_search_episodic.argtypes = [ctypes.c_char_p, ctypes.POINTER(IceVector), ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int]
    _lib.rcc_search_episodic.restype = ctypes.POINTER(IceStringArray)

    _lib.rcc_ingest_document.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p]
    _lib.rcc_ingest_document.restype = ctypes.c_int

    _lib.rcc_test_return.argtypes = []
    _lib.rcc_test_return.restype = ctypes.POINTER(DummyStruct)

    return _lib

class DummyStruct(ctypes.Structure):
    _fields_ = [
        ("value", ctypes.c_int)
    ]


def rcc_free_string_array(ptr):
    lib = get_lib()
    if lib:
        lib.rcc_free_string_array(ptr)

def rcc_free_assembled_prompt(ptr):
    lib = get_lib()
    if lib:
        lib.rcc_free_assembled_prompt(ptr)
