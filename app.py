"""DeptHub: a small department portal. Flask + JSON files, no database."""
import json
import os
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path

import qrcode
from flask import Flask, abort, jsonify, render_template, request, send_file, url_for
from qrcode.image.pure import PyPNGImage

from scripts import validate_data

BASE_DIR = Path(__file__).resolve().parent
IST = timezone(timedelta(hours=5, minutes=30))  # the VM runs on UTC, the campus does not

app = Flask(__name__)
app.config.update(
    DATA_DIR=BASE_DIR / "data",
    VERSION_FILE=BASE_DIR / "version.json",
    # deploy.sh appends to this file; it lives outside the release folders
    HISTORY_FILE=Path(os.environ.get("DEPTHUB_HISTORY", "/opt/depthub/deploy_history.jsonl")),
    TODAY=None,  # tests set this to pin "today"
)


# ---------- helpers ----------

def today():
    return app.config["TODAY"] or datetime.now(IST).date()


def read_json(filename):
    with open(Path(app.config["DATA_DIR"]) / filename, encoding="utf-8") as f:
        return json.load(f)


def get_visible_notices(category=None):
    """Notices that have not expired, urgent ones first, then newest first."""
    notices = []
    for raw in read_json("notices.json"):
        expires_on = validate_data.parse_date(raw["expires_on"])
        if expires_on < today():
            continue  # auto-expired: hidden
        notice = dict(raw)
        notice["posted_on"] = validate_data.parse_date(raw["posted_on"])
        notice["expires_on"] = expires_on
        deadline = raw.get("deadline")
        notice["deadline_iso"] = None
        notice["deadline_text"] = None
        if deadline:
            due = validate_data.parse_datetime(deadline).replace(tzinfo=IST)
            # Send the deadline with its time zone so the browser countdown is exact
            notice["deadline_iso"] = due.isoformat()
            notice["deadline_text"] = f"{due.day} {due:%b %Y}, {due:%I:%M %p}".replace(", 0", ", ")
        notices.append(notice)

    if category:
        notices = [n for n in notices if n["category"] == category]
    notices.sort(key=lambda n: (not n["urgent"], -n["posted_on"].toordinal()))
    return notices


def next_deadline(notices):
    """The notice whose deadline comes soonest (and has not passed yet), or None."""
    now = datetime.now(IST)
    upcoming = [n for n in notices
                if n["deadline_iso"] and datetime.fromisoformat(n["deadline_iso"]) > now]
    return min(upcoming, key=lambda n: n["deadline_iso"], default=None)


def get_notice(notice_id):
    for notice in get_visible_notices():
        if notice["id"] == notice_id:
            return notice
    return None


def time_ago(iso_text):
    try:
        when = datetime.fromisoformat(iso_text.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return "at an unknown time"
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    seconds = int((datetime.now(timezone.utc) - when).total_seconds())
    if seconds < 60:
        return "just now"
    for unit, size in (("day", 86400), ("hour", 3600), ("minute", 60)):
        if seconds >= size:
            count = seconds // size
            return f"{count} {unit}{'s' if count != 1 else ''} ago"


def load_version():
    """Read version.json written at build time; fall back to a 'local' badge."""
    try:
        with open(app.config["VERSION_FILE"], encoding="utf-8") as f:
            info = json.load(f)
        info["deployed_ago"] = time_ago(info.get("timestamp"))
        return info
    except (OSError, ValueError):
        return {"build": "dev", "commit_short": "local", "deployed_ago": None}


def load_history():
    """Deployment history, newest first. Bad lines are skipped."""
    entries = []
    try:
        with open(app.config["HISTORY_FILE"], encoding="utf-8") as f:
            for line in f:
                try:
                    entries.append(json.loads(line))
                except ValueError:
                    continue
    except OSError:
        pass
    for entry in entries:
        entry["ago"] = time_ago(entry.get("timestamp"))
    return list(reversed(entries))


@app.context_processor
def inject_globals():
    return {"version": load_version()}


@app.template_filter("pretty_date")
def pretty_date(value):
    return f"{value.day} {value:%b %Y}"


# ---------- pages ----------

@app.route("/")
def index():
    selected = next(
        (c for c in validate_data.CATEGORIES if c.lower() == request.args.get("category", "").lower()),
        None,
    )
    notices = get_visible_notices(selected)
    return render_template(
        "index.html",
        pinned=[n for n in notices if n["urgent"]],
        others=[n for n in notices if not n["urgent"]],
        next_up=next_deadline(notices),
        categories=validate_data.CATEGORIES,
        selected=selected,
    )


@app.route("/notice/<int:notice_id>")
def notice_detail(notice_id):
    notice = get_notice(notice_id)
    if notice is None:
        abort(404)
    return render_template("notice.html", notice=notice)


@app.route("/qr/<int:notice_id>")
def notice_qr(notice_id):
    if get_notice(notice_id) is None:
        abort(404)
    link = url_for("notice_detail", notice_id=notice_id, _external=True)
    buffer = BytesIO()
    qrcode.make(link, image_factory=PyPNGImage, box_size=8, border=2).save(buffer)
    buffer.seek(0)
    return send_file(buffer, mimetype="image/png")


@app.route("/students")
def students():
    all_students = sorted(read_json("students.json"), key=lambda s: s["name"])
    all_skills = sorted({skill for s in all_students for skill in s["skills"]}, key=str.lower)
    selected = next((s for s in all_skills if s.lower() == request.args.get("skill", "").lower()), None)
    shown = [s for s in all_students if selected in s["skills"]] if selected else all_students
    return render_template("students.html", students=shown, skills=all_skills, selected=selected)


@app.route("/deploys")
def deploys():
    return render_template("deploys.html", history=load_history())


@app.route("/health")
def health():
    errors = validate_data.validate_all(app.config["DATA_DIR"])
    if errors:
        return jsonify(status="error", errors=errors), 500
    return jsonify(status="ok", build=load_version().get("build")), 200


@app.errorhandler(404)
def not_found(_error):
    return render_template("404.html"), 404


if __name__ == "__main__":
    app.run(debug=True)
