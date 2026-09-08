# scripts/04_build_route.py
"""
Step 4: Build the touring route.

Takes the top ROUTE_TOWNS scored towns, builds a road distance and duration
matrix between them with the OpenRouteService matrix endpoint, constructs an
initial closed tour with the nearest-neighbour heuristic (run from every possible
start, keeping the shortest), then improves it with a 2-opt pass until no
reversal shortens the tour.

The tour is a closed loop, so its start is arbitrary. For presentation the
sequence is rotated to begin at the largest town in the loop, which is a sensible
operational entry point, not an optimisation result. One town is assigned per day
across 14 days. The real road geometry for the whole loop is fetched from the ORS
directions endpoint so the route can be drawn on a map.

The tour is optimised on road distance. Driving time is reported but not the
objective.

Requires an OpenRouteService API key as ORS_API_KEY (shell environment or a .env
file in the project root). Responses are cached under data/raw/route/.
"""

import json
import os
from pathlib import Path

import geopandas as gpd
import requests
from dotenv import load_dotenv
from shapely.geometry import shape

# --- Configuration ---------------------------------------------------------

ROUTE_TOWNS = 14          # number of top-scored towns to route, one per day
TOUR_DAYS = 14

TARGET_CRS = "EPSG:27700"
WGS84 = "EPSG:4326"

ORS_MATRIX_URL = "https://api.openrouteservice.org/v2/matrix/driving-car"
ORS_DIRECTIONS_URL = "https://api.openrouteservice.org/v2/directions/driving-car/geojson"

PROCESSED_DIR = Path("data/processed")
RAW_ROUTE_DIR = Path("data/raw/route")

SCORED_GPKG = PROCESSED_DIR / "towns_scored.gpkg"
OUT_GPKG = PROCESSED_DIR / "route.gpkg"
MATRIX_CACHE = RAW_ROUTE_DIR / "matrix.json"
DIRECTIONS_CACHE = RAW_ROUTE_DIR / "directions.json"


def get_api_key():
    load_dotenv()
    key = os.environ.get("ORS_API_KEY")
    if not key:
        raise SystemExit(
            "ORS_API_KEY is not set. Set it in your shell environment or a .env "
            "file in the project root, then re-run."
        )
    return key


def ors_post(url, body, api_key):
    resp = requests.post(
        url,
        json=body,
        headers={"Authorization": api_key, "Content-Type": "application/json"},
        timeout=90,
    )
    if not resp.ok:
        raise SystemExit(f"OpenRouteService returned {resp.status_code}:\n{resp.text}")
    return resp.json()


def load_matrix(coords, codes, api_key):
    """Road distance (km) and duration (minutes) matrices, from cache when the
    cached town set matches."""
    if MATRIX_CACHE.exists():
        cached = json.loads(MATRIX_CACHE.read_text(encoding="utf-8"))
        if cached.get("codes") == codes:
            return cached["distances_km"], cached["durations_min"]

    payload = ors_post(
        ORS_MATRIX_URL,
        {"locations": coords, "metrics": ["distance", "duration"], "units": "km"},
        api_key,
    )
    distances_km = payload["distances"]
    durations_min = [[v / 60 for v in row] for row in payload["durations"]]
    MATRIX_CACHE.write_text(
        json.dumps({"codes": codes, "distances_km": distances_km,
                    "durations_min": durations_min}),
        encoding="utf-8",
    )
    return distances_km, durations_min


def load_route_geometry(coords, codes, api_key):
    """Full-loop road geometry and its ORS distance/time summary, from cache when
    the cached town set matches."""
    if DIRECTIONS_CACHE.exists():
        cached = json.loads(DIRECTIONS_CACHE.read_text(encoding="utf-8"))
        if cached.get("codes") == codes:
            return shape(cached["geometry"]), cached["distance_km"], cached["duration_min"]

    payload = ors_post(ORS_DIRECTIONS_URL, {"coordinates": coords}, api_key)
    feature = payload["features"][0]
    summary = feature["properties"]["summary"]
    geometry = shape(feature["geometry"])
    distance_km = summary["distance"] / 1000
    duration_min = summary["duration"] / 60
    DIRECTIONS_CACHE.write_text(
        json.dumps({"codes": codes, "geometry": feature["geometry"],
                    "distance_km": distance_km, "duration_min": duration_min}),
        encoding="utf-8",
    )
    return geometry, distance_km, duration_min


# --- Tour construction and improvement --------------------------------------

def tour_length(tour, dist):
    n = len(tour)
    return sum(dist[tour[i]][tour[(i + 1) % n]] for i in range(n))


def nearest_neighbour(start, dist):
    """Closed tour built by always hopping to the closest unvisited town."""
    unvisited = set(range(len(dist)))
    unvisited.remove(start)
    tour = [start]
    while unvisited:
        last = tour[-1]
        nxt = min(unvisited, key=lambda k: dist[last][k])
        tour.append(nxt)
        unvisited.remove(nxt)
    return tour


def two_opt(tour, dist):
    """Repeatedly reverse a segment of the tour whenever that shortens it."""
    n = len(tour)
    improved = True
    while improved:
        improved = False
        for i in range(n - 1):
            for j in range(i + 2, n):
                if i == 0 and j == n - 1:
                    continue  # this reversal just flips the whole loop
                a, b = tour[i], tour[i + 1]
                c, d = tour[j], tour[(j + 1) % n]
                if (dist[a][c] + dist[b][d]) < (dist[a][b] + dist[c][d]) - 1e-9:
                    tour[i + 1:j + 1] = reversed(tour[i + 1:j + 1])
                    improved = True
    return tour


# --- Main ------------------------------------------------------------------

def main():
    api_key = get_api_key()
    RAW_ROUTE_DIR.mkdir(parents=True, exist_ok=True)

    towns = gpd.read_file(SCORED_GPKG, layer="towns_scored").head(ROUTE_TOWNS)
    towns = towns.reset_index(drop=True)
    codes = towns["locality_code"].tolist()
    names = towns["name"].tolist()
    pops = towns["population"].tolist()

    towns_wgs = towns.to_crs(WGS84)
    coords = [[p.x, p.y] for p in towns_wgs.geometry]

    print(f"Building a {ROUTE_TOWNS}-town route")
    dist_km, dur_min = load_matrix(coords, codes, api_key)

    start_tours = [nearest_neighbour(s, dist_km) for s in range(len(codes))]
    nn_tour = min(start_tours, key=lambda t: tour_length(t, dist_km))
    nn_len = tour_length(nn_tour, dist_km)

    tour = two_opt(list(nn_tour), dist_km)
    opt_len = tour_length(tour, dist_km)

    # Rotate the loop to start at its largest town (the operational entry point).
    entry_pos = max(range(len(tour)), key=lambda p: pops[tour[p]])
    tour = tour[entry_pos:] + tour[:entry_pos]

    # Per-day schedule. Day 1 has no preceding day; the leg back from the final
    # day to day 1 is reported separately as the closing leg.
    rows = []
    cumulative = 0.0
    for day, node in enumerate(tour, start=1):
        prev = tour[day - 2] if day > 1 else None
        leg_km = dist_km[prev][node] if prev is not None else 0.0
        leg_min = dur_min[prev][node] if prev is not None else 0.0
        cumulative += leg_km
        rows.append({
            "day": day,
            "locality_code": codes[node],
            "name": names[node],
            "council_area": towns.loc[node, "council_area"],
            "population": int(pops[node]),
            "score": round(float(towns.loc[node, "score"]), 3),
            "leg_km": round(leg_km, 1),
            "leg_min": round(leg_min, 1),
            "cum_km": round(cumulative, 1),
            "geometry": towns.loc[node, "geometry"],
        })
    closing_km = dist_km[tour[-1]][tour[0]]
    closing_min = dur_min[tour[-1]][tour[0]]
    loop_km = cumulative + closing_km
    loop_min = sum(r["leg_min"] for r in rows) + closing_min

    route_stops = gpd.GeoDataFrame(rows, geometry="geometry", crs=TARGET_CRS)

    # Real road geometry for the full closed loop.
    loop_coords = [coords[n] for n in tour] + [coords[tour[0]]]
    geom_wgs, road_km, road_min = load_route_geometry(loop_coords, codes, api_key)
    route_line = gpd.GeoDataFrame(
        [{"stops": len(tour), "days": TOUR_DAYS,
          "distance_km": round(road_km, 1), "duration_min": round(road_min, 1)}],
        geometry=[geom_wgs], crs=WGS84,
    ).to_crs(TARGET_CRS)

    if OUT_GPKG.exists():
        OUT_GPKG.unlink()
    route_stops.to_file(OUT_GPKG, layer="route_stops", driver="GPKG")
    route_line.to_file(OUT_GPKG, layer="route_line", driver="GPKG")

    print("\n--- Summary ---")
    print(f"Optimised on road distance. Nearest-neighbour then 2-opt.")
    print(f"Nearest-neighbour tour: {nn_len:,.0f} km")
    print(f"After 2-opt:            {opt_len:,.0f} km  "
          f"({(nn_len - opt_len) / nn_len:.0%} shorter)")
    print(f"Closed loop total:     {loop_km:,.0f} km, {loop_min / 60:,.1f} h driving")
    print(f"ORS road geometry:     {road_km:,.0f} km, {road_min / 60:,.1f} h "
          f"(independent check via directions endpoint)")
    print(f"Entry point (largest town in loop): {route_stops.iloc[0]['name']} "
          f"({route_stops.iloc[0]['population']:,})")
    print(f"\nWrote {OUT_GPKG}")
    print(f"  layer 'route_stops' {len(route_stops)} ordered stops")
    print(f"  layer 'route_line'  1 road geometry")

    print("\nDay-by-day schedule:")
    sched = route_stops[["day", "name", "council_area", "population", "leg_km",
                         "leg_min", "cum_km"]].copy()
    print(sched.to_string(index=False))
    print(f" close  {route_stops.iloc[-1]['name']} -> {route_stops.iloc[0]['name']}"
          f"   {closing_km:,.1f} km  {closing_min:,.1f} min")


if __name__ == "__main__":
    main()
