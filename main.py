"""
TripTrack - Simple commute tracker for Android (built with Kivy).

Screens:
  HomeScreen  - Start/stop a trip (To Work / From Work)
  TripsScreen - Browse and delete past trips
  ExportScreen - Export all trips to CSV

To run on desktop:  python main.py
To build for Android: buildozer android debug
"""

import uuid
from datetime import datetime

from kivy.app import App
from kivy.clock import Clock
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.textinput import TextInput
from kivy.metrics import sp, dp

import storage

# ── helpers ──────────────────────────────────────────────────────────────────

NAV_HEIGHT = dp(50)
BIG_FONT = sp(22)
MED_FONT = sp(16)
SM_FONT = sp(13)

DIRECTION_LABELS = {"to_work": "To Work", "from_work": "From Work"}


def _nav_bar(screen_manager):
    """Return a horizontal BoxLayout with Home / Trips / Export buttons."""
    bar = BoxLayout(size_hint_y=None, height=NAV_HEIGHT, spacing=dp(2))
    for label, target in [("Home", "home"), ("Trips", "trips"), ("Export", "export")]:
        btn = Button(
            text=label, font_size=MED_FONT, background_color=(0.2, 0.2, 0.8, 1)
        )
        btn.bind(on_press=lambda _, t=target: setattr(screen_manager, "current", t))
        bar.add_widget(btn)
    return bar


def _make_label(text, font_size=MED_FONT, bold=False, **kwargs):
    lbl = Label(
        text=text,
        font_size=font_size,
        bold=bold,
        halign="center",
        valign="middle",
        **kwargs,
    )
    lbl.bind(size=lbl.setter("text_size"))
    return lbl


# ── HomeScreen ────────────────────────────────────────────────────────────────


class HomeScreen(Screen):
    """
    Shows two big start buttons when idle.
    While a trip is active: shows direction, live timer, and End Trip button.
    """

    def __init__(self, **kw):
        super().__init__(**kw)
        self._active_trip = None  # dict while a trip is in progress
        self._timer_event = None
        self._elapsed = 0

        root = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(8))

        # Title
        root.add_widget(
            _make_label(
                "TripTrack",
                font_size=sp(28),
                bold=True,
                size_hint_y=None,
                height=dp(50),
            )
        )

        # Content area (swapped between idle / active views)
        self._content = BoxLayout(orientation="vertical", spacing=dp(10))
        root.add_widget(self._content)

        # Last trip summary
        self._last_label = _make_label(
            "", font_size=SM_FONT, size_hint_y=None, height=dp(40)
        )
        root.add_widget(self._last_label)

        # Nav bar added by TripApp after screens are created
        self._nav_placeholder = BoxLayout(size_hint_y=None, height=NAV_HEIGHT)
        root.add_widget(self._nav_placeholder)

        self.add_widget(root)
        self._show_idle()

    def on_enter(self):
        self._refresh_last_trip()

    def _refresh_last_trip(self):
        trips = storage.load_trips()
        if trips:
            t = trips[0]
            dur = t.get("duration_minutes", "?")
            self._last_label.text = (
                f"Last trip: {t.get('date', '')}  "
                f"{DIRECTION_LABELS.get(t.get('direction', ''), '')}  "
                f"{dur} min"
            )
        else:
            self._last_label.text = "No trips yet."

    # ── idle view (two big start buttons) ───────────────────────────────────

    def _show_idle(self):
        self._content.clear_widgets()
        self._content.add_widget(
            _make_label(
                "Where are you going?",
                font_size=MED_FONT,
                size_hint_y=None,
                height=dp(40),
            )
        )
        for direction, label in [
            ("to_work", "To Work  →"),
            ("from_work", "← From Work"),
        ]:
            btn = Button(
                text=label, font_size=BIG_FONT, background_color=(0.1, 0.6, 0.3, 1)
            )
            btn.bind(on_press=lambda _, d=direction: self._start_trip(d))
            self._content.add_widget(btn)

    # ── active trip view ─────────────────────────────────────────────────────

    def _show_active(self):
        self._content.clear_widgets()
        direction_text = DIRECTION_LABELS.get(self._active_trip["direction"], "Trip")
        self._content.add_widget(
            _make_label(
                f"Active: {direction_text}",
                font_size=BIG_FONT,
                bold=True,
                size_hint_y=None,
                height=dp(50),
            )
        )

        self._timer_label = _make_label(
            "00:00", font_size=sp(40), size_hint_y=None, height=dp(70)
        )
        self._content.add_widget(self._timer_label)

        end_btn = Button(
            text="End Trip", font_size=BIG_FONT, background_color=(0.8, 0.1, 0.1, 1)
        )
        end_btn.bind(on_press=self._end_trip)
        self._content.add_widget(end_btn)

    # ── trip lifecycle ────────────────────────────────────────────────────────

    def _start_trip(self, direction):
        now = datetime.now()
        self._active_trip = {
            "id": str(uuid.uuid4()),
            "date": now.strftime("%Y-%m-%d"),
            "direction": direction,
            "start_time": now.strftime("%H:%M:%S"),
            "end_time": "",
            "duration_minutes": 0,
            "notes": "",
        }
        self._elapsed = 0
        self._show_active()
        self._timer_event = Clock.schedule_interval(self._tick, 1)

    def _tick(self, dt):
        self._elapsed += 1
        mins, secs = divmod(self._elapsed, 60)
        self._timer_label.text = f"{mins:02d}:{secs:02d}"

    def _end_trip(self, *_):
        if self._timer_event:
            self._timer_event.cancel()
            self._timer_event = None
        now = datetime.now()
        self._active_trip["end_time"] = now.strftime("%H:%M:%S")
        self._active_trip["duration_minutes"] = round(self._elapsed / 60, 1)
        storage.save_trip(self._active_trip)
        self._active_trip = None
        self._show_idle()
        self._refresh_last_trip()


# ── EditTripPopup ─────────────────────────────────────────────────────────────


class EditTripPopup(Popup):
    """Pre-filled popup to edit an existing trip's fields."""

    def __init__(self, trip, on_saved, **kw):
        self._trip = trip
        self._on_saved = on_saved

        content = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(8))

        def _labeled_row(label_text, widget):
            row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6))
            row.add_widget(
                Label(
                    text=label_text,
                    size_hint_x=None,
                    width=dp(90),
                    font_size=SM_FONT,
                    halign="right",
                    valign="middle",
                )
            )
            row.add_widget(widget)
            return row

        # Date
        self._date_input = TextInput(
            text=trip.get("date", ""), multiline=False, font_size=SM_FONT
        )
        content.add_widget(_labeled_row("Date:", self._date_input))

        # Direction toggle buttons
        dir_row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6))
        dir_row.add_widget(
            Label(
                text="Direction:",
                size_hint_x=None,
                width=dp(90),
                font_size=SM_FONT,
                halign="right",
                valign="middle",
            )
        )
        self._dir_btns = {}
        for key, label in DIRECTION_LABELS.items():
            btn = Button(text=label, font_size=SM_FONT)
            btn.bind(on_press=lambda _, k=key: self._select_direction(k))
            self._dir_btns[key] = btn
            dir_row.add_widget(btn)
        content.add_widget(dir_row)
        self._current_direction = trip.get("direction", "to_work")
        self._highlight_direction(self._current_direction)

        # Start time
        self._start_input = TextInput(
            text=trip.get("start_time", ""), multiline=False, font_size=SM_FONT
        )
        content.add_widget(_labeled_row("Start:", self._start_input))

        # End time
        self._end_input = TextInput(
            text=trip.get("end_time", ""), multiline=False, font_size=SM_FONT
        )
        content.add_widget(_labeled_row("End:", self._end_input))

        # Notes
        self._notes_input = TextInput(
            text=trip.get("notes", ""), multiline=False, font_size=SM_FONT
        )
        content.add_widget(_labeled_row("Notes:", self._notes_input))

        # Save / Cancel buttons
        btn_row = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(10))
        save_btn = Button(
            text="Save", background_color=(0.1, 0.6, 0.3, 1), font_size=SM_FONT
        )
        cancel_btn = Button(text="Cancel", font_size=SM_FONT)
        save_btn.bind(on_press=self._save)
        cancel_btn.bind(on_press=self.dismiss)
        btn_row.add_widget(save_btn)
        btn_row.add_widget(cancel_btn)
        content.add_widget(btn_row)

        super().__init__(
            title="Edit Trip", content=content, size_hint=(0.95, 0.85), **kw
        )

    def _select_direction(self, key):
        self._current_direction = key
        self._highlight_direction(key)

    def _highlight_direction(self, selected_key):
        for key, btn in self._dir_btns.items():
            if key == selected_key:
                btn.background_color = (0.1, 0.6, 0.3, 1)
            else:
                btn.background_color = (0.3, 0.3, 0.3, 1)

    def _save(self, *_):
        start = self._start_input.text.strip()
        end = self._end_input.text.strip()
        try:
            duration = storage.calculate_duration_minutes(start, end)
        except Exception as exc:
            err = Popup(
                title="Invalid time",
                content=Label(text=f"Cannot parse times:\n{exc}\n\nUse HH:MM or HH:MM:SS"),
                size_hint=(0.8, 0.4),
            )
            err.open()
            return
        updated = dict(self._trip)
        updated["date"] = self._date_input.text.strip()
        updated["direction"] = self._current_direction
        updated["start_time"] = start
        updated["end_time"] = end
        updated["duration_minutes"] = round(duration, 1)
        updated["notes"] = self._notes_input.text.strip()
        storage.save_trip(updated)
        self._on_saved(updated)
        self.dismiss()


# ── TripsScreen ───────────────────────────────────────────────────────────────


class TripsScreen(Screen):
    """Scrollable list of past trips with a Delete button per row."""

    def __init__(self, **kw):
        super().__init__(**kw)
        root = BoxLayout(orientation="vertical", padding=dp(8), spacing=dp(6))

        root.add_widget(
            _make_label(
                "Past Trips",
                font_size=BIG_FONT,
                bold=True,
                size_hint_y=None,
                height=dp(50),
            )
        )

        self._scroll = ScrollView()
        self._list = GridLayout(cols=1, spacing=dp(4), size_hint_y=None, padding=dp(4))
        self._list.bind(minimum_height=self._list.setter("height"))
        self._scroll.add_widget(self._list)
        root.add_widget(self._scroll)

        self._nav_placeholder = BoxLayout(size_hint_y=None, height=NAV_HEIGHT)
        root.add_widget(self._nav_placeholder)
        self.add_widget(root)

    def on_enter(self):
        self._reload()

    def _reload(self):
        self._list.clear_widgets()
        trips = storage.load_trips()
        if not trips:
            self._list.add_widget(
                _make_label("No trips recorded yet.", size_hint_y=None, height=dp(40))
            )
            return
        for trip in trips:
            row = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(6))
            info = (
                f"{trip.get('date', '')}  "
                f"{DIRECTION_LABELS.get(trip.get('direction', ''), trip.get('direction', ''))}  "
                f"{trip.get('duration_minutes', '?')} min"
            )
            row.add_widget(_make_label(info, font_size=SM_FONT))
            edit_btn = Button(
                text="Edit",
                size_hint_x=None,
                width=dp(60),
                font_size=SM_FONT,
                background_color=(0.1, 0.4, 0.8, 1),
            )
            edit_btn.bind(on_press=lambda _, t=trip: self._open_edit(t))
            row.add_widget(edit_btn)
            del_btn = Button(
                text="Del",
                size_hint_x=None,
                width=dp(60),
                font_size=SM_FONT,
                background_color=(0.7, 0.1, 0.1, 1),
            )
            del_btn.bind(on_press=lambda _, tid=trip["id"]: self._confirm_delete(tid))
            row.add_widget(del_btn)
            self._list.add_widget(row)

    def _open_edit(self, trip):
        popup = EditTripPopup(trip=trip, on_saved=lambda _: self._reload())
        popup.open()

    def _confirm_delete(self, trip_id):
        content = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(10))
        content.add_widget(_make_label("Delete this trip?", font_size=MED_FONT))
        btns = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(10))
        popup = Popup(title="Confirm", content=content, size_hint=(0.8, 0.4))
        yes = Button(text="Delete", background_color=(0.8, 0.1, 0.1, 1))
        no = Button(text="Cancel")

        def do_delete(_):
            storage.delete_trip(trip_id)
            popup.dismiss()
            self._reload()

        yes.bind(on_press=do_delete)
        no.bind(on_press=popup.dismiss)
        btns.add_widget(yes)
        btns.add_widget(no)
        content.add_widget(btns)
        popup.open()


# ── ExportScreen ──────────────────────────────────────────────────────────────


class ExportScreen(Screen):
    """Single button to export CSV; shows the saved file path."""

    def __init__(self, **kw):
        super().__init__(**kw)
        root = BoxLayout(orientation="vertical", padding=dp(20), spacing=dp(12))

        root.add_widget(
            _make_label(
                "Export Data",
                font_size=BIG_FONT,
                bold=True,
                size_hint_y=None,
                height=dp(50),
            )
        )

        self._status = _make_label(
            "Press Export to save a CSV file.", font_size=MED_FONT
        )
        root.add_widget(self._status)

        export_btn = Button(
            text="Export CSV",
            font_size=BIG_FONT,
            size_hint_y=None,
            height=dp(70),
            background_color=(0.1, 0.4, 0.8, 1),
        )
        export_btn.bind(on_press=self._do_export)
        root.add_widget(export_btn)

        self._nav_placeholder = BoxLayout(size_hint_y=None, height=NAV_HEIGHT)
        root.add_widget(self._nav_placeholder)
        self.add_widget(root)

    def _do_export(self, *_):
        import os

        csv_data = storage.export_csv_string()
        app = App.get_running_app()
        try:
            export_dir = app.user_data_dir
        except Exception:
            export_dir = os.path.dirname(os.path.abspath(__file__))

        filename = datetime.now().strftime("trips_%Y%m%d_%H%M%S.csv")
        path = os.path.join(export_dir, filename)
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(csv_data)
        self._status.text = f"Saved to:\n{path}"


# ── TripApp ───────────────────────────────────────────────────────────────────


class TripApp(App):
    def build(self):
        sm = ScreenManager()

        home = HomeScreen(name="home")
        trips = TripsScreen(name="trips")
        export = ExportScreen(name="export")

        sm.add_widget(home)
        sm.add_widget(trips)
        sm.add_widget(export)

        # Inject shared nav bar into each screen's placeholder
        for screen in (home, trips, export):
            nav = _nav_bar(sm)
            screen._nav_placeholder.add_widget(nav)

        return sm


if __name__ == "__main__":
    TripApp().run()
