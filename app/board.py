"""Departure board: next buses from a stop, with live times where available."""
from datetime import datetime

import pandas as pd

from app.timetable import Timetable


def secs_to_hhmm(s: int) -> str:
    """34920 -> '09:42' (also handles times past midnight)."""
    return f"{(s // 3600) % 24:02d}:{(s % 3600) // 60:02d}"


def live_departures(
    tt: Timetable,
    stop_name: str,
    bus_pos: pd.DataFrame,
    limit: int = 10,
    when: datetime | None = None,
) -> pd.DataFrame:
    """Next departures from every stop matching a name."""
    when = when or datetime.now()
    now_secs = when.hour * 3600 + when.minute * 60 + when.second

    stop_ids = tt.find_stops(stop_name)["stop_id"]
    trips_today = tt.trips[tt.trips["service_id"].isin(tt.services_on(when.date()))]

    st = tt.stop_times
    deps = st[
        st["stop_id"].isin(stop_ids)
        & st["trip_id"].isin(trips_today["trip_id"])
        & (st["departure_secs"] >= now_secs - 3600)   # look back for late buses
        & (~st["is_last_stop"])
    ]

    deps = deps.merge(bus_pos, on="trip_id", how="left")
    deps = deps[deps["bus_at_seq"].isna() | (deps["stop_sequence"] >= deps["bus_at_seq"])].copy()

    deps["live"] = deps["bus_at_seq"].notna()
    deps["real_secs"] = deps["departure_secs"] + (deps["delay_min"].fillna(0) * 60).round().astype(int)
    deps = deps[deps["real_secs"] >= now_secs]

    deps = deps.merge(trips_today[["trip_id", "route_id", "trip_headsign"]], on="trip_id")
    deps = deps.merge(tt.routes[["route_id", "route_short_name"]], on="route_id")

    deps = deps.sort_values("real_secs").drop_duplicates("trip_id").head(limit)
    deps["time"] = deps["real_secs"].apply(secs_to_hhmm)
    deps["due_in_min"] = (deps["real_secs"] - now_secs) // 60

    return deps.rename(columns={"route_short_name": "route", "trip_headsign": "to"})[
        ["route", "to", "time", "due_in_min", "live"]
    ].reset_index(drop=True)