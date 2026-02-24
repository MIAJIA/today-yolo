#!/usr/bin/env python3
import sqlite3
import json
import sys
import os
import shutil
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import argparse


DB_SOURCE_PATH = os.path.expanduser("~/Library/Application Support/info.eurocomp.Timing2/SQLite.db")
TIMEZONE = "America/Los_Angeles"
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_OUTPUT_DIR = os.path.join(REPO_ROOT, "tmp", "ttl=30d")


def extract_activities(target_date):
    """Extract raw activity data from local Timing SQLite DB."""
    try:
        tz = ZoneInfo(TIMEZONE)
        start_dt = datetime.strptime(target_date, "%Y-%m-%d").replace(tzinfo=tz)
        end_dt = start_dt + timedelta(days=1)
        start_ts = start_dt.timestamp()
        end_ts = end_dt.timestamp()
    except ValueError:
        print(f"Error: Invalid date format '{target_date}'. Use YYYY-MM-DD.")
        sys.exit(1)

    temp_dir = os.path.join(
        DEFAULT_OUTPUT_DIR,
        f"{datetime.now().strftime('%Y-%m-%d')}_timing_extract_{datetime.now().strftime('%H%M%S')}"
    )
    os.makedirs(temp_dir, exist_ok=True)
    temp_db_path = os.path.join(temp_dir, "timing_dump.db")

    if not os.path.exists(DB_SOURCE_PATH):
        print(f"Error: Timing Database not found at {DB_SOURCE_PATH}")
        sys.exit(1)

    try:
        src = sqlite3.connect(f"file:{DB_SOURCE_PATH}?mode=ro", uri=True)
        dest = sqlite3.connect(temp_db_path)
        src.backup(dest)
        dest.close()
        src.close()
    except Exception as exc:
        print(f"Error copying database: {exc}")
        shutil.rmtree(temp_dir)
        sys.exit(1)

    activities = []
    try:
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        query = """
        SELECT
          AppActivity.startDate,
          AppActivity.endDate,
          Application.title as AppName,
          Title.stringValue as WindowTitle,
          Path.stringValue as FilePath
        FROM AppActivity
        LEFT JOIN Application ON AppActivity.applicationID = Application.id
        LEFT JOIN Title ON AppActivity.titleID = Title.id
        LEFT JOIN Path ON AppActivity.pathID = Path.id
        WHERE AppActivity.startDate >= ? AND AppActivity.startDate < ?
        ORDER BY AppActivity.startDate ASC
        """
        cursor.execute(query, (start_ts, end_ts))
        rows = cursor.fetchall()

        for row in rows:
            activities.append({
                "start": row[0],
                "end": row[1],
                "app": row[2],
                "title": row[3],
                "path": row[4],
            })

        conn.close()
    except Exception as exc:
        print(f"Error querying database: {exc}")
    finally:
        shutil.rmtree(temp_dir)

    return activities


def normalize_activity(activity):
    app = activity.get("app") or "Unknown"
    title = activity.get("title") or ""
    path = activity.get("path") or ""

    if title:
        summary = f"{app}: {title}"
    else:
        summary = app

    details = []
    if app:
        details.append(f"App: {app}")
    if title:
        details.append(f"Title: {title}")
    if path:
        details.append(f"Path: {path}")

    return {
        "start_ts": activity.get("start"),
        "end_ts": activity.get("end") or activity.get("start"),
        "category": app,
        "summary": summary,
        "details": details,
    }


def build_output_path(target_date, output_format, summary=False):
    output_dir = os.path.join(DEFAULT_OUTPUT_DIR, f"{target_date}_timing")
    os.makedirs(output_dir, exist_ok=True)
    if summary:
        return os.path.join(output_dir, "summary.json")
    ext = "json" if output_format == "json" else "md"
    return os.path.join(output_dir, f"timeline.{ext}")


def extract_project(activity):
    """Extract project name from path or window title."""
    path = activity.get("path") or ""
    title = activity.get("title") or ""
    app = activity.get("app") or ""

    # Extract from path first (most reliable)
    if path:
        # Look for known project directories
        path_parts = path.split("/")
        for i, part in enumerate(path_parts):
            if part in ("zDesk", "znotes", "namefi-astra", "dotenv-mask-editor"):
                return part
            # Check parent of common dirs
            if part in ("src", "skills", ".claude", "packages", "apps"):
                if i > 0:
                    return path_parts[i - 1]

    # Extract from window title
    if title:
        # Pattern: "filename — project" (em dash from editors)
        if " — " in title:
            parts = title.split(" — ")
            if len(parts) >= 2:
                return parts[-1].strip()
        # Pattern: "something – Space Name" (en dash from Arc)
        if " – " in title:
            parts = title.split(" – ")
            if len(parts) >= 2:
                # Last part is usually the Arc Space
                return parts[-1].strip()

    # Fallback to app for non-dev apps
    if app in ("WeChat", "Slack", "Messages", "Telegram", "WhatsApp", "Discord"):
        return "Communication"
    if app in ("Calendar", "Mail", "Gmail"):
        return "Email/Calendar"
    if app in ("Arc", "Safari", "Chrome", "Firefox"):
        return "Browsing"

    return "misc"


def extract_file_name(activity):
    """Extract meaningful file/document name."""
    path = activity.get("path") or ""
    title = activity.get("title") or ""

    if path:
        return os.path.basename(path)

    if title:
        # For "filename — project" pattern, take the filename
        if " — " in title:
            return title.split(" — ")[0].strip()
        # For web pages, take first meaningful part
        if " – " in title:
            return title.split(" – ")[0].strip()
        return title

    return None


def build_summary(activities, target_date):
    """Build aggregated summary grouped by time proximity, then by project within each session."""
    MIN_DURATION_SECS = 5  # Filter out activities under 5 seconds
    SESSION_GAP_SECS = 15 * 60  # 15 minutes gap = new session

    if not activities:
        return {
            "date": target_date,
            "total_hours": 0,
            "by_project": {},
            "work_sessions": [],
        }

    tz = ZoneInfo(TIMEZONE)

    # Enrich activities with project and file info, filter short ones
    enriched = []
    for a in activities:
        start_ts = a.get("start")
        end_ts = a.get("end") or start_ts
        duration = end_ts - start_ts

        # Skip activities under 5 seconds
        if duration < MIN_DURATION_SECS:
            continue

        enriched.append({
            "start_ts": start_ts,
            "end_ts": end_ts,
            "duration": duration,
            "app": a.get("app") or "Unknown",
            "title": a.get("title") or "",
            "project": extract_project(a),
            "file": extract_file_name(a),
        })

    if not enriched:
        return {
            "date": target_date,
            "total_hours": 0,
            "by_project": {},
            "work_sessions": [],
        }

    # Sort by start time
    enriched.sort(key=lambda x: x["start_ts"])

    # Step 1: Group into time-based sessions (merge ALL activities within gap threshold)
    sessions = []
    current_session = {
        "start_ts": enriched[0]["start_ts"],
        "end_ts": enriched[0]["end_ts"],
        "entries": [enriched[0]],
    }

    for entry in enriched[1:]:
        gap = entry["start_ts"] - current_session["end_ts"]

        if gap < SESSION_GAP_SECS:
            # Extend current session
            current_session["end_ts"] = max(current_session["end_ts"], entry["end_ts"])
            current_session["entries"].append(entry)
        else:
            # Start new session
            sessions.append(current_session)
            current_session = {
                "start_ts": entry["start_ts"],
                "end_ts": entry["end_ts"],
                "entries": [entry],
            }

    sessions.append(current_session)

    # Step 2: Analyze each session to find primary project and aggregate data
    formatted_sessions = []
    total_project_seconds = {}

    for session in sessions:
        entries = session["entries"]
        duration_mins = round((session["end_ts"] - session["start_ts"]) / 60, 1)

        if duration_mins < 1:  # Skip sessions under 1 minute
            continue

        # Calculate time per project within this session
        project_seconds = {}
        apps = set()
        files = set()
        titles = []

        for e in entries:
            proj = e["project"]
            project_seconds[proj] = project_seconds.get(proj, 0) + e["duration"]
            apps.add(e["app"])
            if e["file"]:
                files.add(e["file"])
            if e["title"] and e["title"] not in titles:
                titles.append(e["title"])

        # Accumulate for global by_project
        for proj, secs in project_seconds.items():
            total_project_seconds[proj] = total_project_seconds.get(proj, 0) + secs

        # Find primary project (most time spent)
        sorted_projects = sorted(project_seconds.items(), key=lambda x: -x[1])
        primary_project = sorted_projects[0][0] if sorted_projects else "misc"

        # Build project breakdown for this session (only include projects with > 1 min)
        project_breakdown = {}
        for proj, secs in sorted_projects:
            mins = round(secs / 60, 1)
            if mins >= 1:
                project_breakdown[proj] = mins

        start_str = datetime.fromtimestamp(session["start_ts"], tz).strftime("%H:%M")
        end_str = datetime.fromtimestamp(session["end_ts"], tz).strftime("%H:%M")

        formatted_sessions.append({
            "time": f"{start_str}~{end_str}",
            "primary_project": primary_project,
            "duration_mins": duration_mins,
            "projects": project_breakdown,
            "apps": sorted(apps),
            "files": list(files)[:10],
            "titles": titles[:10],
        })

    # Calculate global by_project hours
    total_seconds = sum(total_project_seconds.values())
    sorted_projects = sorted(total_project_seconds.items(), key=lambda x: -x[1])
    by_project = {proj: round(secs / 3600, 2) for proj, secs in sorted_projects}

    return {
        "date": target_date,
        "total_hours": round(total_seconds / 3600, 2),
        "by_project": by_project,
        "work_sessions": formatted_sessions,
    }


def write_output(activities, target_date, output_format, output_path):
    if not activities:
        payload = "[]" if output_format == "json" else f"# Timeline Journal for {target_date}\n\nNo activity found for this date."
        if output_path == "-":
            print(payload)
            return
        with open(output_path, "w") as f:
            f.write(payload)
        print(output_path)
        return

    normalized = [normalize_activity(activity) for activity in activities]
    normalized.sort(key=lambda x: x.get("start_ts", 0))

    if output_format == 'json':
        payload = json.dumps(normalized, indent=2)
        if output_path == "-":
            print(payload)
        else:
            with open(output_path, "w") as f:
                f.write(payload)
            print(output_path)
        return

    lines = [f"# Timeline Journal for {target_date}"]
    for entry in normalized:
        start_str = datetime.fromtimestamp(entry['start_ts'], ZoneInfo(TIMEZONE)).strftime("%H:%M")
        end_str = datetime.fromtimestamp(entry['end_ts'], ZoneInfo(TIMEZONE)).strftime("%H:%M")
        lines.append(f"\n**[{start_str} - {end_str}]**: {entry['summary']}")

    payload = "\n".join(lines)
    if output_path == "-":
        print(payload)
    else:
        with open(output_path, "w") as f:
            f.write(payload)
        print(output_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('date_pos', nargs='?', help='YYYY-MM-DD')
    parser.add_argument('--date', help='YYYY-MM-DD')
    parser.add_argument('--format', choices=['markdown', 'json'], default='json')
    parser.add_argument('--summary', action='store_true', help='Output aggregated summary instead of raw timeline')
    parser.add_argument('--output', help='Output file path (use - for stdout)')
    args = parser.parse_args()

    target_date_str = args.date if args.date else args.date_pos
    if target_date_str:
        target_date = target_date_str
    else:
        target_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    data = extract_activities(target_date)

    if args.summary:
        summary = build_summary(data, target_date)
        output_path = args.output or build_output_path(target_date, args.format, summary=True)
        payload = json.dumps(summary, indent=2)
        if output_path == "-":
            print(payload)
        else:
            with open(output_path, "w") as f:
                f.write(payload)
            print(output_path)
    else:
        output_path = args.output or build_output_path(target_date, args.format)
        write_output(data, target_date, args.format, output_path)
