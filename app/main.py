"""Manchester Bus Tracker API."""
import os
import time

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException

from app.board import live_departures
from app.live import estimate_delays, fetch_live_positions
from app.timetable import Timetable

load_dotenv()
API_KEY = os.getenv("BODS_API_KEY")

app = FastAPI(title="Manchester Bus Tracker")

# Load the timetable ONCE when the server starts (takes ~20 seconds)
tt = Timetable()

# Simple cache: reuse live data for 30 seconds instead of downloading on every request
_cache = {"bus_pos": None, "fetched_at": 0.0}
CACHE_SECONDS = 30


def get_bus_pos():
    """Return live delays, refreshing from BODS at most every 30 seconds."""
    if time.time() - _cache["fetched_at"] > CACHE_SECONDS:
        live = fetch_live_positions(API_KEY)
        _cache["bus_pos"] = estimate_delays(live, tt)
        _cache["fetched_at"] = time.time()
    return _cache["bus_pos"]


@app.get("/")
def home():
    return {"message": "Manchester Bus Tracker API is running"}


@app.get("/stops/search")
def search_stops(name: str):
    """Find stops by name, e.g. /stops/search?name=Piccadilly"""
    results = tt.find_stops(name).head(20)
    return results.to_dict(orient="records")


@app.get("/departures")
def departures(stop: str, limit: int = 10):
    """Next departures from a stop, e.g. /departures?stop=Oxford Road"""
    if tt.find_stops(stop).empty:
        raise HTTPException(status_code=404, detail=f"No stops found matching '{stop}'")
    board = live_departures(tt, stop, get_bus_pos(), limit=limit)
    return board.to_dict(orient="records")