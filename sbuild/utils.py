import sys
import os

def frozen_hash(obj) -> str:
    """
    Returns a string representation of a hash of a frozen set constructed from the specified object.

    Args:
        obj (object): The object to hash.

    Returns:
        str: The resulting hash.
    """
    return f"{hash(frozenset(obj)) % ((sys.maxsize + 1) * 2)}"

def timestamp(path) -> int:
    """
    Returns the timestamp for a given path - this corresponds to the time at which the path was last modified.

    Args:
        path (str): The path to check

    Returs:
        int: The time at which the path was last modified in number of nanoseconds since the epoch, or -1 if the file does not exist.
    """
    try:
        return os.path.getmtime(path)
    except FileNotFoundError:
        return -1
