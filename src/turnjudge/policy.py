"""Policy: maps Jev's answers to pass | advise | block per file, and renders templated feedback.

All thresholds come from config. No prose from the model ever reaches the agent; every
string here is authored in this repo and only numbers, paths, and the task text fill the slots.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from turnjudge.questions import SCORE_LEVELS, SECURITY_IDS, score_top

OUTCOME_RANK = {"pass": 0, "advise": 1, "block": 2}

DEFAULT_THRESHOLDS: dict[str, float] = {
    "security_block": 0.85,
    "swallows_failure_block": 0.85,
    "swallows_failure_advise": 0.50,
    "unrequested_change_block": 0.80,
    "unnecessary_complexity_block": 0.70,
    "unnecessary_complexity_advise": 0.50,
    "complexity_score_gate": 2.0,
    "maintenance_advise": 2.2,
    "maintenance_confidence": 0.6,
    "verbosity_advise": 1.5,
    "tests_missing_advise": 0.3,
    "tests_behavior_gate": 2.0,
}


class Answers:
    """Accessor over a raw API response body (the same dict recorded in fixtures and audit)."""

    def __init__(self, raw: dict[str, Any]):
        self.raw = raw
        self.answers: dict[str, Any] = raw.get("answers", {})

    def noul(self, qid: str) -> float | None:
        a = self.answers.get(qid)
        return None if a is None or "noul" not in a else float(a["noul"])

    def score(self, qid: str) -> float | None:
        a = self.answers.get(qid)
        return None if a is None or "score" not in a else float(a["score"])

    def confidence(self, qid: str) -> float | None:
        a = self.answers.get(qid)
        return None if a is None or "confidence" not in a else float(a["confidence"])

    def flat(self) -> dict[str, float]:
        out: dict[str, float] = {}
        for qid, a in self.answers.items():
            if "noul" in a:
                out[qid] = round(float(a["noul"]), 3)
            elif "score" in a:
                out[qid] = round(float(a["score"]), 3)
                out[f"{qid}_conf"] = round(float(a.get("confidence", 0.0)), 3)
        return out


@dataclass
class Fired:
    rule: str
    outcome: str  # advise | block
    message: str


@dataclass
class FileVerdict:
    path: str
    outcome: str = "pass"
    fired: list[Fired] = field(default_factory=list)
    composite: float = 0.0
    values: dict[str, float] = field(default_factory=dict)


def _lvl(qid: str, v: float | None) -> str:
    if v is None:
        return "n/a"
    return f"{v:.1f}/{score_top(qid)}"


def _short_task(task: str, n: int = 80) -> str:
    t = " ".join((task or "").split())
    return t if len(t) <= n else t[: n - 1] + "…"


# ---- Feedback templates: fixed strings with slots ---------------------------------------------

T_SECURITY = {
    "introduces_secret": "turnjudge: `{path}` appears to add a hardcoded credential, token, or key (p={p:.2f}). "
                         "Read it from the environment or a key file instead, or explain in your reply why this value is not a secret.",
    "unsafe_input_use": "turnjudge: `{path}` appears to pass untrusted input to a shell, eval, SQL, a path, or a deserializer "
                        "without validation (p={p:.2f}). Validate, parameterize, or escape it, or explain in your reply why the input is trusted.",
    "weakens_check": "turnjudge: `{path}` appears to remove or loosen a validation, auth, TLS, or safety check (p={p:.2f}). "
                     "Restore an equivalent check, or explain in your reply why the check is no longer needed.",
    "new_external_surface": "turnjudge: `{path}` appears to add a new network call, dependency, or executable download (p={p:.2f}). "
                            "Task: \"{task}\". Confirm in your reply that this new external surface was asked for, or remove it.",
}
T_SWALLOWS = ("turnjudge: `{path}` appears to hide or swallow a failure that previously surfaced (p={p:.2f}). "
              "Let the failure surface again, or explain in your reply why silencing it is correct here.")
T_SWALLOWS_ADVISE = ("turnjudge (advisory): `{path}` may default away or silence a failure (p={p:.2f}). If a caller could "
                     "no longer tell that something went wrong, say so in your reply or narrow the handling to the case the task named.")
T_UNREQUESTED = ("turnjudge: `{path}` appears to change behavior that the task did not ask for and your summary does not "
                 "mention (p={p:.2f}). Task: \"{task}\". Either revert the extra change or state it explicitly in your reply.")
T_COMPLEXITY = ("turnjudge: `{path}` adds {what} (control flow {cf}, abstraction {ab}) that looks disproportionate to the "
                "behavior the task asked for (behavior {beh}, disproportion p={p:.2f}). Task: \"{task}\". Either simplify "
                "to an inline change or explain in your reply why the structure is needed.")
T_COMPLEXITY_ADVISE = ("turnjudge (advisory): `{path}` may carry more structure than the task needs (disproportion p={p:.2f}, "
                       "abstraction {ab}, control flow {cf}). Task: \"{task}\". Worth a second look before it settles in.")
T_MAINT = ("turnjudge (advisory): `{path}` is judged hard to modify safely later (maintenance risk {mr}, confidence {conf:.2f}). "
           "Consider reducing coupling or adding a short comment on why it is shaped this way.")
T_VERBOSITY = ("turnjudge (advisory): `{path}` carries padding beyond what the task needs (verbosity {vb}): boilerplate, "
               "comments restating code, or redundant checks. Consider trimming it.")
T_TESTS = ("turnjudge (advisory): `{path}` adds behavior (behavior {beh}) without tests proportional to it "
           "(tests_proportional p={p:.2f}). Add a test or say why none is needed.")
T_TOO_LARGE = ("turnjudge: this turn's delta was too large to judge reliably ({files} files, {bytes} bytes after redaction), "
               "so it was reviewed in advisory mode only.")
T_WITHHELD = "turnjudge: {n} file(s) were withheld from review by the redaction deny list: {paths}."


def decide_file(path: str, ans: Answers, thresholds: dict[str, float] | None = None,
                task: str = "") -> FileVerdict:
    t = {**DEFAULT_THRESHOLDS, **(thresholds or {})}
    v = FileVerdict(path=path, values=ans.flat())
    task_s = _short_task(task)

    def fire(rule: str, outcome: str, msg: str) -> None:
        v.fired.append(Fired(rule, outcome, msg))
        if OUTCOME_RANK[outcome] > OUTCOME_RANK[v.outcome]:
            v.outcome = outcome

    # Security: any Noul at or over the block threshold
    for qid in SECURITY_IDS:
        p = ans.noul(qid)
        if p is not None and p >= t["security_block"]:
            fire(qid, "block", T_SECURITY[qid].format(path=path, p=p, task=task_s))

    p = ans.noul("swallows_failure")
    if p is not None and p >= t["swallows_failure_block"]:
        fire("swallows_failure", "block", T_SWALLOWS.format(path=path, p=p))
    elif p is not None and p >= t["swallows_failure_advise"]:
        fire("swallows_failure", "advise", T_SWALLOWS_ADVISE.format(path=path, p=p))

    p = ans.noul("unrequested_behavior_change")
    if p is not None and p >= t["unrequested_change_block"]:
        fire("unrequested_behavior_change", "block", T_UNREQUESTED.format(path=path, p=p, task=task_s))

    # Disproportion is judged by the Noul itself relative to `task`; the Score gate only confirms that
    # real structure was added. No behavior gate: an over-built change still delivers the feature, so
    # behavior_added is not small (calibration/report.md, synthetic pairs, 2026-09-17).
    p = ans.noul("unnecessary_complexity")
    cf, ab, beh = ans.score("control_flow_added"), ans.score("abstraction_added"), ans.score("behavior_added")
    structure = ((cf is not None and cf >= t["complexity_score_gate"]) or (ab is not None and ab >= t["complexity_score_gate"]))
    if p is not None and p >= t["unnecessary_complexity_block"] and structure:
        what = "a new indirection layer" if (ab or 0) >= (cf or 0) else "nested control flow"
        fire("unnecessary_complexity", "block", T_COMPLEXITY.format(
            path=path, what=what, cf=_lvl("control_flow_added", cf), ab=_lvl("abstraction_added", ab),
            beh=_lvl("behavior_added", beh), p=p, task=task_s))
    elif p is not None and p >= t["unnecessary_complexity_advise"]:
        fire("unnecessary_complexity", "advise", T_COMPLEXITY_ADVISE.format(
            path=path, p=p, ab=_lvl("abstraction_added", ab), cf=_lvl("control_flow_added", cf), task=task_s))

    mr, mc = ans.score("maintenance_risk"), ans.confidence("maintenance_risk")
    if mr is not None and mr >= t["maintenance_advise"] and (mc or 0.0) >= t["maintenance_confidence"]:
        fire("maintenance_risk", "advise", T_MAINT.format(path=path, mr=_lvl("maintenance_risk", mr), conf=mc or 0.0))

    vb = ans.score("verbosity")
    if vb is not None and vb >= t["verbosity_advise"]:
        fire("verbosity", "advise", T_VERBOSITY.format(path=path, vb=_lvl("verbosity", vb)))

    tp = ans.noul("tests_proportional")
    if tp is not None and tp <= t["tests_missing_advise"] and beh is not None and beh >= t["tests_behavior_gate"]:
        fire("tests_proportional", "advise", T_TESTS.format(path=path, beh=_lvl("behavior_added", beh), p=tp))

    v.composite = composite(ans)
    return v


def composite(ans: Answers) -> float:
    """Dashboard score 0..1, higher is worse. Logged only; never drives a decision."""
    parts: list[float] = []
    for qid, w in (("maintenance_risk", 0.3), ("verbosity", 0.1), ("control_flow_added", 0.1),
                   ("abstraction_added", 0.1)):
        s = ans.score(qid)
        if s is not None:
            parts.append(w * s / score_top(qid))
    for qid, w in (("unnecessary_complexity", 0.2), ("swallows_failure", 0.1), ("unrequested_behavior_change", 0.1)):
        p = ans.noul(qid)
        if p is not None:
            parts.append(w * p)
    return round(sum(parts), 3)


def worst(verdicts: list[FileVerdict]) -> str:
    return max((v.outcome for v in verdicts), key=lambda o: OUTCOME_RANK[o], default="pass")


def apply_mode(outcome: str, mode: str) -> str:
    """Config mode caps the outcome: advise never blocks, off never says anything."""
    if mode == "off":
        return "pass"
    if mode == "advise" and outcome == "block":
        return "advise"
    return outcome


def render_feedback(verdicts: list[FileVerdict], *, blocking: bool) -> str:
    """Join the fired messages for the outcome level being delivered."""
    # Every fired rule is reported; `blocking` only changes the delivery channel. A block rule that is
    # downgraded (advise mode, too-large delta, subagent) still names its finding in the advisory.
    lines: list[str] = []
    for v in verdicts:
        for f in v.fired:
            lines.append(f.message if blocking or f.outcome == "advise" else f.message.replace("turnjudge:", "turnjudge (advisory):", 1))
    return "\n".join(lines)


def explain_table(verdicts: list[FileVerdict]) -> str:
    """Per-file answer table for --explain and the skill."""
    cols = ["behavior_added", "control_flow_added", "abstraction_added", "maintenance_risk", "verbosity",
            "unnecessary_complexity", "swallows_failure", "unrequested_behavior_change", "tests_proportional",
            *SECURITY_IDS]
    short = {"behavior_added": "beh", "control_flow_added": "cflow", "abstraction_added": "abstr",
             "maintenance_risk": "maint", "verbosity": "verb", "unnecessary_complexity": "unnec",
             "swallows_failure": "swall", "unrequested_behavior_change": "unreq", "tests_proportional": "tests",
             "introduces_secret": "secret", "unsafe_input_use": "input", "weakens_check": "weaken",
             "new_external_surface": "extsurf"}
    out = [f"{'file':<40} {'out':<7} " + " ".join(f"{short[c]:>7}" for c in cols)]
    for v in verdicts:
        row = f"{v.path[-40:]:<40} {v.outcome:<7} "
        row += " ".join(f"{v.values.get(c, float('nan')):>7.2f}" for c in cols)
        out.append(row)
        for f in v.fired:
            out.append(f"    {f.outcome}: {f.rule}")
    return "\n".join(out)
