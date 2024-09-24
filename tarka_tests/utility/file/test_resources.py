import os
from pathlib import Path

import pytest

from tarka.utility.file.resources import ResourcesFolder, ResourcesFolderError
from tarka_tests.utility.file.resources import RESOURCES

HERE = os.path.dirname(os.path.abspath(__file__))


def test_file_resources_folder():
    rp = Path(HERE).joinpath("resources")
    assert RESOURCES.path == rp
    assert RESOURCES.join("file.txt") == str(rp / "file.txt")
    assert ResourcesFolder(HERE).path == rp
    with pytest.raises(
        ResourcesFolderError, match=r"^Resources folder must be a subdirectory under the root directory: "
    ):
        ResourcesFolder(HERE, "..")
    with pytest.raises(ResourcesFolderError, match=r"^Resources folder is not a directory: "):
        ResourcesFolder(HERE, "asdf")
    with pytest.raises(
        ResourcesFolderError, match=r"^Resources folder must not be a python package to avoid ambiguity: "
    ):
        ResourcesFolder(HERE, ".")
