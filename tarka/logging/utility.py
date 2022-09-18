import os
from datetime import datetime
from pathlib import Path
from typing import Union

from tarka.utility.time.format import PRETTY_TIMESTAMP


def get_log_file_path(log_file_path: Union[str, Path]) -> Path:
    """
    Evaluate the selected path and prepare it to be a logging target.
    Expands the path if it has the user's home (~).
    If the path does not end with a name of '.log' extension, treat it as a target directory and generate a filename.
    Create intermediate directories if they do not exist, which may raise an OSError for various reasons.
    """
    if not isinstance(log_file_path, Path):
        log_file_path = Path(log_file_path)
    log_file_path = log_file_path.expanduser()
    if log_file_path.name.endswith(".log"):
        log_parent = log_file_path.parent
    else:
        log_parent = log_file_path
        log_file_path = log_parent / f"{PRETTY_TIMESTAMP.date_time_micro(datetime.now())}_{os.urandom(4).hex()}.log"
    log_parent.mkdir(parents=True, exist_ok=True)
    return log_file_path
