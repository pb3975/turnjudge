"""Every rule fires and does not fire at its boundary; every template slot fills."""
import pytest

from turnjudge.policy import (Answers, DEFAULT_THRESHOLDS, apply_mode, composite, decide_file, explain_table,
                               render_feedback, worst)
from tests.conftest import fake_answers

T = DEFAULT_THRESHOLDS


def verdict(**over):
    return decide_file("src/x.py", Answers({"answers": fake_answers(**over)}), T, task="fix the nil deref in resume")


def rules(v):
    return [f.rule for f in v.fired]


def test_clean_passes():
    v = verdict()
    assert v.outcome == "pass" and v.fired == []


@pytest.mark.parametrize("q", ["introduces_secret", "unsafe_input_use", "weakens_check", "new_external_surface"])
def test_security_boundary(q):
    assert verdict(**{q: T["security_block"]}).outcome == "block"
    assert verdict(**{q: T["security_block"] - 0.001}).outcome == "pass"


def test_swallows_boundary():
    assert rules(verdict(swallows_failure=T["swallows_failure_block"])) == ["swallows_failure"]
    assert verdict(swallows_failure=T["swallows_failure_block"] - 0.01).outcome == "pass"


def test_unrequested_boundary():
    assert verdict(unrequested_behavior_change=T["unrequested_change_block"]).outcome == "block"
    assert verdict(unrequested_behavior_change=T["unrequested_change_block"] - 0.01).outcome == "pass"


def test_complexity_needs_all_three_conditions():
    base = dict(unnecessary_complexity=T["unnecessary_complexity_block"], abstraction_added=2.0, behavior_added=1.0)
    assert rules(verdict(**base)) == ["unnecessary_complexity"]
    assert verdict(**{**base, "unnecessary_complexity": 0.79}).outcome == "pass"
    assert verdict(**{**base, "abstraction_added": 1.9}).outcome == "pass"
    assert verdict(**{**base, "behavior_added": 1.1}).outcome == "pass"
    assert rules(verdict(**{**base, "abstraction_added": 0.0, "control_flow_added": 2.0})) == ["unnecessary_complexity"]


def test_maintenance_advise_needs_confidence():
    assert verdict(maintenance_risk=(2.2, 0.6)).outcome == "advise"
    assert verdict(maintenance_risk=(2.2, 0.59)).outcome == "pass"
    assert verdict(maintenance_risk=(2.19, 0.9)).outcome == "pass"


def test_verbosity_advise():
    assert rules(verdict(verbosity=1.5)) == ["verbosity"]
    assert verdict(verbosity=1.49).outcome == "pass"


def test_tests_advise_needs_behavior():
    assert rules(verdict(tests_proportional=0.3, behavior_added=2.0)) == ["tests_proportional"]
    assert verdict(tests_proportional=0.31, behavior_added=2.0).outcome == "pass"
    assert verdict(tests_proportional=0.1, behavior_added=1.9).outcome == "pass"


def test_block_beats_advise_and_worst():
    v = verdict(swallows_failure=0.9, verbosity=2.0)
    assert v.outcome == "block" and set(rules(v)) == {"swallows_failure", "verbosity"}
    assert worst([verdict(), v]) == "block"
    assert worst([]) == "pass"


def test_missing_answers_do_not_fire():
    v = decide_file("x", Answers({"answers": {}}), T)
    assert v.outcome == "pass" and v.composite == 0.0


def test_apply_mode():
    assert apply_mode("block", "advise") == "advise"
    assert apply_mode("advise", "off") == "pass"
    assert apply_mode("block", "block") == "block"


def test_templates_fill_every_slot():
    v = verdict(introduces_secret=0.9, unsafe_input_use=0.9, weakens_check=0.9, new_external_surface=0.9,
                swallows_failure=0.9, unrequested_behavior_change=0.9, unnecessary_complexity=0.9,
                abstraction_added=2.6, behavior_added=0.8, maintenance_risk=(2.5, 0.8), verbosity=1.8,
                tests_proportional=0.1)
    assert len(v.fired) == 9  # tests rule needs behavior >= 2, which the complexity rule needs <= 1
    text = render_feedback([v], blocking=True)
    assert "{" not in text and "}" not in text
    assert "`src/x.py`" in text and "fix the nil deref" in text and "abstraction 2.6/3" in text and "behavior 0.8/3" in text
    assert render_feedback([v], blocking=False).count("advisory") == 9  # every fired rule is reported when delivered as advice
    table = explain_table([v])
    assert "src/x.py" in table and "block" in table


def test_composite_is_bounded():
    assert 0 <= composite(Answers({"answers": fake_answers()})) <= 1
    assert composite(Answers({"answers": fake_answers(maintenance_risk=3.0, verbosity=2.0, control_flow_added=3.0,
                                                      abstraction_added=3.0, unnecessary_complexity=1.0,
                                                      swallows_failure=1.0, unrequested_behavior_change=1.0)})) == 1.0
