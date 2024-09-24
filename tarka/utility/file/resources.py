from importlib.machinery import SOURCE_SUFFIXES, BYTECODE_SUFFIXES
from itertools import chain
from pathlib import Path
from typing import Union


class ResourcesFolderError(Exception):
    pass


class ResourcesFolder:
    """
    A simple and universal utility to access data files in python packages.
    The only restriction is for the files to be in a separate folder that is not a python package. (for clarity)
    """

    __slots__ = ("path",)

    DEFAULT_DIR = "resources"

    def __init__(self, root_path: Union[Path, str], rel_dir_path: str = None):
        root_path = Path(root_path)
        self.path = root_path.joinpath(rel_dir_path or self.DEFAULT_DIR).resolve()
        if not self.path.is_dir():
            raise ResourcesFolderError(f"Resources folder is not a directory: {self.path}")
        try:
            self.path.relative_to(root_path)
        except ValueError:
            raise ResourcesFolderError(f"Resources folder must be a subdirectory under the root directory: {self.path}")
        if any((self.path / f"__init__{suffix}").exists() for suffix in chain(SOURCE_SUFFIXES, BYTECODE_SUFFIXES)):
            raise ResourcesFolderError(f"Resources folder must not be a python package to avoid ambiguity: {self.path}")

    def join_path(self, *parts: str) -> Path:
        return self.path.joinpath(*parts)

    def join(self, *parts: str) -> str:
        return str(self.join_path(*parts))
