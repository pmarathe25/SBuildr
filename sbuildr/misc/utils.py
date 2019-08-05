from typing import List
import subprocess
import shutil
import time
import sys
import os

def time_subprocess(cmd: List[str]) -> (subprocess.CompletedProcess, float):
    start = time.time()
    status = subprocess.run(cmd, capture_output=True)
    end = time.time()
    return status, end - start

# Returns the captured output of a subprocess call.
def subprocess_output(status: subprocess.CompletedProcess):
    return f"{wrap_str(' Captured stdout ')}\n{status.stdout.decode(sys.stdout.encoding)}\n{wrap_str(' Captured stderr ')}\n{status.stderr.decode(sys.stdout.encoding)}"

def wrap_str(inp: str, wrap: str='='):
    terminal_width, _ = shutil.get_terminal_size()
    return inp.center(terminal_width, wrap)

# Copies src to dst. dst may be either a complete path or containing directory.
def copy_path(src: str, dst: str) -> bool:
    try:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
        return True
    except PermissionError:
        G_LOGGER.error(f"Could not write to {dst}. Do you have sufficient privileges?")
        return False
