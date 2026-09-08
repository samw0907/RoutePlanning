# Data Sources

All sources are open data. Verify each landing page before downloading, as URLs and file
names change between publications.

---

## 1. Locality boundaries and population

**National Records of Scotland — Population estimates for settlements and localities**

Landing page:
https://www.nrscotland.gov.uk/publications/population-estimates-for-settlements-and-localities-in-scotland-mid-2020/

Catalogue entry (check for a newer edition, the dataset was last updated July 2026):
https://www.data.gov.uk/dataset/3ab7d334-fb35-4868-875c-165de9d25b58/population_estimates_for_settlements_and_localities

Open Data Scotland mirror:
https://opendata.scot/datasets/national+records+of+scotland-settlements+and+localities+population/

Boundary geometry:
https://www.data.gov.uk/dataset/de5ad374-53b7-474f-b1c0-725687af1ed4/settlements-scotland

Notes:

- Two related geographies exist. Settlements are contiguous built-up areas; localities are
  subdivisions of the larger settlements. Use **localities**, since they correspond to
  recognisable individual towns. A large settlement such as Greater Glasgow splits into many
  localities, which is the behaviour we want.
- The population tables are published as Excel workbooks with a header block above the data.
  Expect to skip rows when reading.
- Age breakdowns are published alongside the headline estimates in the same publication.
  Confirm the exact band boundaries before computing a 55+ share; the bands may not align
  neatly and may need summing across several columns.
- **If age bands turn out not to be available at locality level, stop and escalate.** The
  fallback is a spatial join from data zone estimates, which is more work and introduces
  boundary-mismatch error, and that trade-off should be a decision rather than an assumption.
- Licence: Open Government Licence. Attribution required on any published map.

---

## 2. Mainland filter

There is no single authoritative "mainland Scotland" dataset. Two workable approaches:

1. Attribute filter, excluding localities in the Na h-Eileanan Siar, Orkney Islands and
   Shetland Islands council areas. Simplest if a council area field is present in the
   boundary data.
2. Spatial filter against the largest landmass polygon.

Prefer option 1. Report which was used.

Note that this filter removes island localities but does not remove mainland localities that
happen to be remote. Places such as Campbeltown remain in scope despite long drive times,
which is correct: they are reachable by road.

---

## 3. Competitor locations

**OpenStreetMap, via the Overpass API**

Endpoint: https://overpass-api.de/api/interpreter

Relevant tags:

- `shop=pawnbroker`
- `shop=jewelry`
- `shop=gold_buyer`

Query the Scotland bounding box, or better, filter by the Scotland administrative relation.

Notes:

- Cache the raw JSON response to `data/raw/`. Overpass is a shared free service and repeated
  identical queries are poor practice.
- The Scotland administrative relation includes the islands, so the response contains
  competitors on Orkney, Shetland and the Western Isles. Step 2 drops any competitor more
  than 8 km from the nearest mainland locality, which removes them. Without this, the
  straight-line nearest-competitor distance for Wick and Thurso is measured to a jeweller in
  Orkney. See the decisions log in `CLAUDE.md`.
- Coverage of small retail categories in OSM is uneven. `shop=jewelry` is reasonably well
  mapped in cities and thin in small towns. `shop=gold_buyer` is rarely used and may return
  almost nothing.
- Report the count found per tag. If the total is too small to produce a meaningful distance
  variable, stop and escalate rather than proceeding with a near-empty layer.
- Licence: Open Database Licence. Attribution required.

---

## 4. Routing, isochrones and distance matrix

**OpenRouteService**

Sign-up: https://openrouteservice.org/dev/#/signup

Endpoints used:

- Isochrones, for drive-time catchments
- Matrix, for the pairwise road distance and duration table
- Directions, for the road geometry of the final route

Notes:

- Requires a free API key. The key is managed manually by the project owner. Do not create or
  read `.env`.
- Free tier has daily and per-minute request quotas. Isochrone requests are the most limited.
  Add a delay between calls and cache every response.
- The matrix endpoint has a size limit on the free tier. For 14 to 20 points this is
  comfortably within range.
- Use the `driving-car` profile.
- Licence: ORS is built on OpenStreetMap data. Attribution required.

An alternative is running OSRM locally in Docker against a Scotland extract, which removes
all rate limits. It is more setup and is not recommended unless ORS quotas become a genuine
blocker. If they do, escalate rather than switching unilaterally.

---

## 5. Basemap and cartographic context

For the QGIS work only. Not needed by any script.

- **OS Open Data** — Open Roads for the road network, Boundary-Line for administrative
  boundaries, and OS Open Names for place labels. Free, no key, and appropriate for a
  UK-focused printed map.
  https://osdatahub.os.uk/downloads/open
- **Natural Earth** — coastline and neighbouring-country context if a wider inset is wanted.
  https://www.naturalearthdata.com/

A plain, muted basemap is preferable to satellite imagery for a poster of this type.

---

## 6. Coordinate reference systems

- Source data will arrive in a mix of British National Grid (EPSG:27700) and WGS84
  (EPSG:4326).
- OpenRouteService requires and returns WGS84 (EPSG:4326).
- Store and export everything in **EPSG:27700** for consistency and correct distance
  calculation. Convert to 4326 only at the point of calling the API, and convert results
  straight back.
- Set the QGIS project CRS to EPSG:27700 so the printed map has a sensible projection for
  Scotland.

---

## 7. Attribution block for the poster

Include something equivalent to the following on any published map:

> Contains National Records of Scotland data. Contains OS data. Crown copyright and database
> right. Licensed under the Open Government Licence.
> Map data from OpenStreetMap contributors, licensed under ODbL.
> Routing and isochrones by OpenRouteService.
