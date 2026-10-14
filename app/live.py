"""Live bus positions from BODS and delay estimates."""
import numpy as np
import pandas as pd
import requests
from google.transit import gtfs_realtime_pb2

from app.timetable import Timetable

BODS_URL = "https://data.bus-data.dft.gov.uk/api/v1/gtfsrtdatafeed/"
GM_BOUNDING_BOX = "-2.73,53.33,-1.91,53.69"   # minLon, minLat, maxLon, maxLat


def distance_m(lat1, lon1, lat2, lon2):
    """Distance in metres between GPS points (haversine formula)."""
    R = 6_371_000
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 2 * R * np.arcsin(np.sqrt(a))


def fetch_live_positions(api_key: str, max_age_min: int = 5) -> pd.DataFrame:
    """Download live bus positions for Greater Manchester."""
    params = {"boundingBox": GM_BOUNDING_BOX, "api_key": api_key}
    response = requests.get(BODS_URL, params=params, timeout=30)
    response.raise_for_status()

    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(response.content)

    rows = []
    for entity in feed.entity:
        if not entity.HasField("vehicle"):
            continue
        v = entity.vehicle
        rows.append({
            "trip_id": v.trip.trip_id,
            "vehicle_id": v.vehicle.id,
            "lat": v.position.latitude,
            "lon": v.position.longitude,
            "timestamp": v.timestamp,
        })

    live = pd.DataFrame(rows)
    if live.empty:
        return live

    live["timestamp"] = pd.to_datetime(live["timestamp"], unit="s", utc=True).dt.tz_convert("Europe/London")
    fresh_after = pd.Timestamp.now(tz="Europe/London") - pd.Timedelta(minutes=max_age_min)
    return live[live["timestamp"] >= fresh_after]


def estimate_delays(live: pd.DataFrame, tt: Timetable) -> pd.DataFrame:
    """For each live bus: which stop it has reached and how late it is."""
    empty = pd.DataFrame(columns=["trip_id", "delay_min", "bus_at_seq"])
    if live.empty:
        return empty

    matched = live[live["trip_id"].isin(tt.stop_times["trip_id"])]

    cand = matched.merge(
        tt.stop_times[["trip_id", "stop_id", "stop_sequence", "departure_secs"]], on="trip_id"
    )
    cand = cand.merge(tt.stops[["stop_id", "stop_lat", "stop_lon"]], on="stop_id")
    if cand.empty:
        return empty

    cand["dist_m"] = distance_m(cand["lat"], cand["lon"], cand["stop_lat"], cand["stop_lon"])
    nearest = cand.loc[cand.groupby("trip_id")["dist_m"].idxmin()].copy()

    ts = nearest["timestamp"]
    now_secs = ts.dt.hour * 3600 + ts.dt.minute * 60 + ts.dt.second
    nearest["delay_min"] = (now_secs - nearest["departure_secs"]) / 60

    nearest = nearest[(nearest["dist_m"] < 300) & nearest["delay_min"].between(-10, 60)]
    return nearest[["trip_id", "delay_min", "stop_sequence"]].rename(
        columns={"stop_sequence": "bus_at_seq"}
    )