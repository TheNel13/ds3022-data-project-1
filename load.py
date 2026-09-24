import duckdb
import os
import logging

logging.basicConfig(
    level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s',
    filename='load.log'
)
logger = logging.getLogger(__name__)

DB_PATH = "emissions.duckdb"
EMISSIONS_CSV = os.path.join("data", "vehicle_emissions.csv")

TLC_BASE_URL = "https://d37ci6vzurychx.cloudfront.net/trip-data"

YEAR = 2024
MONTHS = range(1, 13)

# YELLOW and GREEN parquet files use different column names for the
# pickup/dropoff timestamps (tpep_* vs lpep_*).
TAXI_CONFIG = {
    "yellow": {
        "table": "yellow_trips",
        "pickup_col": "tpep_pickup_datetime",
        "dropoff_col": "tpep_dropoff_datetime",
    },
    "green": {
        "table": "green_trips",
        "pickup_col": "lpep_pickup_datetime",
        "dropoff_col": "lpep_dropoff_datetime",
    },
}

def load_parquet_files():

    con = None

    try:
        # Connect to local DuckDB instance
        con = duckdb.connect(database='emissions.duckdb', read_only=False)
        logger.info("Connected to DuckDB instance")

        # Checkpoint 1: load the vehicle_emissions lookup table (8 rows).
        con.execute("DROP TABLE IF EXISTS vehicle_emissions")
        con.execute(f"""
            CREATE TABLE vehicle_emissions AS
            SELECT * FROM read_csv_auto('{EMISSIONS_CSV}')
        """)
        n = con.execute("SELECT COUNT(*) FROM vehicle_emissions").fetchone()[0]
        print(f"vehicle_emissions: {n} rows loaded")
        logger.info(f"vehicle_emissions: {n} rows loaded")

        # Checkpoint 2: load YELLOW taxi trips for all of 2024.
        con.execute("DROP TABLE IF EXISTS yellow_trips")
        config = TAXI_CONFIG["yellow"]

        for month in MONTHS:
            url = f"{TLC_BASE_URL}/yellow_tripdata_{YEAR}-{month:02d}.parquet"
            select_sql = f"""
                SELECT
                    {config['pickup_col']}  AS pickup_time,
                    {config['dropoff_col']} AS dropoff_time,
                    passenger_count,
                    trip_distance
                FROM read_parquet('{url}')
            """

            table_exists = con.execute(
                "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'yellow_trips'"
            ).fetchone()[0]

            if not table_exists:
                con.execute(f"CREATE TABLE yellow_trips AS {select_sql}")
            else:
                con.execute(f"INSERT INTO yellow_trips {select_sql}")

            logger.info(f"yellow_trips: loaded month {month:02d}/{YEAR}")

        n = con.execute("SELECT COUNT(*) FROM yellow_trips").fetchone()[0]
        print(f"yellow_trips: {n} rows loaded (raw)")
        logger.info(f"yellow_trips: {n} rows loaded (raw)")

    except Exception as e:
        print(f"An error occurred: {e}")
        logger.error(f"An error occurred: {e}")

if __name__ == "__main__":
    load_parquet_files()