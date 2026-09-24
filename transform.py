import duckdb
import logging

logging.basicConfig(
    level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s',
    filename='transform.log'
)
logger = logging.getLogger(__name__)

DB_PATH = "emissions.duckdb"
TRIP_TABLES = ["yellow_trips", "green_trips"]

NEW_COLUMNS = {
    "vehicle_type": "VARCHAR",
    "trip_co2_kgs": "DOUBLE",
    "avg_mph": "DOUBLE",
    "hour_of_day": "INTEGER",
    "day_of_week": "INTEGER",
    "week_of_year": "INTEGER",
    "month_of_year": "INTEGER",
}


def add_columns(con, table):
    """Add all six new columns to `table` if they don't already exist."""
    for column, dtype in NEW_COLUMNS.items():
        con.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {dtype}")
    logger.info(f"{table}: ensured columns {list(NEW_COLUMNS)} exist")


def transform_table(con, table):
    """Populate the six calculated columns for `table` (yellow_trips or
    green_trips): CO2 output (via a real-time lookup against
    vehicle_emissions), average speed, and four date-part extractions
    from pickup_time."""

    add_columns(con, table)

    # Populate vehicle_type from the table name itself, so it can be
    # joined against vehicle_emissions (e.g. 'yellow_taxi', 'green_taxi').
    taxi_color = table.replace("_trips", "")          # "yellow_trips" -> "yellow"
    vehicle_type = f"{taxi_color}_taxi"
    con.execute(f"UPDATE {table} SET vehicle_type = '{vehicle_type}'")
    logger.info(f"{table}: vehicle_type set to '{vehicle_type}'")

    # trip_co2_kgs: real-time lookup against vehicle_emissions, joined on
    # vehicle_type (e.g. 'yellow_taxi'). NOT a hard-coded number.
    con.execute(f"""
        UPDATE {table}
        SET trip_co2_kgs = (
            SELECT ({table}.trip_distance * ve.co2_grams_per_mile) / 1000.0
            FROM vehicle_emissions ve
            WHERE ve.vehicle_type = {table}.vehicle_type
        )
    """)
    logger.info(f"{table}: trip_co2_kgs calculated via vehicle_emissions lookup")

    # avg_mph: distance divided by duration in hours.
    con.execute(f"""
        UPDATE {table}
        SET avg_mph = trip_distance / (date_diff('second', pickup_time, dropoff_time) / 3600.0)
    """)
    logger.info(f"{table}: avg_mph calculated")

    # Date-part extractions from pickup_time.
    con.execute(f"""
        UPDATE {table}
        SET
            hour_of_day   = date_part('hour', pickup_time),
            day_of_week   = date_part('dow', pickup_time),
            week_of_year  = date_part('week', pickup_time),
            month_of_year = date_part('month', pickup_time)
    """)
    logger.info(f"{table}: hour_of_day, day_of_week, week_of_year, month_of_year calculated")

    n = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    print(f"{table}: transformed {n} rows")
    logger.info(f"{table}: transformed {n} rows")


def transform_trip_data():
    """Connect to the DuckDB database and apply all transformations to
    both yellow_trips and green_trips."""

    con = None

    try:
        con = duckdb.connect(database=DB_PATH, read_only=False)
        logger.info("Connected to DuckDB instance")

        for table in TRIP_TABLES:
            transform_table(con, table)

    except Exception as e:
        print(f"An error occurred: {e}")
        logger.error(f"An error occurred: {e}")


if __name__ == "__main__":
    transform_trip_data()