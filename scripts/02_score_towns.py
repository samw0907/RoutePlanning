# scripts/02_score_towns.py
"""
Step 2: Score the candidate towns.

Fetches existing competitor locations (pawnbrokers, jewellers, gold buyers) from
OpenStreetMap via the Overpass API, measures each town's straight-line distance
to the nearest competitor, min-max normalises the three scoring inputs, and
combines them into a single weighted score.

Scoring inputs, all pointing the same way (higher normalised value = more
attractive):
  - population              larger town, more potential demand
  - share aged 55 and over  older age structure, more relevant demand
  - distance to nearest competitor   further from an existing provider, less
                                     served. This one is a deliberately rough
                                     proxy; absence of competitors may signal
                                     opportunity or simply a thin market.

Distance to competitor is straight-line, which is adequate for a screening score.

Source data and licensing: see DATA_SOURCES.md.
"""

import json
from pathlib import Path

import geopandas as gpd
import pandas as pd
import requests

# --- Configuration ---------------------------------------------------------

# Equal weights to start. Kept as one visible constant so they are easy to change.
WEIGHTS = {
    "population": 1 / 3,
    "share_55_plus": 1 / 3,
    "competitor_distance": 1 / 3,
}

# OSM shop tags treated as existing competitors.
COMPETITOR_SHOP_TAGS = ["pawnbroker", "jewelry", "gold_buyer"]

TARGET_CRS = "EPSG:27700"

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
OVERPASS_TIMEOUT = 180

RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")

TOWNS_GPKG = PROCESSED_DIR / "towns.gpkg"
OSM_CACHE = RAW_DIR / "osm_competitors_scotland.json"
OUT_GPKG = PROCESSED_DIR / "towns_scored.gpkg"


def build_overpass_query():
    """Competitor shops within the Scotland administrative area."""
    tag_lines = "\n".join(
        f'  nwr["shop"="{tag}"](area.scot);' for tag in COMPETITOR_SHOP_TAGS
    )
    return (
        "[out:json][timeout:{t}];\n"
        'area["ISO3166-2"="GB-SCT"][admin_level=4]->.scot;\n'
        "(\n{tags}\n);\n"
        "out center tags;\n"
    ).format(t=OVERPASS_TIMEOUT, tags=tag_lines)


def fetch_competitors():
    """Return the raw Overpass JSON, querying only if the cache is absent."""
    if OSM_CACHE.exists():
        print(f"  using cached {OSM_CACHE.name}")
        return json.loads(OSM_CACHE.read_text(encoding="utf-8"))

    print("  querying Overpass API")
    resp = requests.post(
        OVERPASS_URL,
        data={"data": build_overpass_query()},
        headers={"User-Agent": "scotland-route-analysis/1.0 (open data project)"},
        timeout=OVERPASS_TIMEOUT + 30,
    )
    resp.raise_for_status()
    payload = resp.json()
    OSM_CACHE.write_text(json.dumps(payload), encoding="utf-8")
    return payload


def competitors_geodataframe(payload):
    """Turn Overpass elements into a point GeoDataFrame in the target CRS."""
    rows = []
    for el in payload.get("elements", []):
        if el["type"] == "node":
            lon, lat = el.get("lon"), el.get("lat")
        else:
            center = el.get("center", {})
            lon, lat = center.get("lon"), center.get("lat")
        if lon is None or lat is None:
            continue
        tags = el.get("tags", {})
        rows.append(
            {
                "osm_type": el["type"],
                "osm_id": el["id"],
                "name": tags.get("name", ""),
                "shop": tags.get("shop", ""),
                "lon": lon,
                "lat": lat,
            }
        )
    df = pd.DataFrame(rows)
    gdf = gpd.GeoDataFrame(
        df.drop(columns=["lon", "lat"]),
        geometry=gpd.points_from_xy(df["lon"], df["lat"]),
        crs="EPSG:4326",
    ).to_crs(TARGET_CRS)
    return gdf


def minmax(series):
    """Rescale a series so its minimum is 0 and its maximum is 1."""
    low, high = series.min(), series.max()
    return (series - low) / (high - low)


# --- Main --------------------------------------------------------------------

def main():
    assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9, "weights must sum to 1"
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading towns")
    towns = gpd.read_file(TOWNS_GPKG, layer="towns")
    print(f"  {len(towns)} towns")

    print("Fetching competitor locations from OpenStreetMap")
    competitors = competitors_geodataframe(fetch_competitors())
    counts = competitors["shop"].value_counts()
    print(f"  {len(competitors)} competitor points")
    for tag in COMPETITOR_SHOP_TAGS:
        print(f"    shop={tag}: {int(counts.get(tag, 0))}")

    print("Measuring straight-line distance to the nearest competitor")
    nearest = gpd.sjoin_nearest(
        towns, competitors[["geometry"]], how="left", distance_col="comp_dist_m"
    )
    nearest = nearest[~nearest.index.duplicated(keep="first")]
    towns["comp_dist_m"] = nearest["comp_dist_m"].values

    towns["norm_population"] = minmax(towns["population"])
    towns["norm_share_55_plus"] = minmax(towns["share_55_plus"])
    towns["norm_comp_dist"] = minmax(towns["comp_dist_m"])

    towns["score"] = (
        WEIGHTS["population"] * towns["norm_population"]
        + WEIGHTS["share_55_plus"] * towns["norm_share_55_plus"]
        + WEIGHTS["competitor_distance"] * towns["norm_comp_dist"]
    )

    towns = towns.sort_values("score", ascending=False).reset_index(drop=True)

    if OUT_GPKG.exists():
        OUT_GPKG.unlink()
    towns.to_file(OUT_GPKG, layer="towns_scored", driver="GPKG")
    competitors.to_file(OUT_GPKG, layer="competitors", driver="GPKG")

    print("\n--- Summary ---")
    print(f"Weights: {WEIGHTS}")
    print(
        "Competitor distance (km): "
        f"min {towns['comp_dist_m'].min() / 1000:.1f}, "
        f"median {towns['comp_dist_m'].median() / 1000:.1f}, "
        f"max {towns['comp_dist_m'].max() / 1000:.1f}"
    )
    print(f"\nWrote {OUT_GPKG}")
    print(f"  layer 'towns_scored' {len(towns)} towns")
    print(f"  layer 'competitors'  {len(competitors)} points")

    show = towns.head(20)[
        ["name", "council_area", "population", "share_55_plus", "comp_dist_m", "score"]
    ].copy()
    show["share_55_plus"] = (show["share_55_plus"] * 100).round(1)
    show["comp_dist_km"] = (show["comp_dist_m"] / 1000).round(1)
    show["score"] = show["score"].round(3)
    show = show.drop(columns="comp_dist_m")
    print("\nTop 20 by score:")
    print(show.to_string(index=False))


if __name__ == "__main__":
    main()
