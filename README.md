# Scotland Mobile Service Route Analysis

A small, self-contained geospatial analysis that answers one question:

> If a mobile precious-metals and valuables buying service operated a two-week touring
> route across mainland Scotland, which towns should it visit, and in what order?

Services in this category — often advertised as "we buy your gold" — park a vehicle in
a town for a short scheduled stop, take appointments, then move on. Demand for this kind
of service depends on what people already own rather than what they currently need, so
an older population is a more informative signal than population alone, and pawnbrokers,
jewellers and gold buyers are the closest thing to direct competition. Because customers
travel to the vehicle, demand is also drawn from a drive-time catchment rather than the
town itself, so a simple "visit the biggest towns" approach is inadequate. This project
screens candidate towns on three transparent measures, assesses drive-time coverage, and
sequences a fortnight-long touring loop.

## Scope

- Mainland Scotland only. Islands are excluded to avoid ferry routing.
- Candidate towns are National Records of Scotland localities with a population of
  roughly 5,000 or above.
- Towns are scored on three inputs only: population, share of population aged 55 and
  over (a proxy for accumulated valuables), and straight-line distance to the nearest
  existing pawnbroker, jeweller or gold buyer.
- The route is a closed loop with no fixed depot, 14 days, one town per day.
- Sequencing uses a nearest-neighbour construction followed by a 2-opt improvement pass.

This is a demonstration of method. It does not model any specific company's operations
and makes no claim about how real businesses plan routes. Scoring inputs are stated as
reasonable proxies, not established facts.

## Data sources

All open data. See `DATA_SOURCES.md` for provenance and licensing.

- National Records of Scotland: locality boundaries and population estimates
- OpenStreetMap via the Overpass API: competitor locations
- OpenRouteService: isochrones, distance matrix and route geometry (free API key required)

## Running the scripts

Install dependencies:

```
pip install -r requirements.txt
```

Run the scripts in order from the project root. Each writes its output to
`data/processed/` or `outputs/` and prints a short summary.

```
python scripts/01_prepare_towns.py
python scripts/02_score_towns.py
python scripts/03_isochrones.py      # requires an OpenRouteService API key
python scripts/04_build_route.py     # requires an OpenRouteService API key
python scripts/05_export_excel.py
python scripts/06_export_gis.py
```

An OpenRouteService API key is needed for steps 3 and 4. Sign up at
https://openrouteservice.org/dev/#/signup, then provide the key as `ORS_API_KEY`,
either as an environment variable or on a single line in a `.env` file in the
project root:

```
ORS_API_KEY=your_token_here
```

The `.env` file is git-ignored. The free tier is sufficient for this project.

## Outputs

- `outputs/scotland_route_analysis.xlsx` — formatted workbook of town scores and the
  route schedule
- `outputs/gis/scotroute.gpkg` — GeoPackage layers for manual cartography in QGIS

The final poster is produced manually in QGIS and is not part of the scripted pipeline.
