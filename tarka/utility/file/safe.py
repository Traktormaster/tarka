import os
import shutil
import tempfile
from pathlib import Path
from typing import Union


class SafeFile:
    """
    Provides a way to write and read a file on a path safely. Meaning that writing a new version of the file will
    never leave it in an undefined state. In other words, either the new file is successfully written or the old
    version is retained.

    This utility may be necessary on Windows, because the file moving/replacing (MoveFileEx) is not atomic.

    Write new versions of a file safely by utilizing a temporary file and keeping a backup.
    Read the file and fallback to the backup if necessary.

    Not thread-safe!
    """

    __slots__ = ("normal", "backup")

    def __init__(self, path: Union[str, Path], backup_suffix: str = "bak"):
        if not isinstance(path, Path):
            path = Path(path)
        self.normal = path
        self.backup = path.with_name(f"{path.name}.{backup_suffix}")

    def read(self) -> bytes:
        """
        Read the normal path or fall back to the backup.
        """
        try:
            return self.normal.read_bytes()
        except OSError:
            return self.backup.read_bytes()

    def write(self, data: bytes) -> None:
        """
        Write a new version of the file, manage the backup automatically.
        """
        fd, temp_path = tempfile.mkstemp(dir=self.normal.parent, text=False)
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(data)  # Write new version to temp file.
            if self.normal.exists():  # Backup old version if it exists.
                # Removing the backup is necessary to avoid consistency issues made by overwriting.
                # Removing the backup is safe, because if the normal path exists it must be a valid version,
                # as it only ever gets replaced (moved) over. In other words, the backup is never newer than
                # the normal path when that exists.
                self.backup.unlink(missing_ok=True)  # Remove old backup first.
                shutil.copy2(self.normal, self.backup)  # Copy old version to backup.
            # The implementation of replace is atomic on POSIX compatible systems, so the backup feature will
            # never be utilized. However, on Windows the move may be a delete&move on the FS metadata level and
            # thus the old version might be lost. By having a backup of the last version this issue is handled.
            os.replace(temp_path, self.normal)  # Replace old version with temp (new).
        finally:
            try:
                os.unlink(temp_path)  # do not leave the temp file for whatever reason.
            except OSError:
                pass
