from aao.planner import Admission, decide_admission


BASE = dict(
    project_active=True, mandate_confirmed=True, authorized=True,
    dependencies_satisfied=True, capacity_available=True, within_budget=True,
    residual_risk="low", emergency_stop=False,
)


def test_admission_permits_only_fully_authorized_work():
    assert decide_admission(**BASE).status == Admission.READY
    for field, value, expected in [
        ("emergency_stop", True, Admission.DENY),
        ("mandate_confirmed", False, Admission.DENY),
        ("authorized", False, Admission.DENY),
        ("project_active", False, Admission.DEFER),
        ("dependencies_satisfied", False, Admission.DEFER),
        ("capacity_available", False, Admission.DEFER),
        ("within_budget", False, Admission.DEFER),
        ("residual_risk", "high", Admission.DEFER),
        ("residual_risk", "unknown", Admission.DENY),
    ]:
        assert decide_admission(**{**BASE, field: value}).status == expected
