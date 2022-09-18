import random
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import List

import pytest

from tarka.utility.time.utc import (
    utc_timestamp,
    utc_timestamp_delta,
    utc_datetime_from_timestamp,
    utc_datetime_delta,
    utc_timestamp_from_datetime,
    utc_seconds_until,
    utc_datetime_from_uuid,
    utc_timestamp_from_uuid,
    utc_datetime_from_string,
    utc_datetime,
)

_naive_utc_epoch_dt = datetime(1970, 1, 1, 0, 0)
_test_tz_pos = timezone(timedelta(seconds=random.randint(30 * 60, 47 * 30 * 60)))
_test_tz_neg = timezone(timedelta(seconds=-random.randint(30 * 60, 47 * 30 * 60)))
# list of (UUID1, UTC float, naive UTC dt)
_test_data: List[dict] = [
    {
        "uuid": uuid.UUID("13814000-1dd2-11b2-8000-000000000000"),  # contains UTC timestamp
        "utc_epoch": 0.0,  # UTC timestamp (unix)
    },
    {"uuid": uuid.UUID("82355918-2bd2-11eb-bec4-d45d64d4eb7a"), "utc_epoch": 1605946869.259292},
    {"uuid": uuid.UUID("2399f2ae-2bd9-11eb-b333-d45d64d4eb7a"), "utc_epoch": 1605949717.0121388},
]
for _td in _test_data:
    _td["naive_utc_dt"] = _naive_utc_epoch_dt + timedelta(seconds=_td["utc_epoch"])
    _td["utc_dt"] = _td["naive_utc_dt"].replace(tzinfo=timezone.utc)
    _td["naive_utc_dt_pos"] = _td["naive_utc_dt"] + _test_tz_pos.utcoffset(None)
    _td["utc_dt_pos"] = _td["naive_utc_dt_pos"].replace(tzinfo=_test_tz_pos)
    _td["naive_utc_dt_neg"] = _td["naive_utc_dt"] + _test_tz_neg.utcoffset(None)
    _td["utc_dt_neg"] = _td["naive_utc_dt_neg"].replace(tzinfo=_test_tz_neg)

    _td["pos_epoch"] = _td["utc_epoch"] + _test_tz_pos.utcoffset(None).total_seconds()
    _td["naive_pos_dt"] = _naive_utc_epoch_dt + timedelta(seconds=_td["pos_epoch"])
    _td["pos_dt"] = (_td["naive_pos_dt"] + _test_tz_pos.utcoffset(None)).replace(tzinfo=_test_tz_pos)

    _td["neg_epoch"] = _td["utc_epoch"] + _test_tz_neg.utcoffset(None).total_seconds()
    _td["naive_neg_dt"] = _naive_utc_epoch_dt + timedelta(seconds=_td["neg_epoch"])
    _td["neg_dt"] = (_td["naive_neg_dt"] + _test_tz_neg.utcoffset(None)).replace(tzinfo=_test_tz_neg)


def test_utc_timestamp():
    # all of these should be the utc timestamp consistently
    assert abs(time.time() - utc_timestamp()) < 1
    assert abs(datetime.now(timezone.utc).timestamp() - utc_timestamp()) < 1


def test_utc_timestamp_delta():
    for _ in range(10):
        r = random.randint(-50000, 50000)
        assert abs(utc_timestamp_delta(r) - (time.time() + r)) < 0.1


def test_utc_timestamp_from_datetime():
    t = time.time()
    assert utc_timestamp_from_datetime(utc_datetime_from_timestamp(t)) == round(t, 6)
    assert abs(utc_timestamp_from_datetime(datetime.utcnow()) - time.time()) < 0.1
    assert abs(utc_timestamp_from_datetime(datetime.now().astimezone()) - time.time()) < 0.1

    iso_dt = "2018-09-15T11:25:37+02:00"
    dt_in_local = datetime.fromisoformat(iso_dt)
    assert dt_in_local.utcoffset() == timedelta(seconds=7200)
    ts_epoch_utc = utc_timestamp_from_datetime(dt_in_local)
    assert dt_in_local.timestamp() == ts_epoch_utc
    dt_in_utc = utc_datetime_from_timestamp(ts_epoch_utc)
    assert dt_in_utc.utcoffset() == timedelta(seconds=0)
    assert dt_in_local == dt_in_utc


def test_utc_datetime():
    # all of these should be the utc timestamp consistently
    assert abs(time.time() - utc_datetime().timestamp()) < 1
    assert abs(datetime.now(timezone.utc) - utc_datetime()).total_seconds() < 1


def test_utc_datetime_epoch_delta():
    for _ in range(10):
        r = random.randint(-50000, 50000)
        assert abs(utc_datetime_delta(r).timestamp() - (time.time() + r)) < 0.1


def test_utc_datetime_from_uuid():
    assert abs(utc_timestamp_from_datetime(utc_datetime_from_uuid(uuid.uuid1())) - time.time()) < 0.1


def test_utc_datetime_functions():
    assert (datetime.now(timezone.utc) - datetime(*time.gmtime()[:6], tzinfo=timezone.utc)).total_seconds() < 1
    assert abs((datetime.now().astimezone() - datetime.now(timezone.utc)).total_seconds()) < 0.01
    for td in _test_data:
        # consistency checks
        assert td["pos_epoch"] > td["utc_epoch"]
        assert td["naive_pos_dt"] > td["naive_utc_dt"]
        assert td["pos_dt"] > td["utc_dt"]

        assert td["utc_epoch"] > td["neg_epoch"]
        assert td["naive_neg_dt"] < td["naive_utc_dt"]
        assert td["neg_dt"] < td["utc_dt"]

        # uuid
        assert utc_timestamp_from_uuid(td["uuid"]) == td["utc_epoch"]
        assert utc_datetime_from_uuid(td["uuid"]) == td["utc_dt"]
        assert utc_datetime_from_uuid(td["uuid"]).utcoffset().total_seconds() == 0

        # arith
        assert (td["utc_dt"] - td["utc_dt_pos"]).total_seconds() == 0.0
        assert (td["utc_dt"] - td["utc_dt_neg"]).total_seconds() == 0.0
        assert (td["utc_dt_neg"] - td["utc_dt_pos"]).total_seconds() == 0.0

        # to datetime: utc epoch -> utc dt will match associated dts
        assert utc_datetime_from_timestamp(td["utc_epoch"]).utcoffset().total_seconds() == 0
        assert utc_datetime_from_timestamp(td["utc_epoch"]) == td["utc_dt"]
        assert utc_datetime_from_timestamp(td["utc_epoch"]) == td["utc_dt_pos"]
        assert utc_datetime_from_timestamp(td["utc_epoch"]) == td["utc_dt_neg"]
        assert utc_timestamp_from_datetime(td["utc_dt"]) == round(td["utc_epoch"], 6)
        assert utc_timestamp_from_datetime(td["utc_dt_pos"]) == round(td["utc_epoch"], 6)
        assert utc_timestamp_from_datetime(td["utc_dt_neg"]) == round(td["utc_epoch"], 6)

        # to datetime: pos epoch
        assert utc_datetime_from_timestamp(td["pos_epoch"]).utcoffset().total_seconds() == 0
        assert utc_datetime_from_timestamp(td["pos_epoch"]) == td["pos_dt"]
        assert utc_timestamp_from_datetime(td["pos_dt"]) == round(td["pos_epoch"], 6)
        assert utc_datetime_from_timestamp(td["pos_epoch"]) == td["utc_dt"] + _test_tz_pos.utcoffset(None)
        assert utc_datetime_from_timestamp(td["pos_epoch"]) == td["utc_dt_pos"] + _test_tz_pos.utcoffset(None)
        assert utc_datetime_from_timestamp(td["pos_epoch"]) == td["utc_dt_neg"] + _test_tz_pos.utcoffset(None)

        # to datetime: neg epoch
        assert utc_datetime_from_timestamp(td["neg_epoch"]).utcoffset().total_seconds() == 0
        assert utc_datetime_from_timestamp(td["neg_epoch"]) == td["neg_dt"]
        assert utc_timestamp_from_datetime(td["neg_dt"]) == round(td["neg_epoch"], 6)
        assert utc_datetime_from_timestamp(td["neg_epoch"]) == td["utc_dt"] + _test_tz_neg.utcoffset(None)
        assert utc_datetime_from_timestamp(td["neg_epoch"]) == td["utc_dt_pos"] + _test_tz_neg.utcoffset(None)
        assert utc_datetime_from_timestamp(td["neg_epoch"]) == td["utc_dt_neg"] + _test_tz_neg.utcoffset(None)


def test_utc_datetime_from_string():
    for s, v in [
        ("2017-05-26T11:30:14.123456+0100", datetime(2017, 5, 26, 11, 30, 14, 123456, timezone(timedelta(hours=1)))),
        ("1987-01-01 20:59:59-0100", datetime(1987, 1, 1, 20, 59, 59, 0, timezone(timedelta(hours=-1)))),
        ("1987-01-01 20:59:59-071024.75", datetime(1987, 1, 1, 20, 59, 59, 0, timezone(timedelta(seconds=-25824.75)))),
        (
            "1987-01-01T00:00:00.01-071024.00550",
            datetime(1987, 1, 1, 0, 0, 0, 10000, timezone(timedelta(seconds=-25824.0055))),
        ),
        (
            "2112-01-01T00:00:00.0101+07:10:24.03050",
            datetime(2112, 1, 1, 0, 0, 0, 10100, timezone(timedelta(seconds=25824.0305))),
        ),
        ("2112-01-01T00:00:00.0101", datetime(2112, 1, 1, 0, 0, 0, 10100, timezone.utc)),
        ("2110-01-21T00:00:01", datetime(2110, 1, 21, 0, 0, 1, 0, timezone.utc)),
        ("2020-11-21T14:10:31.700Z", datetime(2020, 11, 21, 14, 10, 31, 700000, timezone.utc)),
    ]:
        dt = utc_datetime_from_string(s)
        assert dt == v, f"dt error\nfrom: {s}\nto  : {v}\nres : {dt}"
        assert dt.utcoffset().total_seconds() == 0
    for _ in range(10):
        t = utc_timestamp_delta(random.randint(-100000, 100000))
        assert abs(utc_datetime_from_timestamp(t).timestamp() - t) < 0.1
        assert abs(utc_datetime_from_string(utc_datetime_from_timestamp(t).isoformat()).timestamp() - t) < 0.1
        assert datetime.fromtimestamp(t, timezone.utc) == utc_datetime_from_timestamp(t)
        assert datetime.fromtimestamp(t) != datetime.fromtimestamp(t, timezone.utc)
        assert datetime.fromtimestamp(t) != utc_datetime_from_timestamp(t)
    with pytest.raises(ValueError, match="invalid datetime for parse:"):
        utc_datetime_from_string("asdf")
    with pytest.raises(ValueError, match="invalid tz hours for parse:"):
        utc_datetime_from_string("2112-01-01T00:00:00.0101+25:10:24.03050")
    with pytest.raises(ValueError, match="invalid tz minutes for parse:"):
        utc_datetime_from_string("2112-01-01T00:00:00.0101+07:60:24.03050")
    with pytest.raises(ValueError, match="invalid tz seconds for parse:"):
        utc_datetime_from_string("2112-01-01T00:00:00.0101+07:10:60.03050")


def test_utc_seconds_until():
    assert abs(utc_seconds_until(time.time())) <= 1
    assert abs(utc_seconds_until(time.time() + 61) - 61) <= 1
    assert abs(utc_seconds_until(time.time() - 61) + 61) <= 1


@pytest.mark.skipif(
    datetime.now().astimezone().utcoffset() == 0,
    reason="Requires the timezone of the system to not match with UTC.",
)
def test_utc_datetime_now():
    """
    This is a small research to make a summary of how to use the datetime.<utc>now() methods.

    The simple rules to keep you sane when working with datetime objects: (especially in a server environment)
        1. Always create them in timezone aware mode with datetime.now(tz)
        2. If (1) is true then dt.timestamp() is always utc unix epoch
        3. Only use datetime.utcnow() for comparing to naive dt objects that are surely in utc. For example Timestamp
           columns queried from Cassandra return naive utc timestamps. Alternatively the tz info of an utc datetime
           can be dropped with datetime.replace(tz_info=None) to make it naive for comparison's sake.
        4. Tz aware local time can be created with datetime.now().astimezone()

    """
    local_tz = datetime.now().astimezone().tzinfo
    local_offset = local_tz.utcoffset(None).total_seconds()
    assert abs((datetime.now() - datetime.now(local_tz).replace(tzinfo=None)).total_seconds()) < 0.01

    # === NAIVE LOCAL DATETIME ===
    # converting to unix timestamp IS utc timestamp
    assert abs(datetime.now().timestamp() - time.time()) < 0.01
    # datetime components of this is in local time (it cannot be anything else because it is naive)

    # === NAIVE UTC DATETIME ===
    # converting to unix timestamp IS NOT utc timestamp
    # (naive is assumed to be local so it gets offset in the opposite direction of the timezone)
    assert abs(datetime.utcnow().timestamp() - (time.time() - local_offset)) < 0.01
    # datetime components of this is in utc time (it cannot be anything else because it is naive)

    # === AWARE DATETIME ===
    # converting to unix timestamp IS utc timestamp
    assert abs(datetime.now(timezone.utc).timestamp() - time.time()) < 0.01
    # datetime components of this is can be any time of the day because it is aware

    # Use this snippet to observe how they are expressing the time.
    # print("naive local", (d := datetime.now()).isoformat(), d.timestamp())
    # print("naive utc  ", (d := datetime.utcnow()).isoformat(), d.timestamp())
    # print("aware local", (d := datetime.now(local_tz)).isoformat(), d.timestamp())
    # print("aware utc  ", (d := datetime.now(timezone.utc)).isoformat(), d.timestamp())
    # assert False, "times are interesting"
