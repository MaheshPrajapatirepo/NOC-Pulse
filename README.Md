# NOC Pulse — Network Operations & SLA Intelligence

A portfolio project created as an illustration of how NOC incident raw data can
be structured, processed, and visualized in order to become something
truly useful for the operations team. The idea was to go beyond a simple
dashboard and create something similar to what NOC reporting looks like
in real life — with proper data modeling, SLA management, and team
performance analytics.

---

## Why I built this

Being in the world of network operations, I realized that most of the dashboards
are showing the number of incidents and nothing else. The questions that are
usually being asked in a NOC environment — such as which level of severity
is failing SLAs the most, which region has problems, how does team's MTTR
compare with the target value — always required manual digging through
tickets. This project aims at providing answers to all these questions at once.

---

## Stack

- Python — synthetic data generation (star schema design)
- SQLite — data warehouse for exploratory analysis and validation
- SQL — 6 queries for exploratory data analysis to validate data before loading
to Power BI
- Power BI Desktop — data model, DAX measures, and interactive dashboard

---

## Project Structure

```bash
noc_powerbi/
    NOC-Pulse/
        generate_data.py # generates all 7 CSV files
        load_warehouse.py # loads CSVs into SQLite, runs EDA
    
        noc_data/
            fact_incidents.csv # 5,000 rows, 2 years (2023–2024)
            dim_date.csv
            dim_severity.csv
            dim_category.csv
            dim_region.csv
            dim_team.csv
            dim_device.csv
            noc_warehouse.db
    
        NOC_Pulse.pbix # Power BI dashboard file
        Dashboard PDF & Modeling Screenshots
```

---

## Data Model (Star Schema)
fact_incidents
    dim_date (date_id)
    dim_severity (severity_id) → holds SLA targets per priority
    dim_category (category_id)
    dim_region (region_id)
    dim_team (team_id)
    dim_device (device_id)

5,000 artificial events divided into 8 types, 8 regions, 5 NOC teams, 
and 100 network devices. Event occurrence rate is weighted to imitate
real NOC traffic – P3 events are the most numerous (about 45%), while P1 events are very infrequent (about 8%). Also, 80% of all events occur on weekdays.

---

## DAX Measures

All DAX measures reside in a separate table named "_Measures".

Total Incidents = COUNTROWS(fact_incidents)

SLA Breaches = SUM(fact_incidents[is_sla_breached])

SLA Breach Rate % =
DIVIDE(
SUM(fact_incidents[is_sla_breached]),
COUNTROWS(fact_incidents)
) * 100

SLA Compliance % = 100 - [SLA Breach Rate %]

Avg MTTR (hrs) =
DIVIDE(
AVERAGEX(
FILTER(fact_incidents, fact_incidents[status] = "Closed"),
fact_incidents[duration_minutes]
),
60
)

Open Incidents =
CALCULATE(
COUNTROWS(fact_incidents),
fact_incidents[status] = "Open"
)

P1 Incidents =
CALCULATE(
COUNTROWS(fact_incidents),
fact_incidents[severity_id] = 1
)

P1 Breach Rate % =
CALCULATE(
[SLA Breach Rate %],
fact_incidents[severity_id] = 1
)

SLA Target (hrs) =
DIVIDE(
MAX(dim_severity[sla_target_minutes]),
60
)

MTTR vs SLA Target =
AVERAGEX(
fact_incidents,
fact_incidents[duration_minutes] - fact_incidents[sla_target_minutes]
)

Worst Breach Region =
VAR BreachTable =
ADDCOLUMNS(
VALUES(dim_region[region_name]),
"BreachRate", CALCULATE([SLA Breach Rate %])
)
RETURN
MAXX(TOPN(1, BreachTable, [BreachRate], DESC), [region_name])

---

## Dashboard Pages

### Page 1 — Executive Overview
KPIs in brief form at the very top (number of incidents, SLA compliance, average MTTR,
open incidents, number of P1 incidents), monthly trend chart comparing 2023 and 2024,
incidents grouped by severity, and incidents grouped by category. Slicer of years to focus
on any of the two years.

### Page 2 — SLA Analysis
Gauge with comparison of compliance with 85% threshold, breach rate grouped by category
and by region, MTTR and SLA target shown next to each other by severity, and the trend of
breach rate per month. Severity slicer to get more details on any severity priority.

### Page 3 — Team and Device Performance
Team performance metrics with both MTTR and breach rate, top 10 devices in terms of
incidents with breaches, and treemap showing zone and regional distribution of incidents.
Tier slicer to filter out NOCs' levels.

---

## Major Observations from Data

- Overall SLA compliance stands at 83.6% with 85% being the industry standard
- Breach ratio of Performance Degradation is the highest at 19.8%
- South India and US East are the two worst regions for SLA violations (~19%)
- P1 Critical breach ratio is 31.4%, i.e., 1 out of every 3 critical incident does not meet SLA,
and that is the most actionable observation from this entire dataset
- Average MTTR of P1 is 1.15 hours compared to a 1-hour target; close yet consistent misses
- WAN Optimizers seem to be oversampling in the top 10 worst performing devices

---

## How to Run

```bash
# 1. install dependencies
pip install pandas numpy

# 2. generate data
python generate_data.py

# 3. load into SQLite and perform EDA
python load_warehouse.py

# 4. open NOC_Pulse.pbix in Power BI Desktop
# File > Get Data > Text/CSV > import all 7 files from noc_data/
```

---

## Notes

The Escalation team has 100% SLA breach rate and very low MTTR of
2.1 hrs. This is intentional, as they get tickets that have already been
breached at the Tier 1/2 levels, hence they will always have 100%
breach rate. They have low MTTR due to rapid response once escalated.

SQLite was used as the data warehouse layer before using EDA and schema
validation and Power BI connection. In a live environment, this should
have been replaced by SQL Server or PostgreSQL.

## Author

**Mahesh Prajapati**

- LinkedIn: [https://www.linkedin.com/in/mahesh-prajapati-profile/](...)
- GitHub: [https://github.com/MaheshPrajapatirepo/](...)
- Email: mahesh.prajapati242509@gmail.com/ m.mahesh@op.iitg.ac.in