"""Fetch real Belagavi junction locations and road geometry into simulation/data/belagavi_geo.json.

Usage:  python examples/fetch_belagavi_geo.py

Sources (both free, no API key):
  * OpenStreetMap via Nominatim  - coordinates of the named places (data (c) OpenStreetMap contributors, ODbL)
  * OSRM public demo router      - driving-route geometry between consecutive junctions (routing on OSM data)

The app reads the saved JSON only; nothing is fetched at runtime. Re-run this script to refresh the data.
Please keep to the services' usage policies (identifying User-Agent, ~1 request/second; this script makes ~7 requests).
"""

import json
import os
import time
import urllib.parse
import urllib.request
from datetime import date

UA = {"User-Agent": "QuantumFlow-hackathon-geodata/1.0 (contact: rakesh.sabnis@dfmail.org)"}
OUT = os.path.join(os.path.dirname(__file__), "..", "simulation", "data", "belagavi_geo.json")

# node_id -> (display name, Nominatim query, expected OSM object as "type:id" or None to accept the top bus_station result)
JUNCTIONS = [
    ("I1", "Central Bus Stand", "Belgavi KSRTC Central Bus Stand, Belagavi", None),
    ("I2", "Rani Chennamma Circle", "Rani Chennamma Circle, Belagavi", "way:321455352"),
    ("I3", "Tilak Chowk", "Tilak Chowk, Belagavi", "node:2106608313"),
    ("I4", "Tilakwadi", "Tilakwadi, Belagavi", "node:6039044427"),
]


def http_json(url: str):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        return json.load(r)


def geocode(query: str, expected):
    url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(
        {"q": query, "format": "jsonv2", "limit": 5, "countrycodes": "in"}
    )
    results = http_json(url)
    time.sleep(1.2)
    for r in results:
        key = f"{r['osm_type']}:{r['osm_id']}"
        if (expected and key == expected) or (not expected and r.get("type") == "bus_station"):
            return r
    if expected:  # Nominatim may return a different object for the same place: look the expected one up directly
        prefix = {"node": "N", "way": "W", "relation": "R"}[expected.split(":")[0]]
        url = "https://nominatim.openstreetmap.org/lookup?" + urllib.parse.urlencode(
            {"osm_ids": prefix + expected.split(":")[1], "format": "jsonv2"}
        )
        found = http_json(url)
        time.sleep(1.2)
        if found:
            return found[0]
    raise RuntimeError(f"No suitable OpenStreetMap result for '{query}'")


def main() -> None:
    junctions = []
    for node_id, name, query, expected in JUNCTIONS:
        r = geocode(query, expected)
        junctions.append(
            {
                "node_id": node_id,
                "name": name,
                "lat": round(float(r["lat"]), 6),
                "lon": round(float(r["lon"]), 6),
                "osm": f"{r['osm_type']}/{r['osm_id']}",
                "osm_category": r.get("type"),
                "osm_display_name": r.get("display_name"),
            }
        )
        print(f"{node_id} {name}: {junctions[-1]['lat']}, {junctions[-1]['lon']} ({junctions[-1]['osm']}, {r.get('type')})")

    legs = []
    for a, b in zip(junctions, junctions[1:]):
        url = (
            f"https://router.project-osrm.org/route/v1/driving/{a['lon']},{a['lat']};{b['lon']},{b['lat']}"
            "?overview=full&geometries=geojson"
        )
        route = http_json(url)["routes"][0]
        time.sleep(1.2)
        legs.append(
            {
                "from": a["node_id"],
                "to": b["node_id"],
                "distance_m": round(route["distance"]),
                "duration_s": round(route["duration"]),
                "geometry": [[round(lat, 5), round(lon, 5)] for lon, lat in route["geometry"]["coordinates"]],
            }
        )
        print(f"{a['node_id']}->{b['node_id']}: {legs[-1]['distance_m']} m, {len(legs[-1]['geometry'])} points")

    data = {
        "retrieved": date.today().isoformat(),
        "attribution": "Place locations (c) OpenStreetMap contributors (ODbL), via Nominatim. Route geometry from the OSRM public demo server (OSM data).",
        "note": (
            "Junction coordinates are real OpenStreetMap locations. 'Tilakwadi' is the centroid of the suburb, not a single junction. "
            "The simulator does not model these roads' real signals or traffic; its I1-I4 nodes are mapped onto them for display only."
        ),
        "junctions": junctions,
        "legs": legs,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, ensure_ascii=False)
    print("wrote", os.path.abspath(OUT))


if __name__ == "__main__":
    main()
