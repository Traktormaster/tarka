import argparse
import json
import sys
from pathlib import Path

from tarka.utility.importing import forward_import_recursively


def main():
    parser = argparse.ArgumentParser(prog="Forward import tester")
    parser.add_argument("import_path", help="Imports to gather the sources by.")
    parser.add_argument("output_path")
    args = parser.parse_args()

    pre = set(sys.modules.keys())
    forward_import_recursively(args.import_path)
    post = set(sys.modules.keys())

    Path(args.output_path).write_bytes(json.dumps(sorted(post.difference(pre))).encode("utf-8"))


if __name__ == "__main__":
    main()
