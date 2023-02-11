import errno
import os
import sys
import tempfile
from pathlib import Path
from typing import Optional, Callable, Tuple

from tarka.utility.file.name import split_extension


class ReserveFile:
    """
    Try and reserve a filename as is in by the given path, by creating it safely with EXCL flag. If that fails
    then the file name is to be adjusted with a random value to resolve conflicts.

    This is a variant of tempfile.mkstemp() that provides a behavioural override interface for adjusting the file-name
    and firstly tries to create the file without a random sequence. Additionally if the filename would be too long for
    the system, it will sensibly truncate characters.
    """

    def __init__(self, max_name_length: int = 255):
        """
        :param max_name_length: This is only to optimize the initial truncation loop. Should match the maximum
            file-name length of the current platform.
        """
        self._max_name_length = max_name_length + 1  # +1 to use the value conveniently at comparison

        # mirrors how a binary file is created by mkstemp
        self.flags = os.O_RDWR | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_NOFOLLOW"):
            self.flags |= os.O_NOFOLLOW
        if hasattr(os, "O_BINARY"):
            self.flags |= os.O_BINARY

    def reserve(self, path_or_directory: Path, name: str = "") -> str:
        """
        This is a convenience function that should be used if the file is reserved for later, and no operations are
        to be done with it right now.
        The reserved name is returned which could be different to the input name.
        The directory must exist.
        """
        fd, name = self.open_reserve(path_or_directory, name)
        os.close(fd)
        return name

    def open_reserve(self, path_or_directory: Path, name: str = "") -> Tuple[int, str]:
        """
        Returns the open file-descriptor to the reserved file and its name, which could be different to the input name.
        The directory must exist.
        """
        if not name:
            prefix, suffix = self._adjust_name_direct(path_or_directory.name)
            directory = self._resolve(path_or_directory.parent)
        else:
            prefix, suffix = self._adjust_name_direct(name)
            directory = self._resolve(path_or_directory)
        fd_name = self._reserve_adjust(self._mk_direct, suffix, prefix, directory, 0)
        if fd_name:
            return fd_name
        prefix, suffix = self._adjust_name_parts_temp(prefix, suffix)
        return self._reserve_adjust(self._mk_temp, suffix, prefix, directory, 8)  # mkstemp adds 8 char random sequence

    def _resolve(self, path: Path) -> Path:
        """
        Can be overridden if directory resolution errors need special care.
        """
        return path.resolve(strict=True)

    def _adjust_name_direct(self, name: str) -> Tuple[str, str]:
        """
        Can be overridden to customize the filename to be created at the direct reserve attempt.
        We need to make a the name split to prepare for inserting a random sequence in case of a conflict.
        """
        return split_extension(name)

    def _adjust_name_parts_temp(self, prefix: str, suffix: str) -> Tuple[str, str]:
        """
        Can be overridden to customize the filename to be created at the temp/random sequence attempts.
        The default implementation adds a separator character to the prefix, so the file name stay visually
        clear from random sequence. The suffix should start with a separator dot for the extension, so no
        change needed there.
        """
        if prefix.endswith("-"):
            return prefix, suffix
        return prefix + "-", suffix

    def _reserve_adjust(
        self,
        mk_fn: Callable[[str, str, Path], Optional[Tuple[int, str]]],
        suffix: str,
        prefix: str,
        directory: Path,
        mk_len: int,
    ) -> Optional[Tuple[int, str]]:
        while True:
            try:
                return mk_fn(suffix, prefix, directory)
            except OSError as e:
                if e.errno == errno.ENAMETOOLONG or (sys.platform.startswith("win") and e.errno == errno.EINVAL):
                    if len(prefix) + len(suffix) <= 1:
                        raise e  # no way to truncate more
                else:
                    raise e
            # adjust prefix/suffix to make name sorter
            while True:
                # NOTE: The underlying FS may enforce some normalization in addition to the encoding, so we actually
                # cannot accurately calculate how long the name would be in the representation of the FS.
                # So we truncate to sensible length in one go, then if that is still not acceptable we proceed by
                # a character each cycle with trial and error.
                pre_len = len(os.fsencode(prefix))
                suf_len = len(os.fsencode(suffix))
                if pre_len > suf_len:
                    prefix = prefix[:-1]
                elif suf_len > 0:
                    suffix = suffix[1:]
                if pre_len + suf_len <= self._max_name_length - mk_len:
                    break

    def _mk_direct(self, suffix: str, prefix: str, directory: Path) -> Optional[Tuple[int, str]]:
        # This is based on the internal mkstemp().
        name = prefix + suffix
        try:
            fd = os.open(directory / name, self.flags, 0o600)
        except FileExistsError:
            pass
        except PermissionError:
            if not sys.platform.startswith("win") or not directory.is_dir() or not os.access(directory, os.W_OK):
                raise
        else:
            return fd, name

    def _mk_temp(self, suffix: str, prefix: str, directory: Path) -> Tuple[int, str]:
        fd, temp_path = tempfile.mkstemp(suffix, prefix, directory)
        return fd, os.path.basename(temp_path)
