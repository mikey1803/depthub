"""Check data/notices.json and data/students.json.

Used in two places:
  * Jenkins runs it before deploying (exit code 1 stops the pipeline)
  * the Flask app calls validate_all() for the /health endpoint

Usage: python scripts/validate_data.py [--data-dir data]
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

CATEGORIES = ("Exam", "Event", "Placement", "General")

NOTICE_REQUIRED = {"id", "title", "body", "category", "urgent", "posted_on", "expires_on"}
NOTICE_OPTIONAL = {"deadline"}
STUDENT_FIELDS = {"name", "role", "skills", "projects", "github"}
PROJECT_FIELDS = {"title", "description", "link"}

DATE_FORMAT = "%Y-%m-%d"
DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S"


def parse_date(text):
    """'2026-10-30' -> date. Raises ValueError for anything else."""
    return datetime.strptime(text, DATE_FORMAT).date()


def parse_datetime(text):
    """'2026-10-30T17:00:00' -> datetime. Raises ValueError for anything else."""
    return datetime.strptime(text, DATETIME_FORMAT)


def _is_text(value):
    return isinstance(value, str) and value.strip() != ""


def _check_keys(item, required, optional, where, errors):
    for key in sorted(required - item.keys()):
        errors.append(f"{where}: missing field '{key}'")
    for key in sorted(item.keys() - required - optional):
        errors.append(f"{where}: unknown field '{key}' (typo?)")


def validate_notices(data):
    """Return a list of error messages (empty list = all good)."""
    errors = []
    if not isinstance(data, list):
        return ["notices.json: top level must be a list"]

    seen_ids = set()
    for index, notice in enumerate(data):
        where = f"notices[{index}]"
        if not isinstance(notice, dict):
            errors.append(f"{where}: must be an object")
            continue
        _check_keys(notice, NOTICE_REQUIRED, NOTICE_OPTIONAL, where, errors)

        notice_id = notice.get("id")
        if "id" in notice:
            if not isinstance(notice_id, int) or isinstance(notice_id, bool):
                errors.append(f"{where}: 'id' must be an integer")
            elif notice_id in seen_ids:
                errors.append(f"{where}: duplicate id {notice_id}")
            else:
                seen_ids.add(notice_id)

        for field in ("title", "body"):
            if field in notice and not _is_text(notice[field]):
                errors.append(f"{where}: '{field}' must be a non-empty string")

        if "category" in notice and notice["category"] not in CATEGORIES:
            errors.append(
                f"{where}: unknown category {notice['category']!r}, "
                f"use one of {', '.join(CATEGORIES)}"
            )

        if "urgent" in notice and not isinstance(notice["urgent"], bool):
            errors.append(f"{where}: 'urgent' must be true or false")

        dates = {}
        for field in ("posted_on", "expires_on"):
            if field not in notice:
                continue
            try:
                dates[field] = parse_date(notice[field])
            except (ValueError, TypeError):
                errors.append(f"{where}: '{field}' must be a date like 2026-10-30")
        if len(dates) == 2 and dates["expires_on"] < dates["posted_on"]:
            errors.append(f"{where}: 'expires_on' is before 'posted_on'")

        if notice.get("deadline") is not None:
            try:
                parse_datetime(notice["deadline"])
            except (ValueError, TypeError):
                errors.append(
                    f"{where}: 'deadline' must look like 2026-10-30T17:00:00 (or be left out)"
                )
    return errors


def validate_students(data):
    """Return a list of error messages (empty list = all good)."""
    errors = []
    if not isinstance(data, list):
        return ["students.json: top level must be a list"]

    seen_names = set()
    for index, student in enumerate(data):
        where = f"students[{index}]"
        if not isinstance(student, dict):
            errors.append(f"{where}: must be an object")
            continue
        _check_keys(student, STUDENT_FIELDS, set(), where, errors)

        for field in ("name", "role", "github"):
            if field in student and not _is_text(student[field]):
                errors.append(f"{where}: '{field}' must be a non-empty string")

        name = student.get("name")
        if _is_text(name):
            if name in seen_names:
                errors.append(f"{where}: duplicate student name {name!r}")
            seen_names.add(name)

        if "skills" in student:
            skills = student["skills"]
            if not isinstance(skills, list) or not skills or not all(_is_text(s) for s in skills):
                errors.append(f"{where}: 'skills' must be a non-empty list of strings")

        if "projects" in student:
            projects = student["projects"]
            if not isinstance(projects, list):
                errors.append(f"{where}: 'projects' must be a list")
                continue
            for p_index, project in enumerate(projects):
                p_where = f"{where}.projects[{p_index}]"
                if not isinstance(project, dict):
                    errors.append(f"{p_where}: must be an object")
                    continue
                _check_keys(project, PROJECT_FIELDS, set(), p_where, errors)
                for field in PROJECT_FIELDS & project.keys():
                    if not _is_text(project[field]):
                        errors.append(f"{p_where}: '{field}' must be a non-empty string")
                link = project.get("link")
                if _is_text(link) and not link.startswith(("http://", "https://")):
                    errors.append(f"{p_where}: 'link' must start with http:// or https://")
    return errors


def _load(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f), None
    except FileNotFoundError:
        return None, f"{path.name}: file not found"
    except json.JSONDecodeError as exc:
        return None, f"{path.name}: not valid JSON ({exc})"


def validate_all(data_dir):
    """Validate both files in data_dir. Returns a list of error messages."""
    data_dir = Path(data_dir)
    errors = []
    for filename, checker in (
        ("notices.json", validate_notices),
        ("students.json", validate_students),
    ):
        data, load_error = _load(data_dir / filename)
        if load_error:
            errors.append(load_error)
        else:
            errors.extend(checker(data))
    return errors


def main():
    default_dir = Path(__file__).resolve().parent.parent / "data"
    parser = argparse.ArgumentParser(description="Validate DeptHub data files")
    parser.add_argument("--data-dir", default=str(default_dir))
    args = parser.parse_args()

    errors = validate_all(args.data_dir)
    if errors:
        print(f"Data validation FAILED ({len(errors)} problem(s)):")
        for error in errors:
            print(f"  - {error}")
        return 1
    print("Data validation passed: notices.json and students.json are OK.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
