from datetime import datetime, timezone, timedelta

from tarka.utility.time.format import PRETTY_TIMESTAMP, PrettyTimestamp


def test_pretty_timestamp_default():
    for arg, s in [
        (1657206380.2571106, "220707150620257111"),
        (1657206380, "220707150620000000"),
        (datetime.fromtimestamp(1657206380.2571106, timezone(timedelta(seconds=7200))), "220707170620257111"),
    ]:
        assert PRETTY_TIMESTAMP.date(arg) == s[:6], f"{arg} {s}"
        assert PRETTY_TIMESTAMP.time(arg) == s[6:12], f"{arg} {s}"
        assert PRETTY_TIMESTAMP.date_time(arg) == s[:12], f"{arg} {s}"
        assert PRETTY_TIMESTAMP.date_time_milli(arg) == s[:-3], f"{arg} {s}"
        assert PRETTY_TIMESTAMP.date_time_micro(arg) == s, f"{arg} {s}"


def test_pretty_timestamp_custom():
    t = 1657206380.2571106
    assert PrettyTimestamp(datetime_sep=":", ms_sep=".").date_time_milli(t) == "220707:150620.257"
    assert PrettyTimestamp(datetime_sep=":", ms_sep=".").date_time_micro(t) == "220707:150620.257111"
