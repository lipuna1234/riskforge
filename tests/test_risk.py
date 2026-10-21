import pytest

from riskforge.risk import DailyLossGuard, calculate_position_quantity


def test_quantity_respects_notional_cap():
    qty = calculate_position_quantity(1000, 100, 90, fee_rate=0.001,
                                      risk_fraction=0.01, max_position_fraction=0.25)
    assert qty * 100 <= 250
    assert qty > 0


def test_quantity_rejects_invalid_stop():
    with pytest.raises(ValueError):
        calculate_position_quantity(1000, 100, 101)


def test_daily_guard_halts_at_limit():
    guard = DailyLossGuard(0.03)
    guard.new_day(1000)
    assert not guard.update(980)
    assert guard.update(970)
