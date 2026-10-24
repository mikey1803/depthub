import copy
import json
import subprocess
import sys
from pathlib import Path

from scripts import validate_data
from tests.conftest import GOOD_NOTICES, GOOD_STUDENTS, make_notice

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "validate_data.py"


def run_cli(data_dir):
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--data-dir", str(data_dir)],
        capture_output=True, text=True,
    )


def test_good_data_passes():
    assert validate_data.validate_notices(GOOD_NOTICES) == []
    assert validate_data.validate_students(GOOD_STUDENTS) == []


def test_real_repo_data_passes():
    assert validate_data.validate_all(ROOT / "data") == []


def test_missing_field_is_caught():
    bad = copy.deepcopy(GOOD_NOTICES[1])
    del bad["title"]
    errors = validate_data.validate_notices([bad])
    assert any("missing field 'title'" in e for e in errors)


def test_duplicate_ids_are_caught():
    errors = validate_data.validate_notices([make_notice(1), make_notice(1)])
    assert any("duplicate id" in e for e in errors)


def test_unknown_category_is_caught():
    errors = validate_data.validate_notices([make_notice(1, category="Gossip")])
    assert any("unknown category" in e for e in errors)


def test_bad_dates_are_caught():
    errors = validate_data.validate_notices([
        make_notice(1, posted_on="23/10/2026"),
        make_notice(2, expires_on="2026-02-30"),
        make_notice(3, deadline="tomorrow"),
    ])
    assert len(errors) == 3


def test_expiry_before_posting_is_caught():
    errors = validate_data.validate_notices([make_notice(1, posted_on="2026-10-20", expires_on="2026-10-10")])
    assert any("before" in e for e in errors)


def test_wrong_types_are_caught():
    errors = validate_data.validate_notices([make_notice("1", urgent="yes")])
    assert any("'id' must be an integer" in e for e in errors)
    assert any("'urgent' must be true or false" in e for e in errors)


def test_typo_in_field_name_is_caught():
    errors = validate_data.validate_notices([make_notice(1, deadlne="2026-10-30T17:00:00")])
    assert any("unknown field 'deadlne'" in e for e in errors)


def test_bad_student_data_is_caught():
    bad = copy.deepcopy(GOOD_STUDENTS)
    bad[0]["skills"] = []
    bad[1]["name"] = "Asha"  # duplicate
    bad[0]["projects"][0]["link"] = "not-a-url"
    errors = validate_data.validate_students(bad)
    assert any("'skills'" in e for e in errors)
    assert any("duplicate student name" in e for e in errors)
    assert any("'link'" in e for e in errors)


def test_cli_exits_zero_for_good_data(data_dir):
    result = run_cli(data_dir)
    assert result.returncode == 0, result.stdout
    assert "passed" in result.stdout


def test_cli_exits_nonzero_for_bad_data(data_dir):
    (data_dir / "notices.json").write_text(json.dumps([make_notice(1, category="Gossip")]))
    result = run_cli(data_dir)
    assert result.returncode == 1
    assert "unknown category" in result.stdout


def test_cli_exits_nonzero_for_broken_json(data_dir):
    (data_dir / "students.json").write_text("[ oops")
    result = run_cli(data_dir)
    assert result.returncode == 1
    assert "not valid JSON" in result.stdout
