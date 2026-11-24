from datetime import datetime, timedelta, timezone

from app.services.otp_service import _as_naive_utc, _utcnow


def test_utcnow_is_naive_utc():
    now = _utcnow()
    assert now.tzinfo is None
    assert abs((now - datetime.now(timezone.utc).replace(tzinfo=None)).total_seconds()) < 2


def test_as_naive_utc_converts_aware_values():
    madagascar = timezone(timedelta(hours=3))
    assert _as_naive_utc(datetime(2026, 11, 14, 8, 1, 13, tzinfo=madagascar)) == datetime(2026, 11, 14, 5, 1, 13)
    assert _as_naive_utc(datetime(2026, 11, 14, 5, 1, 13)) == datetime(2026, 11, 14, 5, 1, 13)
