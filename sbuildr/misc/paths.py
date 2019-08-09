# Platform independent paths and file naming conventions.
import os

# TODO: Edit these functions to take into account other platforms
def loader_path_env_var() -> str:
    """
    Returns the name of the environment variable used to specify paths to the loader.
    """
    return "LD_LIBRARY_PATH"

def name_to_libname(name: str) -> str:
    """
    Given the name of a library, specifies the basename of the corresponding file.
    For example, on Linux, name_to_libname("stdc++") would return "libstdc++.so"

    Returns:
        str: The basename of the library.
    """
    return f"lib{name}.so"

def libname_to_name(libname: str) -> str:
    """
    Given the basename of a library, specifies the corresponding library name.
    For example, on Linux, libname_to_name("libstdc++.so") would return "stdc++"

    :returns: The name of the library.
    """
    prefix = "lib"
    if libname.startswith(prefix):
        libname = libname[len(prefix):]
    return os.path.splitext(libname)[0]

def name_to_execname(name: str) -> str:
    """
    Given the name of a executable, specifies the basename of the corresponding file.
    For example, on Windows, name_to_execname("test") would return "test.exe"

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
