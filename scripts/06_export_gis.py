# scripts/06_export_gis.py
"""
Step 6: Export GIS layers.

Collects the analysis outputs into a single GeoPackage, outputs/gis/scotroute.gpkg,
for manual cartography in QGIS. Every layer is written in EPSG:27700 (British
National Grid). This script does no styling; the map is made by hand.

Layers:
  towns_scored          all 174 shortlisted towns with score attributes (points)
  competitors           OSM pawnbroker / jeweller / gold-buyer points
  isochrones            30, 45 and 60 minute drive-time bands for the top 20 towns
  route_line            road geometry of the sequenced 14-day loop
  route_stops           the ordered stops with day numbers
  catchment_localities  mainland localities inside the combined 45-minute
                        catchment, flagged served / underserved (a competitor
                        within LOCAL_COMPETITOR_M counts as served). Visualises
                        that most of the population "reached" already has the
                        service locally. Matches the net figure printed in Step 3.
"""

from pathlib import Path

import geopandas as gpd

TARGET_CRS = "EPSG:27700"

# Must match Step 3.
COVERAGE_BAND_MIN = 45
LOCAL_COMPETITOR_M = 2000

PROCESSED_DIR = Path("data/processed")
OUT_GPKG = Path("outputs/gis/scotroute.gpkg")

# output layer name -> (source GeoPackage, source layer)
LAYERS = {
    "towns_scored": (PROCESSED_DIR / "towns_scored.gpkg", "towns_scored"),
    "competitors": (PROCESSED_DIR / "towns_scored.gpkg", "competitors"),
    "isochrones": (PROCESSED_DIR / "isochrones.gpkg", "isochrones"),
    "route_line": (PROCESSED_DIR / "route.gpkg", "route_line"),
    "route_stops": (PROCESSED_DIR / "route.gpkg", "route_stops"),
}


def build_catchment_localities():
    """Localities inside the combined 45-minute catchment, flagged served or
    underserved by their distance to the nearest competitor."""
    localities = gpd.read_file(PROCESSED_DIR / "towns.gpkg", layer="all_localities")
    isochrones = gpd.read_file(PROCESSED_DIR / "isochrones.gpkg", layer="isochrones")
    competitors = gpd.read_file(PROCESSED_DIR / "towns_scored.gpkg", layer="competitors")
    for gdf in (localities, isochrones, competitors):
        gdf.to_crs(TARGET_CRS, inplace=True)

    catchment = isochrones[isochrones["band_min"] == COVERAGE_BAND_MIN].geometry.union_all()
    inside = localities[localities.intersects(catchment)].copy()

    nearest = gpd.sjoin_nearest(
        inside[["locality_code", "geometry"]],
        competitors[["geometry"]],
        how="left",
        distance_col="comp_dist_m",
    )
    nearest = nearest[~nearest.index.duplicated(keep="first")]
    inside = inside.merge(nearest[["locality_code", "comp_dist_m"]], on="locality_code")
    inside["served"] = inside["comp_dist_m"].lt(LOCAL_COMPETITOR_M).map(
        {True: "served", False: "underserved"}
    )
    return inside[
        ["locality_code", "name", "council_area", "population", "comp_dist_m", "served"]
    ].set_geometry(inside.geometry)


def main():
    OUT_GPKG.parent.mkdir(parents=True, exist_ok=True)
    if OUT_GPKG.exists():
        OUT_GPKG.unlink()

    print(f"Writing {OUT_GPKG}")
    for out_layer, (src_path, src_layer) in LAYERS.items():
        gdf = gpd.read_file(src_path, layer=src_layer)
        if gdf.crs is None:
            raise SystemExit(f"{src_path.name}:{src_layer} has no CRS; cannot export")
        gdf = gdf.to_crs(TARGET_CRS)
        gdf.to_file(OUT_GPKG, layer=out_layer, driver="GPKG")
        geom_types = ", ".join(sorted(gdf.geom_type.unique()))
        print(f"  {out_layer:<20} {len(gdf):>4} features  {geom_types}")

    catchment = build_catchment_localities()
    catchment.to_file(OUT_GPKG, layer="catchment_localities", driver="GPKG")
    served = catchment.loc[catchment["served"] == "served", "population"].sum()
    under = catchment.loc[catchment["served"] == "underserved", "population"].sum()
    print(f"  {'catchment_localities':<20} {len(catchment):>4} features  Point")
    print(f"      served {int(served):,}  underserved {int(under):,}")

    print(f"\nAll layers written in {TARGET_CRS}")


if __name__ == "__main__":
    main()
