import json
from datetime import date

import pytest

from app import app as flask_app

TODAY = date(2026, 10, 23)


def make_notice(notice_id, **overrides):
    notice = {
        "id": notice_id,
        "title": f"Notice {notice_id}",
        "body": "Some text.",
        "category": "General",
        "urgent": False,
        "posted_on": "2026-10-20",
        "expires_on": "2026-11-30",
    }
    notice.update(overrides)
    return notice


GOOD_STUDENTS = [
    {
        "name": "Asha",
        "role": "Student",
        "skills": ["Python", "SQL"],
        "projects": [{"title": "P1", "description": "d", "link": "https://example.com/p1"}],
        "github": "asha",
    },
    {
        "name": "Bala",
        "role": "Student",
        "skills": ["Docker"],
        "projects": [],
        "github": "bala",
    },
]

GOOD_NOTICES = [
    make_notice(1, title="Old news", posted_on="2026-10-01", expires_on="2026-10-22"),  # expired
    make_notice(2, title="Normal older", posted_on="2026-10-10"),
    make_notice(3, title="Normal newer", posted_on="2026-10-21", category="Event"),
    make_notice(4, title="Urgent one", urgent=True, posted_on="2026-10-05", category="Exam",
                deadline="2026-10-30T17:00:00"),
    make_notice(5, title="Expires today", expires_on="2026-10-23"),  # still visible today
]


@pytest.fixture
def data_dir(tmp_path):
    """A small, valid data folder that the app is pointed at for each test."""
    (tmp_path / "notices.json").write_text(json.dumps(GOOD_NOTICES), encoding="utf-8")
    (tmp_path / "students.json").write_text(json.dumps(GOOD_STUDENTS), encoding="utf-8")
    return tmp_path


@pytest.fixture
def client(data_dir, tmp_path, monkeypatch):
    monkeypatch.setitem(flask_app.config, "DATA_DIR", data_dir)
    monkeypatch.setitem(flask_app.config, "TODAY", TODAY)
    monkeypatch.setitem(flask_app.config, "VERSION_FILE", tmp_path / "no-version.json")
    monkeypatch.setitem(flask_app.config, "HISTORY_FILE", tmp_path / "no-history.jsonl")
    flask_app.config["TESTING"] = True
    return flask_app.test_client()
