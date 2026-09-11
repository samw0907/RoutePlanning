# QGIS poster guide

Step 7 of the project: a single A3 poster combining a scored-towns map, a
drive-time coverage map and the sequenced route map, with a legend, north arrow,
scale bar and data attribution. Project CRS EPSG:27700. Muted basemap, one accent
colour, no decorative styling.

Layers come from `outputs/gis/scotroute.gpkg`:

| Layer | Geometry | Used on |
|---|---|---|
| towns_scored | 174 points | scored-towns panel; faint context elsewhere |
| competitors | 411 points | scored-towns panel context |
| isochrones | 60 polygons (band_min 30/45/60) | coverage panel |
| route_line | 1 line | route panel |
| route_stops | 14 points (day, name, leg_km, leg_min, cum_km) | route panel |

Accent colour used across the project: `#1F4E79`. A warm contrast for the route
line: `#E15A1D`.

---

## 1. Fix the basemap

CartoDB Positron and most hosted "light" tile services now require an API key.
For a print poster, raster tiles also pixelate when exported at 300 dpi. Use a
vector land polygon instead - crisp at any size, full colour control, no key.

### Recommended: Natural Earth land (vector, no key)

1. Layers panel: right-click **OpenStreetMap** (or the broken Positron) >
   **Remove Layer**.
2. Download `ne_10m_land`:
   `https://naciscdn.com/naturalearth/10m/physical/ne_10m_land.zip`
   (or via `https://www.naturalearthdata.com/downloads/10m-physical-vectors/`).
3. Unzip into `data/raw/`.
4. **Layer > Add Layer > Add Vector Layer** > browse to `ne_10m_land.shp` > Add.
5. Drag it to the very bottom of the Layers panel.
6. Properties > Symbology > Single Symbol:
   - Fill color `#EDEEF0`
   - Stroke color `#C6CBD1`, Stroke width `0.15` mm
7. Optional crisper coast: also add `ne_10m_coastline.shp`, style as a thin
   `#AAB2BD` line.

It draws the whole world but you only see Scotland in the map frames; no need to
clip. Attribution: the standard OGL / OS / OSM / ORS block only, no basemap line.

### Faster alternative: Esri Light Gray Canvas (raster tiles, no key)

Browser panel > right-click **XYZ Tiles** > **New Connection**:
- Name: `Esri Light Gray`
- URL: `https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}`
  (note `{z}/{y}/{x}` order for Esri)
- Min zoom 0, Max zoom 16 > OK, then double-click to add. Drag to the bottom.

Attribution line to add in section 11:
`Basemap: Esri Light Gray Canvas (Esri, HERE, Garmin, (c) OpenStreetMap contributors)`

### Fully first-party UK data (most setup)

Download OS Open data from `https://osdatahub.os.uk/downloads/open` - Boundary-Line
(Scotland / council outline as a pale fill) and OS Open Roads (thin grey lines).
No API key. Satellite imagery is not wanted.

---

## 2. Palette (clean editorial look)

| Use | Colour |
|---|---|
| Page / sea | `#FBF9F4` |
| Land fill | `#ECE8DE` |
| Land / coast stroke | `#CDC7B8` |
| Accent (towns, stops, isochrones) | `#1F4E79` |
| Route | `#C1442E` |
| Label text | `#1F2933` |

---

## 3. Page and land

1. **Project > Properties > General > Background color** -> `#FBF9F4`. OK.
2. `ne_10m_land` > **Properties > Symbology** > Simple fill:
   - Fill `#ECE8DE`, Stroke color `#CDC7B8`, stroke width `0.2` mm. OK.
3. Add `ne_10m_coastline.shp` (**Layer > Add Layer > Add Vector Layer**), style
   as a line `#BEB8A8`, width `0.3` mm. Place just above `ne_10m_land`.
4. Uncheck any rivers layer.

Layer order, top to bottom: route_stops, route_line, towns_scored, isochrones,
demand heatmap (all_localities), competitors, ne_10m_coastline, ne_10m_land.

---

## 4. Scored towns (graduated by population, small)

`scotroute - towns_scored` > **Properties > Symbology** > Single Symbol.

1. Next to **Size**, click the small data-defined button (yellow/grey) >
   **Assistant**.
2. Source: `population`. Scaling method: **Flannery** (area). Output size
   `1.0` to `4.5` mm. OK.
3. Back in Symbology: Fill `#1F4E79`, **Opacity 65%**, Stroke color white,
   stroke width `0.15` mm.
4. Bottom of the dialog: **Control feature rendering order** (the small button) >
   add `population` > **Descending** (draws big first, small on top). OK.

---

## 5. Demand heatmap and competitors

### Demand (population) heatmap - coverage panel

1. **Layer > Add Layer > Add Vector Layer** > `data/processed/towns.gpkg` >
   sub-layer **all_localities** (646 points).
2. **Properties > Symbology** > **Heatmap**.
3. **Weight points by**: `population`.
4. **Radius**: `18` mm.
5. **Color ramp**: new gradient, transparent -> `#E8862E` -> `#9C3D0E`.
6. **Layer Rendering > Opacity** `55%`. Place just above `ne_10m_coastline`.

Read alongside the isochrones: amber outside the blue zones = unmet demand.

### Competitors - scores panel only, faint

`scotroute - competitors` > **Properties > Symbology** > Single Symbol:
Simple marker, circle `0.8` mm, fill `#8C8C8C`, **Opacity 35%**, No Pen stroke.

---

## 6. Isochrones (coverage panel, overlap density)

Use the original `scotroute - isochrones` (do not dissolve).

1. Right-click the layer > **Filter** > `"band_min" = 45` > OK.
2. **Properties > Symbology** > Single Symbol > Simple fill:
   - Fill `#1F4E79`, Stroke style **No Pen**.
3. **Layer Rendering** > Blending mode **Normal**; **Opacity 22%**. OK.

Overlapping 45-minute zones stack to about 40-55%, so the Central Belt reads as
the densest coverage. Multiply is not used - over the near-white land it makes the
fills almost invisible. Optional crisp edge: add a stroke `#1F4E79` `0.15` mm at
about 40% opacity.

---

## 7. Route line (bold)

`scotroute - route_line` > **Properties > Symbology** > Single Symbol (Line).

1. Select the **Simple Line** > Color `#C1442E`, Stroke width `1.3` mm.
2. Click the green **+** (bottom left) > a second Simple Line appears > drag it
   **below** the first with the down arrow > Color white, Stroke width `2.3` mm.
3. Arrows: click **+** again > select the new layer > **Symbol layer type** >
   **Marker line**. Marker placement **With interval** `22` mm. In the symbol
   tree click the leaf **Simple Marker** > set its shape to the solid
   right-pointing triangle (**Filled arrowhead**) in the shape grid, or change
   **Symbol layer type** to **Font marker** and use the character `>`
   (Segoe UI Symbol). Size `4` mm, Fill white. If the arrows point across the
   line, set **Rotation** to `90`.
4. Symbol tree order, top to bottom: **Marker Line**, **Simple Line** (red core
   1.3), **Simple Line** (white casing 2.3). Reorder with the up/down arrows.
5. Optional: **Layer Rendering > Draw effects** > the star > **Drop shadow**,
   blur `0.5` mm, opacity `25%`.

---

## 8. Route stops

`scotroute - route_stops` > **Properties > Symbology**.

1. Top dropdown: **Rule-based**.
2. Edit the default rule: Simple marker, circle `3` mm, fill `#1F4E79`,
   stroke white `0.4` mm.
3. Click **+** > new rule, Filter `"day" = 1` > Simple marker, circle `6` mm,
   fill `#1F4E79`, stroke white `0.6` mm. OK.

---

## 9. Labels

The Labels tab has sub-panels down the left edge: Text, Formatting, Buffer,
Mask, Background, Shadow, Callouts, Placement, Rendering.

### route_stops - number only (names go in the side list, section 11)

1. Double-click `scotroute - route_stops` > **Labels** tab.
2. Top dropdown: **Single Labels**. **Value**: `"day"`.
3. **Text** sub-panel: Style **Bold**, Size **8**, Color `#1F2933`.
4. **Buffer** sub-panel: tick **Draw text buffer**, Size **1.0** mm, white.
5. **Placement** sub-panel: Mode **Cartographic**, Distance **2.0** mm.
6. **Callouts** sub-panel (for the crowded Ayrshire cluster): tick **Draw
   callouts**, Simple lines, width `0.2` mm, colour `#8A8A8A`.
7. **Rendering** sub-panel: tick **Show all labels for this layer (including
   colliding labels)**; **Label Z-Index** `5`.
8. OK. (The three Ayrshire stops 10-13 will always overlap at national scale;
   the callout lines and the side list handle it.)

### towns_scored - label only the strongest ~20

1. Double-click `scotroute - towns_scored` > **Labels** tab > **Single Labels**.
2. **Value**: choose `name` from the dropdown.
3. **Text** sub-panel: same font, Style **Regular**, Size **7.5**, Color
   `#52606D`.
4. **Buffer** sub-panel: tick **Draw text buffer**, Size **0.8** mm, white.
5. **Placement** sub-panel: Mode **Around point**, Distance **1.5** mm, leave
   **Allow overlap** unticked.
6. **Rendering** sub-panel:
   - Next to **Show label**, click the data-defined button (boxed `e`) >
     **Edit** > enter `"score" >= 0.30` > OK. (Only ~top 20 get labelled.)
   - Set **Label Z-Index** to `0` (so stop labels win any collision).
7. OK.

### Notes

- Label size is fixed in points, so it only looks right at the final poster
  scale. Judge it in the print layout map frame, not the main canvas zoom.
- The Central Belt stays crowded on the national panels; that is what the
  Central Belt inset is for.

---

## 10. Save

- **Ctrl+S** to save the project as `qgis/scotroute.qgz` (set project CRS to
  EPSG:27700 first: Project > Properties > CRS).
- Optional, to reuse styling: each layer Properties > Style (bottom left) > Save
  Style > QML, into `qgis/`.

---

## 11. Print layout (the poster)

### Create it
1. **Project > New Print Layout** > name `ScotRoute A3`.
2. Right-click the page > **Page Properties** > Size **A3**, Orientation
   **Landscape**.

### Three map panels
The whole of mainland Scotland is the natural extent for all three panels, so
they share one scale.

1. Toolbar **Add Map** (or Add Item > Add Map). Drag a rectangle for the left
   third of the page.
2. With it selected, **Item Properties**:
   - **Scale**: type `1600000`, then adjust up or down so mainland Scotland
     fills the frame with a small margin. Note the final number.
3. **Add Map** again for the middle third, and again for the right third. Set
   each to the **same Scale** value.
4. Select all three (click, Shift-click) > **Align** toolbar > distribute
   horizontally and align tops so they line up.

### Per-panel layer sets (the key trick)
Each map item can freeze its own layer visibility.

1. Main window: tick only **panel 1 (scores)** layers -
   `towns_scored`, `competitors`, `ne_10m_coastline`, `ne_10m_land`.
2. Layout: click **panel 1** map item > Item Properties > **Layers** >
   tick **Lock layers**.
3. Main window: **panel 2 (coverage)** -
   `isochrones`, `all_localities` (demand heatmap), `route_stops`,
   `ne_10m_coastline`, `ne_10m_land`.
4. Layout: click **panel 2** > tick **Lock layers**.
5. Main window: **panel 3 (route)** -
   `route_line`, `route_stops`, `ne_10m_coastline`, `ne_10m_land`
   (hide towns_scored, heatmap, isochrones, competitors).
6. Layout: click **panel 3** > tick **Lock layers**.

### Route side list (panel 3)
Add Item > **Add Label** beside the route panel, monospace font, one stop per
line:

```
1  Glasgow            8  Edinburgh        99.8 km
2  Crieff       79.7  9  East Kilbride    71.1 km
3  Thurso      353.6  10 Girvan           85.7 km
4  Wick         34.7  11 Ayr              33.6 km
5  Nairn       189.4  12 Prestwick         5.9 km
6  Forres       18.2  13 Troon             9.9 km
7  Blairgowrie 161.2  14 Largs            42.6 km
                      close -> Glasgow    50.7 km
```

### Furniture
- **Title**: Add Item > Add Label, top centre. e.g.
  "A mobile service touring route across mainland Scotland".
- **Panel captions**: three more Labels, one above each map:
  "Town scores", "Drive-time coverage (30 / 45 / 60 minutes)",
  "Sequenced 14-day route".
- **Legend**: Add Item > Add Legend. In Item Properties set **Map** to the panel
  it describes; untick **Auto update**; delete rows you do not want. Add one
  legend per panel, or a single combined legend below the maps.
- **North arrow**: Add Item > Add North Arrow, place on panel 1.
- **Scale bar**: Add Item > Add Scale Bar. Item Properties: **Map** = panel 1,
  **Units** = Kilometers, style "Single Box", 4 segments.
- **Attribution**: Add Label, bottom of page, small text:

  > Contains National Records of Scotland data. Contains OS data. Crown copyright
  > and database right. Licensed under the Open Government Licence.
  > Map data from OpenStreetMap contributors, licensed under ODbL.
  > Routing and isochrones by OpenRouteService.

  Add a basemap line only if you used one:
  - Natural Earth land: `Land outline: Natural Earth.`
  - Esri Light Gray: `Basemap: Esri Light Gray Canvas (Esri, HERE, Garmin, (c) OpenStreetMap contributors).`
- **Headline numbers** (optional Label strip along the bottom):
  "174 candidate towns  -  top-20 45-minute reach 4.29M (87%), genuinely
  underserved 1.61M (33%)  -  route 1,236 km / 16.9 h over 14 days  -  entry point
  Glasgow".

### Export
- **Layout > Export as PDF** for print.
- **Layout > Export as Image** > PNG, **300 dpi**.

---

## 12. Optional improvements that show the analysis well

Ranked by how much they add:

1. **Gross vs net catchment on the coverage panel.** The most distinctive
   finding. Show, inside the 45-minute catchment, which localities already have a
   competitor (served) versus not (underserved), as two dot colours. Needs a
   small extra layer from the pipeline: localities inside the 45-min union,
   flagged served / underserved, with population. Ask and this can be added to
   Step 6.

2. **Colour the route by leg length.** `route_stops` graduated on `leg_km`: the
   two ~350 km legs to Caithness go dark, the Central Belt hops stay pale.
   Instantly shows that three legs are most of the driving. (Style the line via a
   join, or just colour the arrival stop markers.)

3. **Label each leg with distance and time.** On the route panel, label stops
   with `"day" || ': ' || "name" || '  ' || round("leg_km") || ' km'`. Makes the
   spur cost explicit.

4. **Central Belt inset.** Two thirds of the towns and half the route sit in a
   cluster that is tiny at national scale. Add a fourth small Map item at about
   1:500,000 centred on Glasgow-Edinburgh-Ayrshire, with a rectangle on the main
   panel marking its extent.

5. **Competitor gap as a faint heatmap.** `competitors` > Symbology > Heatmap
   renderer, low opacity, behind the scored towns. The empty north and south-west
   read as white space.

6. **Rank the top towns.** Number the top 10-15 on the scored panel so it ties
   back to the workbook order.

7. **Footnote on the offshore filter.** One line: "16 competitor points on
   Orkney, Shetland and the Western Isles were excluded as outside the mainland
   study area." Shows the choice was deliberate.
