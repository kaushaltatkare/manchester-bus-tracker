"""Geography helpers."""
import numpy as np


def distance_m(lat1, lon1, lat2, lon2):
    """Distance in metres between GPS points (haversine formula)."""
    R = 6_371_000
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 2 * R * np.arcsin(np.sqrt(a))