import pandas as pd
import numpy as np
from datetime import timedelta
import random
import os

SEED = 42
random.seed(SEED)
np.random.seed(SEED)

OUTPUT_DIR = "noc_data"
os.makedirs(OUTPUT_DIR, exist_ok=True)


#DimDate

def build_dim_date(start="2023-01-01", end="2024-12-31"):
    dates = pd.date_range(start, end, freq="D")
    return pd.DataFrame({
        "date_id": range(1, len(dates) + 1),
        "full_date": dates.date,
        "year": dates.year,
        "quarter": "Q" + dates.quarter.astype(str),
        "month_num": dates.month,
        "month_name": dates.strftime("%B"),
        "week_num": dates.isocalendar().week.astype(int),
        "day_name": dates.strftime("%A"),
        "is_weekend": dates.dayofweek >= 5,
    })


# DimSeverity 

dim_severity = pd.DataFrame([
    (1, "P1 - Critical", 60),
    (2, "P2 - High", 240),
    (3, "P3 - Medium", 480),
    (4, "P4 - Low", 1440),
], columns=["severity_id", "severity_name", "sla_target_minutes"])


# DimCategory 

dim_category = pd.DataFrame([
    (1, "Network Congestion", "Network"),
    (2, "Hardware Failure", "Infrastructure"),
    (3, "Software / Firmware", "Software"),
    (4, "Power / Environmental", "Facility"),
    (5, "Security Incident", "Security"),
    (6, "Circuit / Link Down", "Network"),
    (7, "Configuration Error", "Software"),
    (8, "Performance Degradation", "Network"),
], columns=["category_id", "category_name", "category_group"])


# DimRegion  

dim_region = pd.DataFrame([
    (1, "North India", "India", "APAC"),
    (2, "South India", "India", "APAC"),
    (3, "West India", "India", "APAC"),
    (4, "East India",  "India", "APAC"),
    (5, "US East", "USA", "Americas"),
    (6, "US West", "USA", "Americas"),
    (7, "Europe West", "EU", "EMEA"),
    (8, "Middle East", "ME", "EMEA"),
], columns=["region_id", "region_name", "country", "zone"])


# DimTeam

dim_team = pd.DataFrame([
    (1, "Alpha NOC", "Tier 1", "Gurugram"),
    (2, "Beta NOC", "Tier 1", "Bangalore"),
    (3, "Gamma NOC", "Tier 2", "Hyderabad"),
    (4, "Delta NOC", "Tier 2", "Noida"),
    (5, "Escalation", "Tier 3", "Gurugram"),
], columns=["team_id", "team_name", "tier", "location"])


# DimDevice

def build_dim_device(n=100):
    types   = ["Router", "Switch", "Firewall", "Server", "Load Balancer", "WAN Optimizer"]
    vendors = ["Cisco", "Juniper", "Palo Alto", "HPE", "F5", "Nokia"]
    rows = []
    for i in range(1, n + 1):
        dtype= random.choice(types)
        vendor= random.choice(vendors)
        rows.append({
            "device_id": i,
            "device_code": f"DEV-{i:04d}",
            "device_name":f"{vendor} {dtype} #{i:03d}",
            "device_type": dtype,
            "vendor": vendor,
            "region_id": random.randint(1, 8),
        })
    return pd.DataFrame(rows)


# FactIncidents

def build_fact_incidents(dim_date_df,dim_device_df, n=5000):
    sla_map = dict(zip(dim_severity["severity_id"], dim_severity["sla_target_minutes"]))
    dev_region = dict(zip(dim_device_df["device_id"], dim_device_df["region_id"]))
    weekday_ids = dim_date_df[~dim_date_df["is_weekend"]]["date_id"].tolist()
    weekend_ids = dim_date_df[ dim_date_df["is_weekend"]]["date_id"].tolist()
    date_to_ts = dict(zip(dim_date_df["date_id"], pd.to_datetime(dim_date_df["full_date"])))

    # Realistic weightings
    sev_weights= [0.08, 0.20, 0.45, 0.27]
    cat_weights = [0.18, 0.15, 0.12, 0.07,
                   0.10, 0.17, 0.11, 0.10]

    mttr_range  = {1: (30, 180), 2: (60, 480), 3: (120, 960), 4: (240, 2880)}
    breach_prob = {1: 0.30,      2: 0.22,      3: 0.15,       4: 0.08}

    rows = []
    for idx in range(1, n + 1):
        sev_id = int(np.random.choice([1, 2, 3, 4], p=sev_weights))
        sla_target = sla_map[sev_id]
        breached = random.random() < breach_prob[sev_id]
        lo, hi = mttr_range[sev_id]

        if breached:
            duration= random.randint(sla_target + 10, sla_target * 3)
        else:
            upper = max(lo + 1, min(sla_target - 5, hi))
            duration = random.randint(lo, upper)

        # 80% weekday incidents, mirrors real NOC traffic
        date_id = random.choice(weekday_ids if random.random() < 0.80 else weekend_ids)
        base_ts = date_to_ts[date_id]
        open_dt = base_ts +timedelta(hours=random.randint(0, 23),
                                       minutes=random.randint(0, 59))
        close_dt = open_dt +timedelta(minutes=duration)

        status = "Closed" if random.random() < 0.95 else "Open"
        device_id = random.randint(1, 100)
        cat_id = int(np.random.choice(range(1, 9), p=cat_weights))

        # Breached P1s always escalate to Tier 3
        team_id = 5 if (sev_id == 1 and breached) else random.randint(1, 4)

        rows.append({
            "incident_id": f"INC-{idx:05d}",
            "date_id": date_id,
            "device_id": device_id,
            "category_id": cat_id,
            "severity_id": sev_id,
            "region_id": dev_region[device_id],
            "team_id": team_id,
            "open_datetime": open_dt.strftime("%Y-%m-%d %H:%M"),
            "close_datetime": close_dt.strftime("%Y-%m-%d %H:%M") if status == "Closed" else "",
            "duration_minutes": duration if status == "Closed" else None,
            "sla_target_minutes": sla_target,
            "is_sla_breached": int(breached),
            "status": status,
        })

    return pd.DataFrame(rows)


# Export all tables

dim_date_df = build_dim_date()
dim_device_df = build_dim_device()
fact_df = build_fact_incidents(dim_date_df, dim_device_df)

tables = {
    "dim_date": dim_date_df,
    "dim_severity": dim_severity,
    "dim_category": dim_category,
    "dim_region": dim_region,
    "dim_team": dim_team,
    "dim_device": dim_device_df,
    "fact_incidents": fact_df,
}

for name, df in tables.items():
    path = f"{OUTPUT_DIR}/{name}.csv"
    df.to_csv(path, index=False)
    print(f"✓  {name:<22} {len(df):>5,} rows  →  {path}")

# Sanity check
print("\n── Sanity Check ────────────────────────────────")
print(f"Total incidents: {len(fact_df):,}")
print(f"SLA breach rate: {fact_df['is_sla_breached'].mean()*100:.1f}%")
print(f" Avg MTTR (hrs): {fact_df['duration_minutes'].mean()/60:.1f}")
print(f" Open incidents: {(fact_df['status']=='Open').sum()}")