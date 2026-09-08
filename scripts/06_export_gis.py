# scripts/06_export_gis.py
"""
Step 6: Export GIS layers.

Collects the analysis outputs into a single GeoPackage, outputs/gis/scotroute.gpkg,
for manual cartography in QGIS. Every layer is written in EPSG:27700 (British
National Grid). This script does no styling; the map is made by hand.

Layers:
  towns_scored  all 174 shortlisted towns with score attributes (points)
  competitors   OSM pawnbroker / jeweller / gold-buyer points
  isochrones    30, 45 and 60 minute drive-time bands for the top 20 towns
  route_line    road geometry of the sequenced 14-day loop
  route_stops   the ordered stops with day numbers
"""

from pathlib import Path

import geopandas as gpd

TARGET_CRS = "EPSG:27700"

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
        print(f"  {out_layer:<13} {len(gdf):>4} features  {geom_types}")

    print(f"\nAll layers written in {TARGET_CRS}")


if __name__ == "__main__":
    main()
