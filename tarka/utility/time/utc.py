"""
These are prepared for use in a server environment, where using local time is undesired.
All datetime objects returned are in UTC offset zero.
All timestamps are considered to be in UNIX epoch format.
"""
import re
import sys
import time
from datetime import datetime, timezone, timedelta
from uuid import UUID

ISO_DATETIME_RE = re.compile(
    r"^(\d{4})-(\d\d)-(\d\d)[T ](\d\d):(\d\d):(\d\d)(?:\.(\d{1,6}))?"
    r"(?:Z|([+-])(\d\d):?(\d\d):?(\d\d)?(?:\.(\d{1,6}))?)?$"
)


if sys.platform.startswith("win"):
    # NOTE: The C backend of fromtimestamp on Windows does not handle ranges before the epoch and farther in the
    # future, so... don't use it. Luckily the datetime facility in python can  bu used instead easily.
    def _dt_fromtimestamp(t, tz=None) -> datetime:
        return datetime.fromtimestamp(0, tz) + timedelta(seconds=t)

else:
    _dt_fromtimestamp = datetime.fromtimestamp


def utc_timestamp() -> float:
    """
    Current UTC time.
    In Python time.time() calls the time C function.
    On Linux, macOS, Windows the epoch is 1970-1-1, 00:00 UTC, and is timezone-independent.
    """
    return time.time()


def utc_timestamp_delta(offset_seconds: float) -> float:
    """
    Get the current timestamp with some offset.
    """
    return time.time() + offset_seconds


def utc_timestamp_from_datetime(dt: datetime) -> float:
    """
    This function flips the convention of assuming non-aware datetime to be in local time.
    On the server side if a remote request does not specify the timezone, assuming our timezone cannot be
    more correct than assuming the remote point to at least speak a common language, just badly.
    """
    if dt.utcoffset() is not None:
        return dt.timestamp()
    return dt.replace(tzinfo=timezone.utc).timestamp()


def utc_timestamp_from_uuid(uuid1: UUID) -> float:
    """
    The timestamp inside a UUID version 1 is not in UNIX epoch format, so we convert it to that.
    """
    return (uuid1.time - 0x01B21DD213814000) * 1e-07


def utc_datetime() -> datetime:
    """
    Current UTC time.
    Equivalent to calling: datetime.now(timezone.utc)
    """
    return _dt_fromtimestamp(time.time(), timezone.utc)


def utc_datetime_delta(offset_seconds: float) -> datetime:
    """
    Get the current timestamp with some offset.
    """
    return _dt_fromtimestamp(time.time() + offset_seconds, timezone.utc)


def utc_datetime_from_timestamp(utc_epoch_timestamp: float) -> datetime:
    """
    Convert the UTC timestamp to an UTC datetime.
    """
    return _dt_fromtimestamp(utc_epoch_timestamp, timezone.utc)


def utc_datetime_from_uuid(uuid1: UUID) -> datetime:
    """
    Convenience wrapper to get the timestamp of an UUID1 as datetime.
    """
    return _dt_fromtimestamp(utc_timestamp_from_uuid(uuid1), timezone.utc)


def utc_datetime_from_string(s: str) -> datetime:
    """
    Because datetime.strptime() can only handle a single static format, we regexp-process the input and construct
    the datetime object ourselves.
    """
    m = ISO_DATETIME_RE.match(s)
    if m is None:
        raise ValueError(f"invalid datetime for parse: {s}")
    groups = m.groups("0")
    # parse tz from timedelta
    if not (0 <= (tz_hours := int(groups[8])) < 24):
        raise ValueError(f"invalid tz hours for parse: {s}")
    if not (0 <= (tz_minutes := int(groups[9])) < 60):
        raise ValueError(f"invalid tz minutes for parse: {s}")
    if not (0 <= (tz_seconds := int(groups[10])) < 60):
        raise ValueError(f"invalid tz seconds for parse: {s}")
    tz_microseconds = int(groups[11] + "0" * (6 - len(groups[11])))
    tz_delta = timedelta(hours=tz_hours, minutes=tz_minutes, seconds=tz_seconds, microseconds=tz_microseconds)
    dt = datetime(
        int(groups[0]),
        int(groups[1]),
        int(groups[2]),
        int(groups[3]),
        int(groups[4]),
        int(groups[5]),
        int(groups[6] + "0" * (6 - len(groups[6]))) if groups[6] else 0,
        timezone.utc,
    )
    if groups[7] == "-":
        return dt + tz_delta
    return dt - tz_delta


def utc_seconds_until(utc_epoch_timestamp: float) -> float:
    return utc_epoch_timestamp - time.time()
