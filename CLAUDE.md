# CLAUDE.md

Working rules and project plan for the Scotland Mobile Service Route Analysis project.

Read `BACKGROUND.md` for domain context and `DATA_SOURCES.md` for data provenance before
starting Step 1.

---

## 1. What this project is

A small, self-contained geospatial analysis that answers one question:

> If a mobile service operated a two-week touring route across mainland Scotland, which
> towns should it visit, and in what order?

The project produces a scored shortlist of towns, a drive-time coverage assessment, a
sequenced two-week route, a formatted Excel workbook, and map layers ready for manual
cartography in QGIS.

It is a demonstration of technical and analytical ability. It is not a consultancy
deliverable and does not model any specific company's operations.

---

## 2. Guiding principles

These matter more than any individual technical choice. When in doubt, follow these.

**Keep it simple and explainable.** Every method used must be something the project owner
can describe out loud in two or three sentences without notes. If a technique cannot be
explained simply, it is the wrong technique for this project, even if it is more accurate.

**Prefer transparent methods over sophisticated ones.** A weighted score of three variables
beats a regression. A nearest-neighbour heuristic with a 2-opt pass beats a commercial
solver. The reader should be able to follow the logic without trusting a black box.

**Do not over-engineer.** No config frameworks, no plugin architectures, no abstract base
classes. Plain scripts that run top to bottom.

**Do not embellish the domain.** The project makes no claims about how any real business
plans its routes. Scoring inputs are stated as reasonable proxies, not established facts.

**Stand-alone framing.** The project documentation and outputs must read as an independent
piece of analysis. Do not reference job applications, employers, cover letters, or
recruitment anywhere in code, comments, output files or written material.

---

## 3. Hard rules

**Never push to GitHub.** At the end of every completed step, output the git commands as a
copy-pasteable block for the project owner to run manually:

```
git add .
git commit -m "<appropriate message>"
git push
```

Do not execute them. Just print them.

**Never read, open or display the contents of `.env` files.** This is an assistant
restriction for security: Claude Code must not view the secrets inside. The scripts
themselves may load `.env` (via `python-dotenv`) to read a key into the environment. API
keys are provided by the project owner. When a new key is needed, stop, give written
instructions on where to obtain it and the variable name to set, then wait. Do not create
the `.env` file on the owner's behalf.

**Escalate significant decisions.** If anything needs to change materially from this plan
(scope, data source, method, output format, or anything that would invalidate work already
done), stop. Present the options clearly with pros and cons for each, give a recommendation,
and wait for a decision. Do not decide unilaterally.

**Never delete or overwrite raw downloaded data.** Raw files in `data/raw/` are treated as
read-only once fetched. All processing writes to `data/processed/`.

**Code style.** Clean, light, readable. Comments used sparingly, for sections that genuinely
need explanation. A file path comment at the top of each file. No emojis anywhere in code,
comments, commit messages or output.

**One step at a time.** Complete a step, report what was done, print the git block, then
stop and wait. Do not run ahead into the next step.

---

## 4. Locked scope decisions

These were decided before work began. Do not revisit without escalating.

| Decision | Value |
|---|---|
| Study area | Mainland Scotland only. Islands excluded to avoid ferry routing. |
| Candidate towns | NRS localities with population of roughly 5,000 or above |
| Scoring inputs | Three only: population, share aged 55+, distance to nearest existing competitor |
| Route type | Closed loop. No fixed depot. Natural entry point is an output, not an input. |
| Tour length | 14 days |
| Routing method | Nearest-neighbour construction plus 2-opt improvement |
| Excel approach | Hybrid. Python writes formatted data sheets; pivots added manually. |
| Spreadsheet software | LibreOffice Calc. Avoid native Excel Table objects; use formatted ranges with autofilter and named ranges. |
| Mapping | QGIS, manual. Python exports layers only, performs no cartography. |

---

## 5. Project structure

```
scotroute/
  CLAUDE.md              This file
  BACKGROUND.md          Domain context
  DATA_SOURCES.md        Data provenance and licensing
  README.md              Short project description (written in Step 0)
  requirements.txt
  data/
    raw/                 Downloaded source data, treated as read-only
    processed/           Cleaned intermediate outputs
  scripts/
    01_prepare_towns.py
    02_score_towns.py
    03_isochrones.py
    04_build_route.py
    05_export_excel.py
    06_export_gis.py
  outputs/
    scotland_route_analysis.xlsx
    gis/                 GeoPackage layers for QGIS
  qgis/                  QGIS project file and print layout (manual work)
```

---

## 6. Step-by-step plan

Each step ends with a report and a git block. Then stop.

### Step 0 — Setup

- Create the directory structure above.
- Write `requirements.txt`. Expected: `geopandas`, `pandas`, `requests`, `openpyxl`,
  `shapely`. Add others only if genuinely needed.
- Write a short `README.md` describing the project in a few sentences, its scope, and how to
  run the scripts. Neutral tone, stand-alone framing.
- Create a `.gitignore` that excludes `.env`, `data/raw/`, `__pycache__/`, and any large
  intermediate files.

Do not install anything or fetch any data yet.

### Step 1 — Prepare the candidate towns (`01_prepare_towns.py`)

- Download NRS locality boundaries and locality population estimates. See `DATA_SOURCES.md`.
- Filter to mainland Scotland. Exclude the Western Isles, Orkney and Shetland council areas.
  If a simple attribute filter is not available, a spatial filter against the mainland
  landmass is acceptable, but flag the approach used.
- Filter to localities with population of roughly 5,000 or above.
- Attach the share of population aged 55 and over. The NRS locality tables are the preferred
  source. If age bands are not available at locality level, stop and escalate with options
  before falling back to a data zone join.
- Compute a representative point for each locality for routing purposes. Use the centroid,
  or a point-on-surface if the centroid falls outside the polygon.
- Output: `data/processed/towns.gpkg` with one row per locality, plus a brief printed summary
  of how many towns passed each filter.

Expected result is somewhere in the region of 80 to 120 towns. If the count is wildly outside
that, stop and report before continuing.

### Step 2 — Score the towns (`02_score_towns.py`)

- Fetch existing competitor locations from OpenStreetMap via the Overpass API. Relevant tags
  are `shop=pawnbroker`, `shop=jewelry` and `shop=gold_buyer`. Cache the raw response to
  `data/raw/` so Overpass is not queried repeatedly.
- OSM coverage for these tags in Scotland may be patchy. Report the count found. If coverage
  looks too thin to be meaningful, stop and escalate rather than quietly proceeding.
- Drop competitors more than 8 km from the nearest mainland locality (added 2026-09-08, see
  decisions log). This removes island points (Orkney, Shetland, Western Isles) that would
  otherwise measure Wick's and Thurso's nearest competitor across open water.
- For each town, compute straight-line distance to the nearest competitor. Straight-line is
  fine here and should be stated as such.
- Normalise each of the three inputs to a 0 to 1 range using min-max scaling. Population is
  log10-transformed before min-max; age share and competitor distance are min-max on their
  raw values. This deviation from plain min-max was escalated and agreed on 2026-09-08
  because population is strongly right-skewed and a plain min-max left it with almost no
  influence on the ranking. See the decisions log.
- Combine into a single score with explicit, visible weights. Start with equal weights of
  one third each. Keep the weights in one clearly named constant at the top of the file so
  they are easy to find and change.
- Output: `data/processed/towns_scored.gpkg` and a printed top 20 table.

Do not add a fourth scoring variable. Do not switch to a more complex normalisation or
weighting scheme without escalating. (The log10 step for population is the one agreed
exception, recorded in the decisions log.)

### Step 3 — Drive-time coverage (`03_isochrones.py`)

- Requires an OpenRouteService API key. Stop and request setup instructions be followed
  before running. Do not create or read the `.env` file.
- Take the top 15 to 20 scored towns.
- Request 30, 45 and 60 minute driving isochrones for each.
- Respect the free tier rate limits. Add a short delay between requests and cache every
  response to `data/raw/isochrones/` so the API is called only once per town.
- Estimate the population falling inside the 45 minute band. A simple approach is fine:
  intersect the isochrones with all locality points and sum their populations. State the
  method and its limitation, which is that it counts only urban locality population and
  ignores dispersed rural population.
  "All locality points" here means the `all_localities` layer written by Step 1: every
  mainland locality with no population threshold (646 points), not just the 174 shortlisted
  towns. Step 1 was extended to write this layer.
- Report the catchment two ways (added 2026-09-08, see decisions log): gross (everyone
  within 45 minutes) and net of localities that already have a competitor within 2 km. The
  net figure avoids crediting a small stop with a nearby city's population when that city is
  already served. Gross is an upper bound, net a lower bound.
- Output: `data/processed/isochrones.gpkg` and the printed coverage figures.

### Step 4 — Build the route (`04_build_route.py`)

- Take the top N scored towns, where N is set by a clearly named constant. Start with 14,
  one per day.
- Build a road distance and duration matrix between them using the OpenRouteService matrix
  endpoint. Cache the result.
- Construct an initial tour with a nearest-neighbour heuristic.
- Improve it with a 2-opt pass until no further improvement is found.
- The result is a closed loop. Report total distance, total driving time, and the per-leg
  breakdown.
- Identify and report a sensible entry point into the loop, defined as the town in the loop
  with the largest population, and rotate the sequence to start there for presentation
  purposes.
- Assign one town per day across 14 days.
- Fetch the actual road geometry for the full sequence so the route can be drawn on a map
  rather than shown as straight lines.
- Output: `data/processed/route.gpkg` containing both the ordered stop points and the route
  line geometry, plus a printed day-by-day schedule.

Keep the heuristic implementation short and readable. It should be obvious from the code
what nearest-neighbour and 2-opt are doing.

### Step 5 — Excel workbook (`05_export_excel.py`)

Produce `outputs/scotland_route_analysis.xlsx` with three sheets.

**Sheet 1: Town Scores.** All shortlisted towns with population, share aged 55+, distance to
nearest competitor, the three normalised components, and the final score. Sorted by score
descending.

**Sheet 2: Route Schedule.** Day number, town, population, distance from previous stop,
driving time from previous stop, and cumulative distance.

**Sheet 3: Summary.** Left largely empty by design, with a short note at the top stating that
pivot tables and charts are added manually from the named ranges on the other sheets.

Formatting requirements:

- Bold header row with a single accent fill colour, frozen panes below it.
- Autofilter across the header row on the data sheets.
- Sensible column widths, set explicitly rather than guessed.
- Correct number formats. Thousands separators on population, one decimal place on
  distances, percentages formatted as percentages.
- A colour scale conditional format on the score column only.
- A named range covering each data sheet's table area, so pivots can be built against it.
- Print setup: A4 landscape, fit to one page wide, repeat the header row on each page.

Do not use openpyxl's Table or ListObject feature. LibreOffice handles those inconsistently.
Formatted ranges with autofilter and named ranges achieve the same result portably.

Aim for the look of a competent internal working document. Clear and readable, one accent
colour, no decorative styling.

### Step 6 — Export GIS layers (`06_export_gis.py`)

Export a single GeoPackage at `outputs/gis/scotroute.gpkg` with these layers:

- `towns_scored` — all shortlisted towns with score attributes
- `isochrones` — the drive-time bands
- `route_line` — the road geometry of the sequenced tour
- `route_stops` — the ordered stops with day numbers
- `competitors` — the OSM competitor points

Ensure all layers share a single CRS. British National Grid, EPSG 27700, is appropriate for
a Scotland-only project and will make QGIS work straightforward.

This script performs no styling. Cartography is manual.

### Step 7 — QGIS poster (manual, no Claude Code involvement)

Handled entirely by the project owner in QGIS. Claude Code's involvement ends at Step 6.

For reference, the intended output is a single A3 poster combining a scored-towns map, a
drive-time coverage map and the sequenced route map, with a legend, north arrow, scale bar
and data attribution.

If asked for help at this stage, provide written guidance on QGIS styling and layout only.
Do not attempt to generate map images programmatically.

---

## 7. API keys required

One only.

**OpenRouteService** — used in Steps 3 and 4 for isochrones and the distance matrix. Free
tier is sufficient for this project's request volume. When Step 3 is reached, provide setup
instructions and wait. Do not create the `.env` file.

---

## 8. Progress log

Update this section at the end of every step. Keep entries to one or two lines.

| Step | Status | Notes |
|---|---|---|
| 0 — Setup | Done | Directory structure, requirements.txt, README.md, .gitignore, script stubs created. Nothing installed or fetched. |
| 1 — Prepare towns | Done | NRS mid-2020 localities. Mainland attribute filter, pop >= 5,000. 174 towns. Age 55+ share from Table 3.2 (locality level, no data-zone fallback needed). towns.gpkg layers: towns (174 points), towns_poly (174 polygons), all_localities (646 mainland points, no threshold, added for Step 3 coverage). EPSG:27700. |
| 2 — Score towns | Done | 411 OSM competitors used (427 fetched, 16 dropped as >8 km offshore - see decisions log). Straight-line nearest-competitor distance. Equal 1/3 weights. Population log10 then min-max (escalated change); age and distance min-max on raw values. Thurso and Wick now score 1st/2nd (nearest competitor on the mainland: 92 and 86 km). towns_scored.gpkg has layers towns_scored and competitors, EPSG:27700. |
| 3 — Isochrones | Done | Top 20 scored towns, 30/45/60 min driving-car bands via ORS, cached. Key from .env via python-dotenv. Combined 45-min catchment: gross 4.29M (86.8% of the 4.95M mainland locality pop), net of localities with a competitor within 2 km 1.61M (32.5%). isochrones.gpkg layer isochrones (60 polygons), EPSG:27700. |
| 4 — Build route | Done | Option A route, confirmed after review. Top 14 scored towns. ORS matrix (cached). Multi-start nearest-neighbour then 2-opt on road distance: 1,272 -> 1,236 km. Closed loop 1,236 km / 16.9 h, ORS directions confirms. Entry point Glasgow. route.gpkg layers route_stops (14) and route_line (1), EPSG:27700. Days 3/5/7 are long single drives into Caithness/Moray - kept with a caveat per the review. |
| 5 — Excel workbook | Done | outputs/scotland_route_analysis.xlsx. Sheets: Town Scores (174), Route Schedule (14 + loop-total line), Catchment (477 localities, served/underserved), Summary (note only). Accent 1F4E79 header, frozen + autofiltered, explicit widths, number formats, colour scale on Score column only (Town Scores only), named ranges TownScores, RouteSchedule and CatchmentLocalities, A4 landscape fit-to-width, repeating header. No Table objects. Council area added as a context column. Pivot tables for the Summary sheet are being built manually outside this repo; see the handoff note in the project owner's scratchpad. |
| 6 — Export GIS | Done | outputs/gis/scotroute.gpkg, all EPSG:27700: towns_scored (174 pts), competitors (411 pts), isochrones (60 polys), route_line (1), route_stops (14), catchment_localities (477 pts). No styling. Offshore competitors already removed in Step 2; a few Bute/Mull/Skye points remain (do not affect scoring - see decisions log). |
| 7 — QGIS poster | Done (manual) | Four-panel poster built by hand in QGIS, outside this scripted pipeline as planned. Not tracked here in detail. |

### Decisions made during the project

Record any escalated decision here, with the option chosen and a one-line reason.

- **Step 1, town count.** The locked population >= 5,000 threshold yields 174 mainland
  localities, above the plan's expected 80 to 120. Chose to keep the 5,000 threshold as a
  locked scope decision and proceed with 174; downstream steps only use the top N, and the
  threshold is a single named constant if it needs revisiting.

- **Step 2, population normalisation (2026-09-08).** Chose Option B: log10-transform
  population before min-max, leaving age share and competitor distance as plain min-max on
  raw values. Weights stay equal at one third each.
  Reason: population across the 174 towns is extremely right-skewed (skewness 7.98; Glasgow
  632k against a median of 10k). Under plain min-max, 75 percent of towns had a normalised
  population below 0.02 and only the four cities exceeded 0.2, so the population term did
  almost no work in the ranking (component-to-score correlation 0.15, versus 0.75 for age
  and 0.64 for distance; removing population changed only 2 of the top 30 towns). This
  defeats the stated purpose of population as the main demand proxy. log10 first compares
  towns by order of magnitude, which is the intended meaning of "larger town, more demand";
  after the change the population term has the same spread as the other two (std ~0.17) and
  a score correlation of 0.34. Alternatives considered and rejected: keep as-is and disclose
  (leaves the main demand measure inert); percentile/rank normalisation of all three (throws
  away magnitude everywhere, larger departure from the plan); winsorise population at the
  95th percentile (arbitrary cap point, over-corrects). Change is contained to
  `02_score_towns.py`; only Step 2 was re-run.

- **Post Step 4, route review (2026-09-08).** After seeing the results, reviewed whether to
  adjust the scoring weights before producing outputs. The optimised route is 1,247 km /
  17.3 h, of which 61 percent of the driving is the Highland excursion (Thurso, Wick, Nairn,
  Forres - 34,350 residents between them). Two changes were trialled and re-run end to end:
  weights 0.40/0.40/0.20 still keep Wick and Thurso in the top 14 and leave the route length
  unchanged (1,251 km) while making the northern spur a pure there-and-back; weights
  0.50/0.35/0.15 remove the Highlands entirely (709 km) but revert the shortlist toward a
  conventional "biggest towns" list, losing the project's analytical angle. There is no
  middle weighting that drops Caithness while keeping the small-underserved-town character,
  because competitor distance both surfaces genuine white space and over-rewards remoteness.
  Decision: keep Option A (equal weights, the original method) unchanged. The write-up will
  state plainly that Thurso and Wick are genuine but small white space (net catchment = gross
  = 16,020 each, i.e. fully unserved) and that whether the return justifies roughly 700 km
  and two near-dead vehicle-days is a business judgement needing the operator's own margin
  and response data. Weights reverted to 1/3 each; Steps 2, 3, 4 re-run to restore A.

- **Step 2, offshore competitors (2026-09-08).** The Overpass query returns competitors
  across the whole Scotland administrative area, including the islands. Straight-line
  distance then measured Wick's and Thurso's nearest competitor to a jeweller in Orkney
  (86 and 92 km once corrected, but 58 and 43 km to Orkney), a ferry away. Added a filter in
  `02_score_towns.py`: competitors more than `MAINLAND_MAX_KM` (8 km) from the nearest
  mainland locality are dropped. The cutoff sits in a wide empty gap in the data (every kept
  point is within 5 km of a locality, the nearest dropped one about 10 km out). 16 points
  removed: Shetland (5), Orkney (5), Western Isles (1), Iona (1), Skye (3), one deep-rural.
  Only Wick and Thurso were affected (their nearest competitor is now on the mainland);
  their scores moved -0.021 and +0.087 and they swapped 1st/2nd place. Route re-run:
  1,247 -> 1,236 km, Auchterarder and Lanark replaced by Prestwick and East Kilbride at the
  14-town cut. Steps 2 to 6 re-run.
  Residual not fixed: five competitors on Bute, Mull and Skye survive the filter because
  those islands have NRS localities in kept councils. Only Largs is affected (nearest
  competitor on Bute, 12.6 km, versus 18.1 km to the mainland) with no rank or route change.
  Chose Option A: leave it. Removing them would need a hardcoded island-locality list or a
  coastline dataset, disproportionate to a 5 km shift on one town, and island residents
  plausibly do travel to mainland stops so island population is not simply out of scope.

- **Catchment sheet and pipeline reorganisation (2026-09-13).** Added a fourth Excel sheet,
  "Catchment" (477 localities, served/underserved, Council area, distance to nearest
  competitor), positioned between Route Schedule and Summary, with named range
  `CatchmentLocalities`. This is pivot-ready source data for a pivot table the project owner
  is building manually. Doing so required fixing a pipeline ordering problem: the
  served/underserved classification only existed as a written output inside
  `06_export_gis.py`, computed after `05_export_excel.py` already runs, so Step 5 had no way
  to read it. Checked the code rather than assuming; confirmed Step 3 computes the same
  gross/net split but only as summary totals, never persists the per-locality table. Moved
  the classification into `03_isochrones.py`, written once to `data/processed/catchment.gpkg`
  (layer `catchment_localities`); `05_export_excel.py` and `06_export_gis.py` both read it
  from there now instead of recomputing it. Verified unchanged after the move: 477
  localities, 69 served (2,685,470), 408 underserved (1,608,100), summing to the gross
  4,293,570 already reported by Step 3, and the GIS layer identical in row count, columns
  and geometry to before the refactor. Steps 3, 5 and 6 re-run; Steps 1, 2 and 4 untouched.

- **Step 3, gross vs net catchment (2026-09-08).** Added a second coverage figure: catchment
  population excluding localities that already have a competitor within 2 km
  (`LOCAL_COMPETITOR_M`). Reason: the gross figure counts a large town such as Perth toward
  the catchment of a nearby small stop even though its residents already have the service
  locally, overstating the addressable market. Gross is reported as an upper bound, net as a
  lower bound. Reporting only - does not feed the score or the route. Contained to
  `03_isochrones.py`.
