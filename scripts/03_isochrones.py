# scripts/03_isochrones.py
"""
Step 3: Drive-time coverage.

For the top N scored towns, requests 30, 45 and 60 minute driving isochrones from
OpenRouteService, then estimates the population within the 45 minute band by
intersecting the combined catchment with every mainland locality point and
summing their populations.

Method note: this counts locality (defined urban area) population only. Population
living outside any defined locality, i.e. dispersed rural population, is not
counted, so the coverage figure understates true reach.

Requires an OpenRouteService API key. Set it as ORS_API_KEY, either in your shell
environment or in a .env file in the project root (loaded automatically here).
Sign-up: https://openrouteservice.org/dev/#/signup.

Every API response is cached under data/raw/isochrones/ and reused on later runs.
"""

import json
import os
import time
from pathlib import Path

import geopandas as gpd
import requests
from dotenv import load_dotenv
from shapely.geometry import shape

# --- Configuration ---------------------------------------------------------

N_TOWNS = 20                        # number of top-scored towns to profile
ISOCHRONE_MINUTES = [30, 45, 60]
COVERAGE_BAND_MIN = 45             # band used for the population estimate

# Polite spacing between calls. The free tier allows about 20 isochrone
# requests per minute; one request per town covers all three bands.
REQUEST_DELAY_S = 3

TARGET_CRS = "EPSG:27700"
WGS84 = "EPSG:4326"

ORS_ISOCHRONES_URL = "https://api.openrouteservice.org/v2/isochrones/driving-car"

PROCESSED_DIR = Path("data/processed")
RAW_ISO_DIR = Path("data/raw/isochrones")

SCORED_GPKG = PROCESSED_DIR / "towns_scored.gpkg"
TOWNS_GPKG = PROCESSED_DIR / "towns.gpkg"
OUT_GPKG = PROCESSED_DIR / "isochrones.gpkg"


def get_api_key():
    load_dotenv()  # picks up ORS_API_KEY from a .env file in the project root
    key = os.environ.get("ORS_API_KEY")
    if not key:
        raise SystemExit(
            "ORS_API_KEY is not set.\n"
            "Obtain a free key at https://openrouteservice.org/dev/#/signup and set "
            "it as ORS_API_KEY, in your shell environment or a .env file in the "
            "project root, then re-run."
        )
    return key


def fetch_isochrone(code, lon, lat, api_key):
    """Return the raw ORS isochrone response for one town, from cache if present."""
    cache = RAW_ISO_DIR / f"{code}.json"
    if cache.exists():
        print("    cached")
        return json.loads(cache.read_text(encoding="utf-8"))

    body = {
        "locations": [[lon, lat]],
        "range": [minutes * 60 for minutes in ISOCHRONE_MINUTES],
        "range_type": "time",
    }
    resp = requests.post(
        ORS_ISOCHRONES_URL,
        json=body,
        headers={"Authorization": api_key, "Content-Type": "application/json"},
        timeout=60,
    )
    if not resp.ok:
        raise SystemExit(
            f"OpenRouteService returned {resp.status_code} for {code}:\n{resp.text}"
        )
    payload = resp.json()
    cache.write_text(json.dumps(payload), encoding="utf-8")
    time.sleep(REQUEST_DELAY_S)
    return payload


def isochrone_rows(payload, code, name):
    """One row per range band in an ORS response."""
    rows = []
    for feature in payload["features"]:
        seconds = feature["properties"]["value"]
        rows.append(
            {
                "locality_code": code,
                "name": name,
                "band_min": int(round(seconds / 60)),
                "geometry": shape(feature["geometry"]),
            }
        )
    return rows


# --- Main --------------------------------------------------------------------

def main():
    api_key = get_api_key()
    RAW_ISO_DIR.mkdir(parents=True, exist_ok=True)

    scored = gpd.read_file(SCORED_GPKG, layer="towns_scored").head(N_TOWNS)
    scored_wgs = scored.to_crs(WGS84)
    print(f"Requesting isochrones for the top {len(scored)} scored towns")

    rows = []
    for (_, town), (_, town_wgs) in zip(scored.iterrows(), scored_wgs.iterrows()):
        code, name = town["locality_code"], town["name"]
        print(f"  {name} ({code})")
        payload = fetch_isochrone(code, town_wgs.geometry.x, town_wgs.geometry.y, api_key)
        rows.extend(isochrone_rows(payload, code, name))

    isochrones = gpd.GeoDataFrame(rows, geometry="geometry", crs=WGS84).to_crs(TARGET_CRS)

    localities = gpd.read_file(TOWNS_GPKG, layer="all_localities")
    band = isochrones[isochrones["band_min"] == COVERAGE_BAND_MIN]
    catchment = band.geometry.union_all()
    covered = localities[localities.intersects(catchment)]
    covered_pop = int(covered["population"].sum())
    total_pop = int(localities["population"].sum())

    per_town = (
        gpd.GeoDataFrame(
            [
                {"name": r["name"],
                 "pop_45min": int(localities[localities.intersects(r.geometry)]["population"].sum())}
                for _, r in band.iterrows()
            ]
        )
        .sort_values("pop_45min", ascending=False)
        .reset_index(drop=True)
    )

    if OUT_GPKG.exists():
        OUT_GPKG.unlink()
    isochrones.to_file(OUT_GPKG, layer="isochrones", driver="GPKG")

    print("\n--- Summary ---")
    print(f"Towns profiled: {len(scored)} (top {N_TOWNS} by score)")
    print(f"Bands: {ISOCHRONE_MINUTES} minutes, driving-car profile")
    print(
        f"\nCombined {COVERAGE_BAND_MIN}-minute catchment reaches "
        f"{len(covered)} of {len(localities)} mainland localities"
    )
    print(f"Locality population within {COVERAGE_BAND_MIN} minutes of a profiled town: "
          f"{covered_pop:,}")
    print(f"  {covered_pop / total_pop:.1%} of the {total_pop:,} mainland locality population")
    print("  (locality population only; dispersed rural population is not counted)")
    print(f"\nWrote {OUT_GPKG} with layer 'isochrones' ({len(isochrones)} polygons)")
    print(f"\nPer-town {COVERAGE_BAND_MIN}-minute locality population:")
    print(per_town.to_string(index=False))


if __name__ == "__main__":
    main()
