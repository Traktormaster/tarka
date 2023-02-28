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

    def __init__(self, max_name_length: int = 255, fs_name_encode_length: Optional[Callable[[str], int]] = None):
        """
        :param max_name_length: This is only to optimize the initial truncation loop. Should match the maximum
            file-name length of the current platform.
        :param fs_name_encode_length: Customizable name-length calculator for the initial stripping round.
        """
        self.max_name_length = max_name_length
        if fs_name_encode_length is None:
            if sys.platform.startswith("linux"):
                self.fs_name_encode_length = self._fs_name_encode_utf8_bytes_length
            else:  # Assuming Windows, macOS or other systems that may have Unicode filename support.
                self.fs_name_encode_length = self._fs_name_encode_unicode_length
        else:
            self.fs_name_encode_length = fs_name_encode_length

        # mirrors how a binary file is created by mkstemp
        self.flags = os.O_RDWR | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_NOFOLLOW"):
            self.flags |= os.O_NOFOLLOW
        if hasattr(os, "O_BINARY"):
            self.flags |= os.O_BINARY

    def _fs_name_encode_unicode_length(self, name: str) -> int:
        """
        This is used for platforms that have support for Unicode filename representation on their primary filesystems.
        For these the unicode length shall be considered as the filename length as-is.
        """
        return len(name)

    def _fs_name_encode_utf8_bytes_length(self, name: str) -> int:
        """
        On Linux (and possibly other POSIX systems that originate from the 1970s) the filename length limit is measured
        as bytes, with a maximum length of 255. This limitation is so low-level in the kernel and all the file-systems
        as well, that it will not be enhanced soon.
        """
        return len(os.fsencode(name))

    def reserve(self, path_or_directory: Path, name: str = "", try_as_is: bool = True) -> str:
        """
        This is a convenience function that should be used if the file is reserved for later, and no operations are
        to be done with it right now.
        The reserved name is returned which could be different to the input name.
        The directory must exist.
        """
        fd, name = self.open_reserve(path_or_directory, name, try_as_is)
        os.close(fd)
        return name

    def open_reserve(self, path_or_directory: Path, name: str = "", try_as_is: bool = True) -> Tuple[int, str]:
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
        if try_as_is:
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
            pre_len = self.fs_name_encode_length(prefix)
            suf_len = self.fs_name_encode_length(suffix)
            while True:
                # NOTE: The underlying FS may enforce some normalization in addition to the encoding, so we actually
                # cannot accurately calculate how long the name would be in the representation of the FS. In addition
                # to that, different FS can have different file length support or may even change what the length
                # limit actually means in relation to the character encoding:
                #   - Windows counts the length limit in Unicode characters (as UTF-16 codepoints), having a limit of
                #     255 for NTFS, exFAT and FAT32, while having a lower limit on some other filesystems such as UDF.
                #   - macOS supports 255 Unicode characters with HFS+ similarly to Windows, but older or alternate
                #     filesystems may have more restrictive limits.
                #   - Linux counts the length limit as the encoded byte sequence up to 255 length in general.
                # So we truncate to sensible length in one go, then if that is still not acceptable we proceed by
                # a character each cycle with trial and error.
                if pre_len > suf_len:
                    prefix = prefix[:-1]
                    pre_len = self.fs_name_encode_length(prefix)
                elif suf_len > 0:
                    suffix = suffix[1:]
                    suf_len = self.fs_name_encode_length(suffix)
                if pre_len + suf_len + mk_len - 1 <= self.max_name_length:
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
