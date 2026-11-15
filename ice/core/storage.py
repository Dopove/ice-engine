# SPDX-License-Identifier: MIT

import os
import logging
from typing import List
import fsspec

logger = logging.getLogger("ice_storage")

class StorageManager:
    """
    Universal Storage Abstraction Layer for ICE.
    Supports local filesystem, Amazon S3, Google Cloud Storage, and other S3-compatible stores.
    Explicitly excludes Azure Blob Storage support.
    """
    
    @staticmethod
    def _check_protocol(path: str):
        if path.startswith("abfs://") or path.startswith("az://"):
            raise ValueError("ICE Engine explicitly does not support Microsoft Azure Blob Storage.")

    @staticmethod
    def is_remote_path(path: str) -> bool:
        StorageManager._check_protocol(path)
        return "://" in path and not path.startswith("file://")

    @staticmethod
    def is_dir(path: str) -> bool:
        """Determines if a path is a directory (local) or prefix (remote)."""
        StorageManager._check_protocol(path)
        try:
            fs, _ = fsspec.core.url_to_fs(path)
            return fs.isdir(path)
        except Exception as e:
            logger.error(f"StorageManager: Error checking directory {path}: {e}")
            return False

    @staticmethod
    def exists(path: str) -> bool:
        """Checks if a file or directory exists."""
        StorageManager._check_protocol(path)
        try:
            fs, _ = fsspec.core.url_to_fs(path)
            return fs.exists(path)
        except Exception as e:
            logger.error(f"StorageManager: Error checking existence of {path}: {e}")
            return False

    @staticmethod
    def list_files(path: str) -> List[str]:
        """Recursively lists all files in a directory or remote prefix."""
        StorageManager._check_protocol(path)
        fs, _ = fsspec.core.url_to_fs(path)
        
        files = []
        for f in fs.find(path):
            # fsspec find sometimes returns paths without protocol, we need to add it back if remote
            if StorageManager.is_remote_path(path):
                protocol = path.split("://")[0]
                # Avoid double slashes if f already starts with /
                clean_f = f.lstrip('/')
                files.append(f"{protocol}://{clean_f}")
            else:
                files.append(f)
        return files

    @staticmethod
    def fetch_to_local(path: str, temp_dir: str) -> str:
        """Fetches a file to a local temporary directory if it's on remote storage."""
        StorageManager._check_protocol(path)
        if StorageManager.is_remote_path(path):
            fs, _ = fsspec.core.url_to_fs(path)
            os.makedirs(temp_dir, exist_ok=True)
            local_path = os.path.join(temp_dir, os.path.basename(path))
            
            logger.info(f"StorageManager: Downloading {path} to {local_path}...")
            fs.get(path, local_path)
            return local_path
        else:
            if not os.path.exists(path):
                raise FileNotFoundError(f"Path not found: {path}")
            return path
