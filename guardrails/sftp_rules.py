"""
SFTP filesystem safety rules.

Prevents path traversal and unsafe file operations.
"""

import os
import posixpath
from pathlib import Path
from typing import Optional


def safe_filename(name: str) -> str:
    """
    Sanitize a filename to prevent path traversal.
    
    Args:
        name: Original filename (may contain path components)
        
    Returns:
        Safe filename (basename only, no path traversal)
    """
    if not name:
        return ""
    
    # Extract basename to remove any path components
    safe = posixpath.basename(name)
    
    # Remove path traversal attempts
    safe = safe.replace("..", "")
    safe = safe.replace("/", "_")
    safe = safe.replace("\\", "_")
    
    # Remove null bytes and other dangerous characters
    safe = safe.replace("\x00", "")
    safe = safe.replace("\r", "")
    safe = safe.replace("\n", "")
    
    # Limit length
    if len(safe) > 255:
        name_part = safe[:200]
        ext_part = safe[200:]
        safe = name_part + ext_part[-55:] if len(ext_part) > 55 else name_part + ext_part
    
    return safe


def validate_remote_path(remote_dir: Optional[str] = None) -> str:
    """
    Validate and return safe remote directory path.
    
    Args:
        remote_dir: Optional remote directory override
        
    Returns:
        Validated remote directory path
    """
    # Get from env or use default
    if not remote_dir:
        remote_dir = os.getenv("SFTP_REMOTE_DIR")
    
    if not remote_dir:
        # Default fallback (should be set in production)
        sftp_user = os.getenv("SFTP_USER", "user")
        remote_dir = f"/home/{sftp_user}/public_html"
    
    # Normalize path (remove trailing slashes, resolve ..)
    remote_dir = posixpath.normpath(remote_dir)
    
    # Ensure it's absolute
    if not remote_dir.startswith("/"):
        sftp_user = os.getenv("SFTP_USER", "user")
        remote_dir = f"/home/{sftp_user}/{remote_dir}"
        remote_dir = posixpath.normpath(remote_dir)
    
    # Prevent path traversal outside home
    if ".." in remote_dir:
        # Remove .. components
        parts = remote_dir.split("/")
        safe_parts = []
        for part in parts:
            if part == "..":
                if safe_parts:
                    safe_parts.pop()
            elif part and part != ".":
                safe_parts.append(part)
        remote_dir = "/" + "/".join(safe_parts)
    
    return remote_dir

