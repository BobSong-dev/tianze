import pytest

from tianze.calendar.time_resolution import resolve_time
from tianze.domain.models import BirthInfo


@pytest.mark.parametrize("mode", ["clock", "mean_solar", "true_solar"])
def test_report_mode_matches_actual_pillar_clock(mode):
    birth = BirthInfo.model_validate({"date": "2003-08-18", "time": "14:30", "longitude": 87.6, "timeAlg": mode})
    resolution, warnings = resolve_time(birth)
    assert resolution.effective_mode == "clock"
    assert resolution.pillar_dt == resolution.local_clock
    assert any("太阳时校正尚未启用" in warning for warning in warnings) == (mode != "clock")
