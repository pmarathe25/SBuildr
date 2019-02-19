from sbuild.logger import G_LOGGER
import hashlib
import sys
import os

def str_hash(obj) -> str:
    """
    Returns a string representation of the hash of a string constructed from the specified object.

    Args:
        obj (object): The object to hash.

    Returns:
        str: The resulting hash.
    """
    in_str = " ".join(obj).strip()
    generated_hash = hashlib.md5(in_str.encode()).hexdigest()
    G_LOGGER.verbose(f"Generated hash {generated_hash} from '{in_str}'")
    return generated_hash


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
