import os
import shutil
from collections import defaultdict

from setuptools import setup, find_packages

HERE = os.path.abspath(os.path.dirname(__file__))
VERSION = "0.10.0"

with open(os.path.join(HERE, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

requirements = defaultdict(list)
for name in os.listdir(os.path.join(HERE, "requirements")):
    if name not in ("base.in",):
        continue
    reqs = requirements[name.rpartition(".")[0]]
    with open(os.path.join(HERE, "requirements", name)) as f:
        for line in f:
            line = line.strip()
            if line.startswith("#") or line.startswith("-r"):
                continue
            reqs.append(line)
install_requirements = requirements.pop("base")


def _package_data_files(pkg: str, path: str = "", ignored_suffixes=(".py", ".pyc")):
    root = os.path.join(HERE, pkg)
    for parent, _, files in os.walk(os.path.join(root, path)):
        for file in files:
            if any(file.endswith(suffix) for suffix in ignored_suffixes):
                continue
            yield os.path.relpath(os.path.join(parent, file), root)


package_data = {"tarka": sorted(_package_data_files("tarka"))}
if package_data != {"tarka": []}:
    raise Exception(f"Package data has changed\n{str(package_data)}")

# Manually cleaning before build is required.
for p in [os.path.join(HERE, "build"), os.path.join(HERE, "dist"), os.path.join(HERE, "tarka.egg-info")]:
    if os.path.exists(p):
        shutil.rmtree(p)

setup(
    name="tarka",
    version=VERSION,
    description="Various things for common use, like a Swiss Army Knife.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Traktormaster/tarka",
    author="Nándor Mátravölgyi",
    author_email="nandor.matra@gmail.com",
    license="Apache 2.0",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: Implementation :: CPython",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
    ],
    packages=[p for p in find_packages(where=HERE, include=["tarka*"]) if not p.startswith("tarka_")],
    package_data=package_data,
    install_requires=install_requirements,
    extras_require=dict(requirements),
    python_requires=">=3.9",
)
