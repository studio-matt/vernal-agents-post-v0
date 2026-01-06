import os
import re
from pathlib import PurePosixPath
from typing import Tuple

_BAD_FILENAME_RE = re.compile(r"[^A-Za-z0-9._-]")

def safe_filename(name: str) -> str:
    """
    Normalize filename to avoid traversal & weird chars.
    """
    if not name:
        return "file"
    name = name.strip().replace("\x00", "")
    name = os.path.basename(name)  # drops any path
    name = _BAD_FILENAME_RE.sub("_", name)
    # prevent hidden dotfiles or empty
    if name in (".", "..", ""):
        name = "file"
    return name[:180]

def validate_remote_path(remote_dir: str) -> Tuple[bool, str]:
    """
    Ensure remote_dir is a safe absolute POSIX path and doesn't contain traversal.
    """
    if not remote_dir:
        return (False, "missing_remote_dir")
    p = PurePosixPath(remote_dir)
    if not str(p).startswith("/"):
        return (False, "remote_dir_not_absolute")
    if ".." in p.parts:
        return (False, "remote_dir_traversal")
    return (True, "ok")
