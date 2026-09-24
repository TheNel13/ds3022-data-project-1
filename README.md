# DS3022 - Data Project 1 (Fall 2025)

## What this pipeline does

This project builds a small ELT pipeline that estimates CO2 output for NYC
YELLOW and GREEN taxi trips across all of 2024, using DuckDB as the local
database engine. It runs in four stages:

1. **`load.py`** — Connects to a local DuckDB file (`emissions.duckdb`)
   and builds three tables:
   - `yellow_trips` — all YELLOW taxi trips for 2024, loaded month by
     month directly from NYC TLC's public Parquet files
     (`https://d37ci6vzurychx.cloudfront.net/trip-data/`).
   - `green_trips` — same, for GREEN taxis.
   - `vehicle_emissions` — a small lookup table loaded from
     `data/vehicle_emissions.csv`, mapping vehicle type to its
     `co2_grams_per_mile` rate.

   Files are loaded programmatically in a loop over months 1–12 for each
   taxi color, rather than one static `INSERT` per file. Only the columns
   actually needed downstream (`pickup_time`, `dropoff_time`,
   `passenger_count`, `trip_distance`) are pulled from each Parquet file,
   with YELLOW's `tpep_*` and GREEN's `lpep_*` timestamp columns aliased
   to the same common names so both tables share one schema.

2. **`clean.py`** — Applies five cleaning rules to both trip tables:
   removes duplicate rows, trips with 0 passengers, trips with 0 miles,
   trips over 100 miles, and trips lasting more than 86,400 seconds
   (1 day). Each rule prints and logs a before/after row count to prove
   the condition no longer exists after cleaning.

3. **`transform.py`** — Adds six calculated columns to both tables:
   - `trip_co2_kgs` — `(trip_distance * co2_grams_per_mile) / 1000`,
     looked up in real time against `vehicle_emissions` (not
     hard-coded), joined by a `vehicle_type` column set from the table
     name (`yellow_taxi` / `green_taxi`).
   - `avg_mph` — distance divided by trip duration in hours.
   - `hour_of_day`, `day_of_week`, `week_of_year`, `month_of_year` —
     extracted from `pickup_time` using DuckDB's `date_part()`.

4. **`analysis.py`** — Answers six questions per cab type (YELLOW and
   GREEN), all printed and logged with labels:
   - The single largest CO2-producing trip of the year.
   - The heaviest and lightest average-CO2 hour of day.
   - The heaviest and lightest average-CO2 day of week.
   - The heaviest and lightest average-CO2 week of year.
   - The heaviest and lightest average-CO2 month of year.
   - A monthly CO2 total plotted for both taxi types, saved as both
     `monthly_co2_line.png` (line chart) and `monthly_co2_bar.png`
     (bar chart).

## How to run it

```bash
python -m venv .venv
source .venv/bin/activate      # or .venv\Scripts\activate on Windows
pip install -r requirements.txt

python load.py
python clean.py
python transform.py
python analysis.py
```

Each stage logs to its own file (`load.log`, `clean.log`,
`transform.log`, `analysis.log`), and all key results also print to the
console. Running `load.py` downloads real Parquet files directly from
NYC's servers, so it takes a few minutes and needs a working internet
connection.

## Design decisions

**Reading Parquet straight off NYC's servers, instead of downloading first.**
DuckDB's `read_parquet()` can read a file directly from an HTTPS URL, so
`load.py` never saves a local copy of any Parquet file — it streams each
month straight into the database. This keeps the repo clean (no giant
data files to accidentally commit) and means anyone who clones this repo
can regenerate the whole database from scratch just by running the
scripts, without me having to distribute gigabytes of taxi data myself.

**Trimming the SELECT list early.** Each YELLOW/GREEN Parquet file has
around 20 columns — fares, tips, tolls, location IDs, and so on — but
`clean.py` and `transform.py` only ever touch four of them: pickup time,
dropoff time, passenger count, and trip distance. So `load.py` only pulls
those four (aliased to common names) instead of loading everything and
throwing most of it away later. It's faster to load and keeps the
database smaller for no real cost, since none of the discarded columns
are used anywhere in this project's required calculations.

**Aliasing `tpep_*`/`lpep_*` to one shared schema at load time.** YELLOW
and GREEN taxi files name their pickup/dropoff columns differently
(`tpep_pickup_datetime` vs `lpep_pickup_datetime`). Rather than carrying
that inconsistency through the whole pipeline and writing separate
cleaning/transform logic for each taxi color, I renamed both to
`pickup_time`/`dropoff_time` right in the `SELECT` during load. That way
`clean.py` and `transform.py` can loop over both tables with the exact
same code, instead of duplicating every rule twice.

**Cleaning rules as five separate DELETE + verify steps, not one
combined WHERE clause.** I originally considered writing one query that
filtered out all five bad conditions at once, but the rubric specifically
asks for a verification query proving each rule worked — a single
combined filter wouldn't let me isolate "did the 0-mile rule actually
do anything" from "did the >100-mile rule do anything." So each rule
gets its own before-count, `DELETE`, and after-count (which should
always land on 0), even though it means re-scanning the table five
times instead of once. For a table with tens of millions of rows that's
a real time cost, but I chose correctness/provability over speed here.

**CO2 as a real-time lookup, not a hard-coded rate.** It would have been
much simpler to just multiply every YELLOW trip's distance by 380 (the
rate in the CSV), but that breaks the moment the emissions data changes,
and it silently gives GREEN trips the wrong rate if I'm not careful. So
`transform.py` joins each trip back to `vehicle_emissions` by a
`vehicle_type` column (set from the table name at transform time) and
looks up the actual `co2_grams_per_mile` for that row's taxi color every
time. It's a small correlated subquery instead of a flat multiplication,
but it means the CO2 numbers stay correct even if the emissions CSV is
ever updated.

**Two plots instead of one.** The assignment only requires one chart
(a time-series plot or histogram), but I built both a line chart and a
bar chart of monthly CO2 by taxi type, since I wasn't sure which one my
instructor wanted and it cost almost nothing extra to generate both from
the same aggregated data.

**Not attempting the 2015–2024 bonus.** Expanding the date range would
mean roughly 10x the Parquet files and a database in the tens of
gigabytes, plus rewriting every hardcoded `2024` in the load script to
loop across years too. Given the time I had for this project, I decided
to focus on getting the core 2024 pipeline fully correct and well-tested
rather than spreading myself across a much larger dataset.

## DBT bonus
Not Attempted