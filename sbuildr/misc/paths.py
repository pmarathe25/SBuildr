# Platform independent paths and file naming conventions.
import os

def libname(name: str) -> str:
    """
    Given the name of a library, specifies the basename of the corresponding file.
    For example, on Linux, libname("stdc++") would return "libstdc++.so"

    Returns:
        str: The basename of the library.
    """
    return f"lib{name}.so"

def execname(name: str) -> str:
    """
    Given the name of a executable, specifies the basename of the corresponding file.
    For example, on Windows, execname("test") would return "test.exe"

    Returns:
        str: The basename of the library.
    """
    return name

def default_library_install_path() -> str:
    """
    Returns the default installation path for libraries on this system.
    """
    return os.path.join(os.sep, "usr", "local", "lib")

def default_executable_install_path() -> str:
    """
    Returns the default installation path for executables on this system.
    """
    return os.path.join(os.sep, "usr", "local", "bin")

def default_header_install_path() -> str:
    """
    Returns the default installation path for headers on this system.
    """
    return os.path.join(os.sep, "usr", "local", "include")
