from datetime import datetime
from typing import Union

from tarka.utility.time.utc import utc_datetime_from_timestamp


class PrettyTimestamp:
    """
    Timestamps that are human readable, concise, constant-width, with no special characters by default.
    Timezone information is omitted. The same tz should be used in the same context to avoid ambiguity.
    """

    __slots__ = ("_date", "_time", "_date_time", "_date_time_ms")

    def __init__(self, date: str = "%y%m%d", time: str = "%H%M%S", datetime_sep: str = "", ms_sep: str = ""):
        self._date = date
        self._time = time
        self._date_time = f"{date}{datetime_sep}{time}"
        self._date_time_ms = f"{date}{datetime_sep}{time}{ms_sep}%f"

    def date(self, dt: Union[datetime, float, int]) -> str:
        if not isinstance(dt, datetime):
            dt = utc_datetime_from_timestamp(dt)
        return dt.strftime(self._date)

    def time(self, dt: Union[datetime, float, int]) -> str:
        if not isinstance(dt, datetime):
            dt = utc_datetime_from_timestamp(dt)
        return dt.strftime(self._time)

    def date_time(self, dt: Union[datetime, float, int]) -> str:
        if not isinstance(dt, datetime):
            dt = utc_datetime_from_timestamp(dt)
        return dt.strftime(self._date_time)

    def date_time_milli(self, dt: Union[datetime, float, int]) -> str:
        if not isinstance(dt, datetime):
            dt = utc_datetime_from_timestamp(dt)
        return dt.strftime(self._date_time_ms)[:-3]

    def date_time_micro(self, dt: Union[datetime, float, int]) -> str:
        if not isinstance(dt, datetime):
            dt = utc_datetime_from_timestamp(dt)
        return dt.strftime(self._date_time_ms)


PRETTY_TIMESTAMP = PrettyTimestamp()  # default global instance for ease of use
