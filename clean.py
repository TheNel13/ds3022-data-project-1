import duckdb
import logging

logging.basicConfig(
    level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s',
    filename='clean.log'
)
logger = logging.getLogger(__name__)

DB_PATH = "emissions.duckdb"
TRIP_TABLES = ["yellow_trips", "green_trips"]


def clean_table(con, table):
    """Apply all five cleaning rules to one trip table (yellow_trips or
    green_trips), printing and logging a before/after verification count
    for each rule so we can prove the condition no longer exists."""

    # Rule 1: remove duplicate trips.
    before = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    con.execute(f"""
        CREATE TABLE {table}_deduped AS
        SELECT DISTINCT * FROM {table}
    """)
    con.execute(f"DROP TABLE {table}")
    con.execute(f"ALTER TABLE {table}_deduped RENAME TO {table}")
    after = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    print(f"{table} - duplicates removed: {before} -> {after}")
    logger.info(f"{table} - duplicates removed: {before} -> {after}")

    # Rule 2: remove trips with 0 passengers.
    before = con.execute(f"SELECT COUNT(*) FROM {table} WHERE passenger_count = 0").fetchone()[0]
    con.execute(f"DELETE FROM {table} WHERE passenger_count = 0")
    after = con.execute(f"SELECT COUNT(*) FROM {table} WHERE passenger_count = 0").fetchone()[0]
    print(f"{table} - 0-passenger trips: before={before}, after(verify)={after}")
    logger.info(f"{table} - 0-passenger trips: before={before}, after(verify)={after}")

    # Rule 3: remove trips with 0 miles.
    before = con.execute(f"SELECT COUNT(*) FROM {table} WHERE trip_distance = 0").fetchone()[0]
    con.execute(f"DELETE FROM {table} WHERE trip_distance = 0")
    after = con.execute(f"SELECT COUNT(*) FROM {table} WHERE trip_distance = 0").fetchone()[0]
    print(f"{table} - 0-mile trips: before={before}, after(verify)={after}")
    logger.info(f"{table} - 0-mile trips: before={before}, after(verify)={after}")

    # Rule 4: remove trips longer than 100 miles.
    before = con.execute(f"SELECT COUNT(*) FROM {table} WHERE trip_distance > 100").fetchone()[0]
    con.execute(f"DELETE FROM {table} WHERE trip_distance > 100")
    after = con.execute(f"SELECT COUNT(*) FROM {table} WHERE trip_distance > 100").fetchone()[0]
    print(f"{table} - >100-mile trips: before={before}, after(verify)={after}")
    logger.info(f"{table} - >100-mile trips: before={before}, after(verify)={after}")

    # Rule 5: remove trips lasting more than 86400 seconds (1 day).
    before = con.execute(f"""
        SELECT COUNT(*) FROM {table}
        WHERE date_diff('second', pickup_time, dropoff_time) > 86400
    """).fetchone()[0]
    con.execute(f"""
        DELETE FROM {table}
        WHERE date_diff('second', pickup_time, dropoff_time) > 86400
    """)
    after = con.execute(f"""
        SELECT COUNT(*) FROM {table}
        WHERE date_diff('second', pickup_time, dropoff_time) > 86400
    """).fetchone()[0]
    print(f"{table} - >86400s trips: before={before}, after(verify)={after}")
    logger.info(f"{table} - >86400s trips: before={before}, after(verify)={after}")


def clean_trip_data():
    """Connect to the DuckDB database and apply all cleaning rules to
    both yellow_trips and green_trips."""

    con = None

    try:
        con = duckdb.connect(database=DB_PATH, read_only=False)
        logger.info("Connected to DuckDB instance")

        for table in TRIP_TABLES:
            clean_table(con, table)

    except Exception as e:
        print(f"An error occurred: {e}")
        logger.error(f"An error occurred: {e}")


if __name__ == "__main__":
    clean_trip_data()