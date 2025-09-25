from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from fmi_cli.api import _mk_limits

HEL = ZoneInfo("Europe/Helsinki")


def test_mk_limits_works_without_tz():
    """Results contain at most 168 observations even when offset changes"""
    start_time = datetime(2014, 10, 23, 15, tzinfo=HEL)
    end_time = datetime(2014, 10, 30, 18, tzinfo=HEL)
    resolution = timedelta(hours=1)
    max_query_size = 168
    for s, e in _mk_limits(start_time, end_time, resolution):
        assert (e.timestamp() - s.timestamp()) / 3600 <= max_query_size
