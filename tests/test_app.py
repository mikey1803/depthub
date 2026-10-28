import json

import app as app_module
from tests.conftest import GOOD_NOTICES


# ---------- routes ----------

def test_main_pages_return_200(client):
    for path in ("/", "/students", "/deploys", "/notice/3"):
        assert client.get(path).status_code == 200, path


def test_unknown_notice_is_404(client):
    assert client.get("/notice/999").status_code == 404


def test_qr_returns_png(client):
    response = client.get("/qr/3")
    assert response.status_code == 200
    assert response.mimetype == "image/png"
    assert response.data.startswith(b"\x89PNG")


# ---------- expiry and ordering ----------

def test_expired_notice_is_hidden(client):
    page = client.get("/").get_data(as_text=True)
    assert "Old news" not in page
    assert "Normal newer" in page


def test_expired_notice_detail_and_qr_are_404(client):
    assert client.get("/notice/1").status_code == 404
    assert client.get("/qr/1").status_code == 404


def test_notice_visible_on_its_last_day(client):
    assert "Expires today" in client.get("/").get_data(as_text=True)


def test_urgent_notices_come_first(client):
    titles = [n["title"] for n in app_module.get_visible_notices()]
    # urgent first (even though it is the oldest), then newest first
    assert titles == ["Urgent one", "Normal newer", "Expires today", "Normal older"]


def test_urgent_rendered_before_normal_on_page(client):
    page = client.get("/").get_data(as_text=True)
    assert page.index("Urgent one") < page.index("Normal newer")
    assert "tag-urgent" in page


# ---------- filters ----------

def test_category_filter(client):
    page = client.get("/?category=Event").get_data(as_text=True)
    assert "Normal newer" in page
    assert "Normal older" not in page


def test_skill_filter(client):
    page = client.get("/students?skill=Python").get_data(as_text=True)
    assert "Asha" in page
    assert "Bala" not in page


# ---------- deadline, version badge, history ----------

def test_deadline_is_sent_to_browser_with_timezone(client):
    page = client.get("/").get_data(as_text=True)
    assert 'data-deadline="2026-10-30T17:00:00+05:30"' in page


def test_deadline_shown_as_readable_text(client):
    assert "Due 30 Oct 2026, 5:00 PM" in client.get("/notice/4").get_data(as_text=True)


def test_next_deadline_picks_soonest_future_one():
    past = {"deadline_iso": "2000-01-01T10:00:00+05:30", "title": "past"}
    later = {"deadline_iso": "2099-06-01T10:00:00+05:30", "title": "later"}
    sooner = {"deadline_iso": "2099-01-01T10:00:00+05:30", "title": "sooner"}
    none = {"deadline_iso": None, "title": "no deadline"}
    assert app_module.next_deadline([past, later, sooner, none])["title"] == "sooner"
    assert app_module.next_deadline([past, none]) is None


def test_footer_shows_local_badge_without_version_file(client):
    assert "vdev" in client.get("/").get_data(as_text=True)


def test_footer_shows_version_info(client, tmp_path, monkeypatch):
    version_file = tmp_path / "version.json"
    version_file.write_text(json.dumps({
        "build": "42", "commit_short": "abc1234", "timestamp": "2020-01-01T00:00:00Z",
    }))
    monkeypatch.setitem(app_module.app.config, "VERSION_FILE", version_file)
    page = client.get("/students").get_data(as_text=True)
    assert "v42" in page and "commit abc1234" in page and "deployed" in page


def test_deploy_history_page_lists_entries_newest_first(client, tmp_path, monkeypatch):
    history = tmp_path / "history.jsonl"
    lines = [
        {"build": "1", "commit_short": "aaaaaaa", "message": "first deploy", "author": "Asha",
         "timestamp": "2026-10-01T10:00:00Z", "status": "success"},
        {"build": "2", "commit_short": "bbbbbbb", "message": "second deploy", "author": "Bala",
         "timestamp": "2026-10-02T10:00:00Z", "status": "rolled-back"},
    ]
    history.write_text("\n".join(json.dumps(x) for x in lines) + "\nnot json\n")
    monkeypatch.setitem(app_module.app.config, "HISTORY_FILE", history)
    page = client.get("/deploys").get_data(as_text=True)
    assert page.index("second deploy") < page.index("first deploy")
    assert "rolled-back" in page


# ---------- /health ----------

def test_health_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"


def test_health_fails_on_broken_json(client, data_dir):
    (data_dir / "notices.json").write_text("{ this is not json")
    response = client.get("/health")
    assert response.status_code == 500
    assert response.get_json()["status"] == "error"


def test_health_fails_on_invalid_data(client, data_dir):
    bad = [dict(GOOD_NOTICES[1], category="Gossip")]
    (data_dir / "notices.json").write_text(json.dumps(bad))
    assert client.get("/health").status_code == 500


def test_health_fails_when_file_missing(client, data_dir):
    (data_dir / "students.json").unlink()
    assert client.get("/health").status_code == 500
