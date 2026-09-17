"""Live smoke: one real request per question type. Skipped without a key."""
import os
from pathlib import Path

import pytest

from jev_review.client import KEY_FILE, JevClient, KeyError_, load_key
from jev_review.questions import questions

pytestmark = pytest.mark.skipif(
    os.environ.get("JEV_REVIEW_LIVE") != "1" or (not os.environ.get("TYPESAFE_API_KEY") and not KEY_FILE.is_file()),
    reason="set JEV_REVIEW_LIVE=1 and provide a key to run live",
)


def test_live_all_question_types():
    try:
        load_key()
    except KeyError_:
        pytest.skip("no key")
    state = {"task": "fix typo", "standards": "none", "repo": {"name": "x", "language": "python"},
             "file": {"path": "a.py", "language": "python", "status": "M", "lines_added": 1, "lines_removed": 1},
             "diff": "@@ -1 +1 @@\n-print('helo')\n+print('hello')\n", "turn_summary": "fixed typo",
             "turn_files_changed": [{"path": "a.py", "status": "M", "lines_added": 1, "lines_removed": 1}]}
    with JevClient(timeout=20) as c:
        j = c.judge(state, questions())
    assert j.ok, j.error
    a = j.raw["answers"]
    assert 0 <= a["swallows_failure"]["noul"] <= 1
    assert 0 <= a["behavior_added"]["score"] <= 3 and "confidence" in a["behavior_added"]
    assert j.raw["usage"]["input_tokens"] > 0
