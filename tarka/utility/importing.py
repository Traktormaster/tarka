import os
import warnings
from importlib import import_module
from importlib.machinery import EXTENSION_SUFFIXES, SOURCE_SUFFIXES, BYTECODE_SUFFIXES
from itertools import chain
from types import ModuleType
from typing import Sequence, Optional


def forward_import_recursively(package_module_path: str, skip_dir_names: Sequence[str] = ("__pycache__",)):
    """
    This can be utilized to load plugin-like solutions and structures that utilize subclass-hook for example.
    """
    package_init = import_module(package_module_path).__file__
    if os.path.splitext(os.path.basename(package_init))[0] != "__init__":
        raise Exception(f"Failed forward import for {package_module_path}")
    package_dir_path = os.path.dirname(package_init)
    for root, dirs, files in os.walk(package_dir_path):
        if os.path.basename(root) in skip_dir_names:
            continue
        imp_root = package_module_path
        sub_path = root[len(package_dir_path) + 1 :]
        if sub_path:
            imp_root = ".".join([imp_root, *sub_path.split(os.path.sep)])
        for file in files:
            if os.path.splitext(file)[0] == "__init__":
                continue
            for suffix in chain(SOURCE_SUFFIXES, BYTECODE_SUFFIXES, EXTENSION_SUFFIXES):
                if file.endswith(suffix):
                    import_module(f"{imp_root}.{file[:-len(suffix)]}")
        for dir_ in dirs:
            if dir_ in skip_dir_names:
                continue
            if any(
                os.path.isfile(os.path.join(root, dir_, f"__init__{suffix}"))
                for suffix in chain(SOURCE_SUFFIXES, BYTECODE_SUFFIXES)
            ):
                import_module(f"{imp_root}.{dir_}")


def import_optional(import_path: str, warn_error: bool = True) -> Optional[ModuleType]:
    try:
        return import_module(import_path)
    except ImportError:
        if warn_error:
            warnings.warn(f"Can't import optional {import_path}")
