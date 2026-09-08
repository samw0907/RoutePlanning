# scripts/01_prepare_towns.py
"""
Step 1: Prepare the candidate towns.

Downloads the National Records of Scotland mid-2020 locality boundaries and
population estimates, filters to mainland Scotland localities with a population
of at least MIN_POPULATION, attaches the share of population aged 55 and over,
computes a representative point for routing, and writes data/processed/towns.gpkg.

Source data and licensing: see DATA_SOURCES.md.
"""

from pathlib import Path

import geopandas as gpd
import pandas as pd
import requests

# --- Configuration ---------------------------------------------------------

# Candidate town threshold. One clearly named constant so it is easy to change.
MIN_POPULATION = 5000

# Mainland filter: exclude localities in the three island council areas.
# This is the attribute filter (option 1 in DATA_SOURCES.md).
ISLAND_COUNCIL_AREAS = ["Na h-Eileanan Siar", "Orkney Islands", "Shetland Islands"]

# British National Grid. Everything is stored and exported in this CRS.
TARGET_CRS = "EPSG:27700"

RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")

BOUNDARY_ZIP = RAW_DIR / "settlements_localities_shapefiles_mid2020.zip"
DATA_TABLES = RAW_DIR / "settlements_localities_data_tables_mid2020.xlsx"

BOUNDARY_URL = "https://www.nrscotland.gov.uk/media/2hsoadnx/shapefiles.zip"
DATA_TABLES_URL = "https://www.nrscotland.gov.uk/media/wtwjdfuo/data-tables.xlsx"

# Locality polygons bounded to mean high water.
LOCALITY_LAYER = "Localities2020_MHW"

# A few localities straddle a council boundary and are listed by NRS under two
# council areas. The council field here is descriptive only (the island filter is
# unaffected), so record the council the built-up area principally sits in.
PRIMARY_COUNCIL_OVERRIDES = {
    "S19002137": "Dundee City",        # Dundee
    "S19002206": "Glasgow City",       # Glasgow
    "S19002233": "North Lanarkshire",  # Harthill
    "S19002268": "Fife",               # Kelty
    "S19002329": "Angus",              # Liff
    "S19002509": "North Lanarkshire",  # Stepps
}

# Five-year bands that make up the 55-and-over group, as named in Table 3.2.
AGE_BANDS_55_PLUS = [
    "55 to 59", "60 to 64", "65 to 69", "70 to 74",
    "75 to 79", "80 to 84", "85 to 89", "90 & over",
]

OUT_GPKG = PROCESSED_DIR / "towns.gpkg"
OUT_COLUMNS = [
    "locality_code", "name", "council_area",
    "population", "pop_55_plus", "share_55_plus",
]


# --- Helpers -------------------------------------------------------------------

def download_if_missing(url, path):
    """Fetch url to path only if it is not already present. Raw files are
    treated as read-only once fetched and are never re-downloaded."""
    if path.exists():
        print(f"  using cached {path.name}")
        return
    print(f"  downloading {path.name}")
    resp = requests.get(url, timeout=120)
    resp.raise_for_status()
    path.write_bytes(resp.content)


def representative_points(geoms):
    """Centroid of each polygon, or a guaranteed-interior point where the
    centroid falls outside the polygon. Returns the points and a count of the
    fallbacks used."""
    points, fallbacks = [], 0
    for geom in geoms:
        centroid = geom.centroid
        if geom.contains(centroid):
            points.append(centroid)
        else:
            points.append(geom.representative_point())
            fallbacks += 1
    return points, fallbacks


# --- Main --------------------------------------------------------------------

def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    print("Fetching source data")
    download_if_missing(BOUNDARY_URL, BOUNDARY_ZIP)
    download_if_missing(DATA_TABLES_URL, DATA_TABLES)

    print("\nReading locality boundaries")
    localities = gpd.read_file(BOUNDARY_ZIP, layer=LOCALITY_LAYER)
    localities = localities.to_crs(TARGET_CRS)
    localities = localities[["code", "name", "geometry"]]
    print(f"  {len(localities)} localities in the boundary file")

    print("Reading population and age estimates (Table 3.2)")
    pop = pd.read_excel(DATA_TABLES, sheet_name="Table_3.2", skiprows=3)
    pop = pop[pop["Sex"] == "All"].copy()
    pop["population"] = pd.to_numeric(pop["All ages"]).astype(int)
    bands = pop[AGE_BANDS_55_PLUS].apply(pd.to_numeric, errors="coerce").fillna(0)
    pop["pop_55_plus"] = bands.sum(axis=1).astype(int)
    pop = pop.rename(columns={"Locality code": "locality_code"})
    pop = pop[["locality_code", "population", "pop_55_plus"]]

    print("Reading council areas (Table 1.2)")
    council = pd.read_excel(DATA_TABLES, sheet_name="Table_1.2", skiprows=3)
    council = council.iloc[:, [1, 4]]
    council.columns = ["locality_code", "council_area"]
    council = council.drop_duplicates(subset="locality_code", keep="first")
    council["council_area"] = council.apply(
        lambda r: PRIMARY_COUNCIL_OVERRIDES.get(r["locality_code"], r["council_area"]),
        axis=1,
    )

    towns = localities.merge(
        pop, left_on="code", right_on="locality_code", how="inner"
    )
    towns = towns.merge(council, on="locality_code", how="left")
    n_source = len(towns)

    towns = towns[~towns["council_area"].isin(ISLAND_COUNCIL_AREAS)].copy()
    n_mainland = len(towns)

    towns = towns[towns["population"] >= MIN_POPULATION].copy()
    n_final = len(towns)

    points, fallbacks = representative_points(towns.geometry)
    towns["rep_point"] = gpd.GeoSeries(points, index=towns.index, crs=towns.crs)
    towns["share_55_plus"] = towns["pop_55_plus"] / towns["population"]

    towns = towns.sort_values("population", ascending=False).reset_index(drop=True)

    town_points = gpd.GeoDataFrame(
        towns[OUT_COLUMNS].copy(), geometry=towns["rep_point"].values, crs=TARGET_CRS
    )
    town_polygons = gpd.GeoDataFrame(
        towns[OUT_COLUMNS].copy(), geometry=towns["geometry"].values, crs=TARGET_CRS
    )

    if OUT_GPKG.exists():
        OUT_GPKG.unlink()
    town_points.to_file(OUT_GPKG, layer="towns", driver="GPKG")
    town_polygons.to_file(OUT_GPKG, layer="towns_poly", driver="GPKG")

    print("\n--- Summary ---")
    print("Mainland filter: council area attribute filter (DATA_SOURCES.md option 1)")
    print(f"Localities with a boundary and population estimate: {n_source}")
    print(f"After mainland filter: {n_mainland}  "
          f"(removed {n_source - n_mainland} island localities)")
    print(f"After population >= {MIN_POPULATION:,}: {n_final}")
    print(f"Representative point: centroid for {n_final - fallbacks}, "
          f"point-on-surface fallback for {fallbacks}")
    print(f"Population range: {towns['population'].min():,} to "
          f"{towns['population'].max():,}, median {int(towns['population'].median()):,}")
    print(f"55+ share range: {towns['share_55_plus'].min():.1%} to "
          f"{towns['share_55_plus'].max():.1%}")
    print(f"\nWrote {OUT_GPKG}")
    print(f"  layer 'towns'      {len(town_points)} representative points")
    print(f"  layer 'towns_poly' {len(town_polygons)} locality polygons")

    show = ["name", "council_area", "population", "share_55_plus"]
    print("\nTop 10 by population:")
    print(towns.head(10)[show].to_string(index=False))
    print("\nSmallest 10 above the threshold:")
    print(towns.tail(10)[show].to_string(index=False))


if __name__ == "__main__":
    main()
