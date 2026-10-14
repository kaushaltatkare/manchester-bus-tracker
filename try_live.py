import os
from dotenv import load_dotenv

from app.timetable import Timetable
from app.live import fetch_live_positions, estimate_delays

load_dotenv()
tt = Timetable()
live = fetch_live_positions(os.getenv("BODS_API_KEY"))
bus_pos = estimate_delays(live, tt)

print("Fresh live vehicles:", len(live))
print("Buses with a trusted delay:", len(bus_pos))
print("Typical delay: {:.1f} min".format(bus_pos["delay_min"].median()))