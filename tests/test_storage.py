"""E2E tests for storage.py using tmp_path to isolate the data file."""

import pytest
import storage


@pytest.fixture(autouse=True)
def isolate_storage(tmp_path):
    """Point storage._DATA_FILE at a temp file and reset after each test."""
    storage._DATA_FILE = str(tmp_path / "trips.json")
    yield
    storage._DATA_FILE = None


def _trip(id_, date, direction="to_work", duration=30, notes=""):
    return {
        "id": id_,
        "date": date,
        "direction": direction,
        "start_time": "08:00",
        "end_time": "08:30",
        "duration_minutes": duration,
        "notes": notes,
    }


# --- empty state ---


def test_load_trips_empty_when_no_file():
    assert storage.load_trips() == []


def test_export_csv_header_only_when_no_trips():
    csv = storage.export_csv_string()
    lines = csv.strip().splitlines()
    assert lines == ["date,direction,duration_minutes,notes"]


# --- save creates file ---


def test_save_trip_creates_file(tmp_path):
    storage.save_trip(_trip("1", "2024-01-01"))
    import os

    assert os.path.exists(storage._DATA_FILE)


def test_save_trip_load_returns_trip():
    storage.save_trip(_trip("1", "2024-01-01"))
    trips = storage.load_trips()
    assert len(trips) == 1
    assert trips[0]["id"] == "1"


# --- newest first ordering ---


def test_load_trips_newest_first():
    storage.save_trip(_trip("A", "2024-01-01"))
    storage.save_trip(_trip("B", "2024-01-02"))
    trips = storage.load_trips()
    assert trips[0]["id"] == "B"
    assert trips[1]["id"] == "A"


# --- update existing ---


def test_save_trip_updates_existing():
    storage.save_trip(_trip("1", "2024-01-01", notes="original"))
    storage.save_trip(_trip("1", "2024-01-01", notes="updated"))
    trips = storage.load_trips()
    assert len(trips) == 1
    assert trips[0]["notes"] == "updated"


# --- delete ---


def test_delete_trip_removes_by_id():
    storage.save_trip(_trip("1", "2024-01-01"))
    storage.save_trip(_trip("2", "2024-01-02"))
    storage.delete_trip("1")
    trips = storage.load_trips()
    assert len(trips) == 1
    assert trips[0]["id"] == "2"


def test_delete_nonexistent_trip_leaves_data_intact():
    storage.save_trip(_trip("1", "2024-01-01"))
    storage.delete_trip("does-not-exist")
    assert len(storage.load_trips()) == 1


# --- export CSV ---


def test_export_csv_correct_header_and_rows():
    storage.save_trip(
        _trip("1", "2024-01-01", direction="to_work", duration=25, notes="early")
    )
    storage.save_trip(
        _trip("2", "2024-01-02", direction="from_work", duration=35, notes="late")
    )
    lines = storage.export_csv_string().strip().splitlines()
    assert lines[0] == "date,direction,duration_minutes,notes"
    assert len(lines) == 3  # header + 2 rows


def test_export_csv_field_values():
    storage.save_trip(
        _trip("1", "2024-06-15", direction="to_work", duration=20, notes="sunny")
    )
    lines = storage.export_csv_string().strip().splitlines()
    assert "2024-06-15" in lines[1]
    assert "to_work" in lines[1]
    assert "20" in lines[1]
    assert "sunny" in lines[1]


# --- calculate_duration_minutes ---


def test_calculate_duration_minutes():
    assert storage.calculate_duration_minutes("08:00:00", "08:30:00") == 30.0
    assert storage.calculate_duration_minutes("09:00:00", "10:15:00") == 75.0
    assert storage.calculate_duration_minutes("23:00:00", "00:30:00") == 90.0


# --- full round-trip ---


def test_full_round_trip():
    storage.save_trip(_trip("X", "2024-03-01", notes="first"))
    storage.save_trip(_trip("Y", "2024-03-02", notes="second"))
    assert len(storage.load_trips()) == 2

    storage.save_trip(_trip("X", "2024-03-01", notes="updated"))
    trips = storage.load_trips()
    x = next(t for t in trips if t["id"] == "X")
    assert x["notes"] == "updated"

    storage.delete_trip("X")
    trips = storage.load_trips()
    assert len(trips) == 1
    assert trips[0]["id"] == "Y"

    csv_lines = storage.export_csv_string().strip().splitlines()
    assert len(csv_lines) == 2  # header + 1 row
