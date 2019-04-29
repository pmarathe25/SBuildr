from srbuild.logger import G_LOGGER
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
