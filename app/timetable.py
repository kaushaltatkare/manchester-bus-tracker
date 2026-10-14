"""Timetable data for Greater Manchester: stops, trips, routes and calendars."""
from datetime import date
from pathlib import Path

import pandas as pd

from app.geo import distance_m

# Paths work no matter where you run the code from
PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW = PROJECT_ROOT / "data" / "raw" / "itm_north_west_gtfs"
PROC = PROJECT_ROOT / "data" / "processed"


class Timetable:
    """Loads the Manchester timetable once and answers questions about it."""

    def __init__(self):
        self.stops = pd.read_parquet(PROC / "gm_stops.parquet")
        self.stop_times = pd.read_parquet(PROC / "gm_stop_times.parquet")
        self.trips = pd.read_parquet(PROC / "gm_trips.parquet")
        self.routes = pd.read_parquet(PROC / "gm_routes.parquet")

        self.calendar = pd.read_csv(
            RAW / "calendar.txt",
            dtype={"service_id": str, "start_date": str, "end_date": str},
        )
        self.calendar_dates = pd.read_csv(
            RAW / "calendar_dates.txt",
            dtype={"service_id": str, "date": str},
        )

        # Mark each trip's last stop (buses ending here can't be boarded)
        last_seq = self.stop_times.groupby("trip_id")["stop_sequence"].transform("max")
        self.stop_times["is_last_stop"] = self.stop_times["stop_sequence"] == last_seq

    def find_stops(self, name: str) -> pd.DataFrame:
        """Search stops by name (not case-sensitive)."""
        matches = self.stops[self.stops["stop_name"].str.contains(name, case=False, na=False)]
        return matches[["stop_id", "stop_name", "stop_lat", "stop_lon"]]

    def stops_named(self, exact_name: str) -> pd.Series:
        """stop_ids whose name matches exactly (not case-sensitive)."""
        mask = self.stops["stop_name"].str.lower() == exact_name.lower()
        return self.stops.loc[mask, "stop_id"]

    def nearby_stops(self, lat: float, lon: float, limit: int = 5) -> pd.DataFrame:
        """Closest stop names to a GPS position, nearest first."""
        s = self.stops.copy()
        s["distance_m"] = distance_m(lat, lon, s["stop_lat"], s["stop_lon"])
        nearest = s.groupby("stop_name", as_index=False)["distance_m"].min()
        nearest["distance_m"] = nearest["distance_m"].round().astype(int)
        return nearest.sort_values("distance_m").head(limit)

    def services_on(self, day: date) -> set:
        """Service IDs running on a date, including bank holiday exceptions."""
        weekday = day.strftime("%A").lower()
        date_str = day.strftime("%Y%m%d")

        cal = self.calendar
        running = cal[
            (cal[weekday] == 1)
            & (cal["start_date"] <= date_str)
            & (cal["end_date"] >= date_str)
        ]
        services = set(running["service_id"])

        exc = self.calendar_dates[self.calendar_dates["date"] == date_str]
        added = set(exc.loc[exc["exception_type"] == 1, "service_id"])
        removed = set(exc.loc[exc["exception_type"] == 2, "service_id"])
        return (services | added) - removed