import sqlite3
import pandas as pd
import os

DB_PATH = "noc_data/noc_warehouse.db"
DATA_DIR = "noc_data"

SCHEMA = {
    "dim_date": """
        date_id INTEGER PRIMARY KEY,
        full_date TEXT,
        year INTEGER,
        quarter TEXT,
        month_num INTEGER,
        month_name TEXT,
        week_num INTEGER,
        day_name TEXT,
        is_weekend  INTEGER
    """,
    "dim_severity": """
        severity_id INTEGER PRIMARY KEY,
        severity_name TEXT,
        sla_target_minutes INTEGER
    """,
    "dim_category": """
        category_id INTEGER PRIMARY KEY,
        category_name TEXT,
        category_group TEXT
    """,
    "dim_region": """
        region_id INTEGER PRIMARY KEY,
        region_name TEXT,
        country TEXT,
        zone TEXT
    """,
    "dim_team": """
        team_id INTEGER PRIMARY KEY,
        team_name TEXT,
        tier TEXT,
        location TEXT
    """,
    "dim_device": """
        device_id INTEGER PRIMARY KEY,
        device_code TEXT,
        device_name TEXT,
        device_type TEXT,
        vendor TEXT,
        region_id INTEGER
    """,
    "fact_incidents": """
        incident_id TEXT PRIMARY KEY,
        date_id INTEGER,
        device_id INTEGER,
        category_id INTEGER,
        severity_id INTEGER,
        region_id INTEGER,
        team_id INTEGER,
        open_datetime TEXT,
        close_datetime TEXT,
        duration_minutes REAL,
        sla_target_minutes INTEGER,
        is_sla_breached INTEGER,
        status TEXT
    """,
}

EDA_QUERIES = {
    "Total incidents by severity": """
        SELECT s.severity_name, COUNT(*) AS total,
               ROUND(AVG(f.duration_minutes), 1) AS avg_mttr_min,
               SUM(f.is_sla_breached) AS breaches
        FROM fact_incidents f
        JOIN dim_severity s ON f.severity_id = s.severity_id
        GROUP BY s.severity_name
        ORDER BY s.severity_id
    """,
    "SLA breach rate by category": """
        SELECT c.category_name,
               COUNT(*) AS total,
               SUM(f.is_sla_breached) AS breached,
               ROUND(100.0 * SUM(f.is_sla_breached) / COUNT(*), 1) AS breach_pct
        FROM fact_incidents f
        JOIN dim_category c ON f.category_id = c.category_id
        GROUP BY c.category_name
        ORDER BY breach_pct DESC
    """,
    "Incidents by region and zone": """
        SELECT r.zone, r.region_name, COUNT(*) AS total,
               ROUND(100.0 * SUM(f.is_sla_breached) / COUNT(*), 1) AS breach_pct
        FROM fact_incidents f
        JOIN dim_region r ON f.region_id = r.region_id
        GROUP BY r.zone, r.region_name
        ORDER BY r.zone, total DESC
    """,
    "Monthly trend 2023 vs 2024": """
        SELECT d.year, d.month_name, d.month_num, COUNT(*) AS incidents
        FROM fact_incidents f
        JOIN dim_date d ON f.date_id = d.date_id
        GROUP BY d.year, d.month_num
        ORDER BY d.year, d.month_num
    """,
    "Top 10 devices by incidents": """
        SELECT dv.device_code, dv.device_type, dv.vendor,
               COUNT(*) AS total_incidents,
               SUM(f.is_sla_breached) AS sla_breaches
        FROM fact_incidents f
        JOIN dim_device dv ON f.device_id = dv.device_id
        GROUP BY dv.device_id
        ORDER BY total_incidents DESC
        LIMIT 10
    """,
    "Team performance": """
        SELECT t.team_name, t.tier,
               COUNT(*) AS total,
               ROUND(AVG(f.duration_minutes) / 60.0, 1) AS avg_mttr_hrs,
               ROUND(100.0 * SUM(f.is_sla_breached) / COUNT(*), 1) AS breach_pct
        FROM fact_incidents f
        JOIN dim_team t ON f.team_id = t.team_id
        GROUP BY t.team_name
        ORDER BY t.tier, breach_pct
    """,
}


def load_data():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    for table, schema in SCHEMA.items():
        cur.execute(f"DROP TABLE IF EXISTS {table}")
        cur.execute(f"CREATE TABLE {table} ({schema})")

        df = pd.read_csv(os.path.join(DATA_DIR, f"{table}.csv"))
        df.to_sql(table, conn, if_exists="append",index=False)

        count = cur.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"✓  {table:<22} {count:>5,} rows loaded")

    conn.commit()
    return conn


def run_eda(conn):
    print("\n" + "=" * 55)
    print("EDA - Data Warehouse Validation")
    print("=" * 55)

    for label, sql in EDA_QUERIES.items():
        print(f"\n-- {label} --")
        df = pd.read_sql_query(sql, conn)
        print(df.to_string(index=False))


if __name__ == "__main__":
    conn = load_data()
    run_eda(conn)
    conn.close()
    print(f"\n✓  Database saved -> {DB_PATH}")