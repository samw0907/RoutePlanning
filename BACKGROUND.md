# Background

Domain context for the Scotland Mobile Service Route Analysis project. This exists so the
analysis is grounded in how mobile touring services actually operate, rather than being an
abstract exercise in graph theory.

---

## 1. The mobile touring service model

A growing category of consumer businesses operates without fixed premises. Instead, a small
fleet of branded vehicles tours a country on a published schedule, stopping in towns for a
short period before moving on. Examples include mobile precious-metal buyers, mobile health
screening, mobile opticians and hearing tests, and mobile veterinary services.

The shared characteristics that matter for planning are:

**Short, scheduled stops.** The vehicle parks at a published time in an accessible, familiar
public location, typically a supermarket or retail car park. Customers come to the vehicle.

**Appointment-led with limited capacity.** Slots are booked in advance and are finite,
because service is usually one customer at a time inside the vehicle. This caps the revenue
available from any single stop-day regardless of how large the town is.

**Blanket-then-move coverage.** Operators typically concentrate a run of stops into a defined
window in one area, then relocate. A single vehicle may make dozens of stops across one urban
region over a fortnight before moving to the next region. This is a meaningfully different
pattern from a fixed weekly milk round.

**Demand is drawn from a catchment, not a footprint.** Because customers travel to the
vehicle, the relevant population is everyone within a tolerable drive, not just the residents
of the town itself. This is why drive-time analysis matters more than town population alone.

**Supply is finite and depletes.** In categories where customers sell or dispose of something
they own, a given area cannot be revisited too frequently, because the stock of available
items takes time to replenish. This constrains revisit cadence.

The last two points are the reason a naive "visit the biggest towns" approach is inadequate,
and they are the analytical hook for this project.

---

## 2. What route planning involves in this context

Route planning for a touring service is not the same as vehicle routing for deliveries. There
are no fixed customers with fixed addresses. The planner is choosing *where demand is likely
to be* as well as *how to get there efficiently*. In practice it decomposes into four
questions.

**Site selection.** Which settlements are worth visiting at all? This is a market-screening
question answered with demographic and competitive data, not with a routing algorithm.

**Catchment and coverage.** How much of the population does a given set of stops actually
reach, and where are the gaps? Answered with drive-time isochrones. Overlapping catchments
indicate two stops competing for the same customers.

**Sequencing.** Given a set of stops, what order minimises travel? This is the classic
travelling salesman problem. For a realistic number of stops it does not need an exact
solver.

**Scheduling and allocation.** How many days does each area justify, how are stops spread
across the working week, and how many vehicles are needed? This depends heavily on internal
operational data and is largely out of scope for an open-data project.

This project covers the first three and deliberately leaves the fourth alone.

---

## 3. Technical concepts used

Short definitions, at the level of detail the project actually requires.

**Locality.** A defined urban area used in Scottish official statistics. National Records of
Scotland publishes boundaries and population estimates for settlements and localities,
covering urban areas whose population rounds to at least 500 people. Settlements are built
from contiguous high-density postcodes; larger settlements are subdivided into localities.
As of the mid-2020 publication there were 656 localities and 514 settlements. Localities are
a good candidate unit for this project because they correspond to recognisable towns rather
than administrative boundaries.

**Isochrone.** A polygon enclosing everywhere reachable from a point within a given travel
time. A 45-minute driving isochrone around a town shows the realistic catchment from which
customers might travel. Isochrones are computed against a real road network, so they are
irregular and follow major roads outward, unlike a simple circular buffer.

**Distance matrix.** A table of road distances and travel times between every pair of points
in a set. Required as the input to any sequencing algorithm. Straight-line distance is a poor
substitute in Scotland, where sea lochs and mountains mean two towns close together as the
crow flies can be an hour apart by road.

**Travelling salesman problem (TSP).** Given a set of stops and the distances between them,
find the shortest route visiting each once and returning to the start. Exactly solvable for
small sets but expensive as the count grows, so heuristics are normal practice.

**Nearest-neighbour heuristic.** Build a tour by repeatedly travelling to the closest
unvisited stop. Fast and intuitive but typically produces a tour some way above optimal,
because it makes locally greedy choices and gets stranded at the end.

**2-opt improvement.** Take an existing tour, and repeatedly test whether reversing a section
of it produces a shorter route. Continue until no improvement is found. It is easy to
implement, easy to explain, and typically brings a nearest-neighbour tour close to optimal.
The combination of nearest-neighbour construction plus 2-opt improvement is a standard
textbook approach and is entirely adequate here.

**Closed loop and entry point.** A closed tour has no inherent starting position. Entering
the loop at any stop gives the same total distance. The choice of entry point is therefore
an operational convenience, not an optimisation result, and this project reports it as such.

**Min-max normalisation.** Rescaling a variable so its lowest value becomes 0 and its highest
becomes 1. Used here so that three variables measured in different units can be combined into
a single weighted score. It is simple and transparent, though it is sensitive to outliers.

---

## 4. Why the three chosen scoring variables

The scoring model deliberately uses only three inputs. Each is a reasonable proxy rather than
a measured driver, and the project should describe them that way.

**Population.** The most direct available measure of potential demand. Larger towns supply
more potential customers and more potential appointments.

**Share aged 55 and over.** Older households are more likely to have accumulated durable
goods, inherited items and unused possessions. For services whose demand derives from what
people already own rather than what they currently need, age structure is a more informative
signal than raw population.

**Distance to nearest existing competitor.** Towns without a nearby established provider
represent an underserved catchment. This variable is genuinely ambiguous and the project
should say so: the absence of competitors may indicate an opportunity, or it may indicate
that no viable market exists there. It is included because it adds a competitive dimension
cheaply, not because the direction of the effect is certain.

Deliberately excluded, to keep the model explainable: deprivation indices, household income,
tenure, car ownership, retail footfall, and any composite index. Each could be defended, but
every additional variable makes the score harder to reason about and the marginal insight is
small.

---

## 5. Known limitations

Worth stating openly in any write-up.

- Population is counted at locality level only. Dispersed rural population outside defined
  localities is not captured, so coverage figures understate true reach.
- Competitor data comes from OpenStreetMap, which is volunteer-maintained and has uneven
  coverage of small retail categories.
- Scoring weights are set by judgement, not calibrated against any outcome data.
- The route treats one stop per day, which is a simplification. Real touring operations make
  multiple short stops per day within an area.
- Islands are excluded. Ferry scheduling introduces constraints that a project at this scale
  cannot handle meaningfully.
- Drive-time isochrones assume free-flowing traffic and do not account for time of day.

---

## 6. Sector context for Scotland

Useful framing when interpreting results.

Scotland's population is heavily concentrated in the Central Belt, with Glasgow and Edinburgh
and their surrounding towns accounting for a large majority of the urban population. Beyond
that there are secondary clusters around Aberdeen, Dundee and Inverness, and then a long tail
of small towns along the coasts and in the Borders.

This geography has a direct consequence for touring services: a short, tight loop through the
Central Belt reaches a very large share of the population at low travel cost, while extending
north or into the Borders adds substantial driving for comparatively little additional reach.
Quantifying that trade-off is one of the more interesting things this project can show.

Established competitors in the second-hand and precious-metals retail space in Scotland
include national pawnbroking chains with high-street branches concentrated in larger towns.
Their absence from smaller towns is part of what the competitor distance variable is
attempting to capture.
