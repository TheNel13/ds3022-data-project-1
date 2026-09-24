import duckdb
import logging
import matplotlib
matplotlib.use("Agg")  # no GUI backend needed, just save to file
import matplotlib.pyplot as plt

logging.basicConfig(
    level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s',
    filename='analysis.log'
)
logger = logging.getLogger(__name__)

DB_PATH = "emissions.duckdb"
TRIP_TABLES = {"yellow_trips": "YELLOW", "green_trips": "GREEN"}


def report(label, value):
    """Print and log one labeled analysis result."""
    line = f"{label}: {value}"
    print(line)
    logger.info(line)


def largest_trip(con, table, cab_label):
    """Find and report the single largest CO2-producing trip in `table`."""
    row = con.execute(f"""
        SELECT trip_distance, trip_co2_kgs, pickup_time
        FROM {table}
        ORDER BY trip_co2_kgs DESC
        LIMIT 1
    """).fetchone()
    distance, co2, pickup = row
    report(
        f"{cab_label} - largest single carbon-producing trip",
        f"{co2:.2f} kg CO2 ({distance} miles, picked up {pickup})",
    )


def heaviest_lightest(con, table, cab_label, column, column_label, formatter=str):
    """Report the heaviest and lightest average-CO2 value of `column`
    (e.g. hour_of_day, day_of_week, week_of_year, month_of_year)."""
    rows = con.execute(f"""
        SELECT {column}, AVG(trip_co2_kgs) AS avg_co2
        FROM {table}
        GROUP BY {column}
        ORDER BY avg_co2 DESC
    """).fetchall()

    heaviest = rows[0]
    lightest = rows[-1]

    report(
        f"{cab_label} - heaviest {column_label}",
        f"{formatter(heaviest[0])} (avg {heaviest[1]:.4f} kg CO2/trip)",
    )
    report(
        f"{cab_label} - lightest {column_label}",
        f"{formatter(lightest[0])} (avg {lightest[1]:.4f} kg CO2/trip)",
    )


def plot_monthly_co2(con):
    """Render both a line chart and a bar chart of total CO2 by month,
    one series per cab type, saved as monthly_co2_line.png and
    monthly_co2_bar.png."""
    months = list(range(1, 13))
    totals_per_table = {}

    for table, cab_label in TRIP_TABLES.items():
        rows = con.execute(f"""
            SELECT month_of_year, SUM(trip_co2_kgs) AS total_co2
            FROM {table}
            GROUP BY month_of_year
            ORDER BY month_of_year
        """).fetchall()
        totals_by_month = dict(rows)
        totals_per_table[cab_label] = [totals_by_month.get(m, 0) for m in months]

    # Line chart
    fig, ax = plt.subplots(figsize=(10, 6))
    for cab_label, totals in totals_per_table.items():
        ax.plot(months, totals, marker="o", label=cab_label)
    ax.set_xlabel("Month")
    ax.set_ylabel("Total CO2 (kg)")
    ax.set_title("Monthly CO2 Output by Taxi Type (2024) - Line")
    ax.set_xticks(months)
    ax.legend()
    fig.tight_layout()
    fig.savefig("monthly_co2_line.png")
    logger.info("Saved monthly_co2_line.png")
    print("Saved plot: monthly_co2_line.png")

    # Bar chart
    fig, ax = plt.subplots(figsize=(10, 6))
    width = 0.35
    for i, (cab_label, totals) in enumerate(totals_per_table.items()):
        offset = (i - 0.5) * width
        ax.bar([m + offset for m in months], totals, width=width, label=cab_label)
    ax.set_xlabel("Month")
    ax.set_ylabel("Total CO2 (kg)")
    ax.set_title("Monthly CO2 Output by Taxi Type (2024) - Bar")
    ax.set_xticks(months)
    ax.legend()
    fig.tight_layout()
    fig.savefig("monthly_co2_bar.png")
    logger.info("Saved monthly_co2_bar.png")
    print("Saved plot: monthly_co2_bar.png")


DAY_NAMES = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
MONTH_NAMES = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def analyze_trip_data():
    """Connect to the DuckDB database and answer all six analysis
    questions for both yellow_trips and green_trips."""

    con = None

    try:
        con = duckdb.connect(database=DB_PATH, read_only=True)
        logger.info("Connected to DuckDB instance")

        for table, cab_label in TRIP_TABLES.items():
            largest_trip(con, table, cab_label)
            heaviest_lightest(con, table, cab_label, "hour_of_day", "hour of day")
            heaviest_lightest(con, table, cab_label, "day_of_week", "day of week", lambda d: DAY_NAMES[d])
            heaviest_lightest(con, table, cab_label, "week_of_year", "week of year")
            heaviest_lightest(con, table, cab_label, "month_of_year", "month of year", lambda m: MONTH_NAMES[m])

        plot_monthly_co2(con)

    except Exception as e:
        print(f"An error occurred: {e}")
        logger.error(f"An error occurred: {e}")


if __name__ == "__main__":
    analyze_trip_data()