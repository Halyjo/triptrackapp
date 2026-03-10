"""
storage.py - JSON persistence for trip data.

Trips are stored as a JSON array in a single file.
Each trip is a dict with keys:
  id, date, direction, start_time, end_time, duration_minutes, notes
"""

import json
import os
import csv
import io
from datetime import datetime

# On Android, Kivy sets App.user_data_dir to app-private storage.
# On desktop we fall back to the current directory.
_DATA_FILE = None


def _get_data_file():
    global _DATA_FILE
    if _DATA_FILE is not None:
        return _DATA_FILE
    try:
        from kivy.app import App

        app = App.get_running_app()
        if app is not None:
            _DATA_FILE = os.path.join(app.user_data_dir, "trips.json")
            return _DATA_FILE
    except Exception:
        pass
    # Fallback: same directory as this file
    _DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "trips.json")
    return _DATA_FILE


def load_trips():
    """Return list of trip dicts, newest first."""
    path = _get_data_file()
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return list(reversed(data))  # newest first for display


def _load_raw():
    """Return trips in insertion order (oldest first)."""
    path = _get_data_file()
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_trip(trip_dict):
    """Append or update a trip. Uses trip['id'] as key."""
    trips = _load_raw()
    existing_ids = [t["id"] for t in trips]
    if trip_dict["id"] in existing_ids:
        idx = existing_ids.index(trip_dict["id"])
        trips[idx] = trip_dict
    else:
        trips.append(trip_dict)
    path = _get_data_file()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(trips, f, indent=2)


def delete_trip(trip_id):
    """Remove trip by id."""
    trips = [t for t in _load_raw() if t["id"] != trip_id]
    path = _get_data_file()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(trips, f, indent=2)


def calculate_duration_minutes(start_str, end_str):
    """Parse HH:MM:SS or HH:MM time strings, return duration in minutes as float.
    Handles overnight trips (end < start) by adding 24 hours."""
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            start = datetime.strptime(start_str, fmt)
            end = datetime.strptime(end_str, fmt)
            break
        except ValueError:
            continue
    else:
        raise ValueError(f"Cannot parse times: {start_str!r}, {end_str!r}")
    delta = end - start
    minutes = delta.total_seconds() / 60
    if minutes < 0:
        minutes += 24 * 60
    return minutes


def export_csv_string():
    """Return CSV string with header: date,direction,duration_minutes,notes."""
    trips = _load_raw()
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["date", "direction", "duration_minutes", "notes"])
    for t in trips:
        writer.writerow(
            [
                t.get("date", ""),
                t.get("direction", ""),
                t.get("duration_minutes", ""),
                t.get("notes", ""),
            ]
        )
    return buf.getvalue()
