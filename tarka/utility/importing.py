import os
import sys
import warnings
from importlib import import_module
from importlib.machinery import EXTENSION_SUFFIXES, SOURCE_SUFFIXES, BYTECODE_SUFFIXES
from importlib.util import spec_from_file_location, module_from_spec
from itertools import chain
from types import ModuleType
from typing import Sequence, Optional
from urllib.parse import quote


def forward_import_recursively(package_module_path: str, skip_dir_names: Sequence[str] = ("__pycache__",)):
    """
    This can be utilized to load plugin-like solutions and structures that utilize subclass-hook for example.
    """
    package_init = import_module(package_module_path).__file__
    package_dir_path = os.path.dirname(package_init)
    if os.path.splitext(os.path.basename(package_init))[0] != "__init__" or not os.path.isdir(package_dir_path):
        return  # Imported module is not a traditional python package (directory with __init__ module)
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


class IsolatedPackageImport:
    """
    This can be used to import modules on an arbitrary absolute path and have them all under an isolated package if
    they are imported with relative paths.
    """

    @classmethod
    def create(cls, root_module_path: str):
        # create fake package (for relative imports)
        package_name = "__main__" + quote(root_module_path, safe="").replace(".", "_")
        package_module = ModuleType(package_name)
        package_module.__path__ = [os.path.dirname(root_module_path)]
        package_module.__file__ = os.path.join(package_module.__path__[0], "__init__.py")
        sys.modules[package_name] = package_module
        try:
            # import main module under fake package
            module_name = package_name + "." + os.path.basename(root_module_path).rpartition(".")[0]
            spec = spec_from_file_location(module_name, root_module_path)
            main_module = module_from_spec(spec)
            sys.modules[module_name] = main_module
            try:
                spec.loader.exec_module(main_module)
            except:
                del sys.modules[module_name]
                raise
        except:
            del sys.modules[package_name]
            raise
        return cls(package_name, main_module)

    def __init__(self, pacakge_name: str, module: ModuleType):
        self.package_name = pacakge_name
        self.module = module

    def unload(self):
        # NOTE: This only ensures that a subsequent import will be clean, provided that all submodules were imported
        # with relative imports.
        for k in list(sys.modules.keys()):
            if k.startswith(self.package_name):
                if len(k) == len(self.package_name) or k[len(self.package_name)] == ".":
                    del sys.modules[k]
