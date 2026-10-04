# Commercial Analytics Dashboard

> An internal sales analytics dashboard built with Python + Streamlit — designed to handle millions of rows of FMCG transactional data efficiently without any paid BI tool or cloud subscription.

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.35+-FF4B4B?logo=streamlit&logoColor=white)
![DuckDB](https://img.shields.io/badge/DuckDB-0.10+-FFF000?logoColor=black)
![Plotly](https://img.shields.io/badge/Plotly-5.20+-3F4F75?logo=plotly&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-22C55E)

---

## The problem

A sales team needed real-time visibility into millions of rows of transactional data — spanning multiple years, regions, branches, and SKUs — **without a paid BI subscription**.

The data lived in Parquet files on a local machine and needed to be accessible only to the internal team, not the public internet.

| Constraint               | Solution                                    |
| ------------------------ | ------------------------------------------- |
| No cloud BI budget       | Streamlit (open source)                     |
| Data too large for Excel | DuckDB — queries Parquet directly on disk   |
| Needs to stay internal   | Tailscale peer-to-peer VPN                  |
| Multiple team members    | One machine as host, others connect via VPN |

---

## Architecture

```
┌─────────────────────────────────────────┐
│             Host Machine                │
│                                         │
│  Parquet files  →  DuckDB               │
│  (millions of rows)   ↓                 │
│               Streamlit app             │
│                    ↓                    │
│              Tailscale VPN ─────────────┼──► Team browsers
└─────────────────────────────────────────┘
```

Data never leaves the host machine. Team members connect via Tailscale and access the dashboard through their browser — no port forwarding, no cloud.

---

## Features

### Analytics

| Feature                     | Description                                                                             |
| --------------------------- | --------------------------------------------------------------------------------------- |
| **KPI Summary**             | Volume, Outlet Coverage, Avg/Month, Dropsize — with YoY delta                           |
| **Volume & Coverage Trend** | Monthly/yearly line chart with breakdown by RGM, Region, Brand, or Category             |
| **YTD Comparison**          | Cross-year YTD bar chart (fair comparison, same month cutoff) with growth indicators ▲▼ |
| **Brand & Product Mix**     | Volume share pie + top sub brand ranking                                                |
| **Dropsize Analysis**       | Average volume per outlet by brand and by region                                        |
| **Outlet Coverage Heatmap** | Region × Brand unique account matrix                                                    |
| **Pivot Export**            | Excel file with multi-level headers: Metric × Period                                    |

### Engineering

| Feature                     | Description                                                                           |
| --------------------------- | ------------------------------------------------------------------------------------- |
| **DuckDB on Parquet**       | SQL queries run directly on `.parquet` files — no RAM overload                        |
| **Multi-layer filter**      | Period, Territory (RGM/Region/Branch), Product (Brand/Sub Brand/SKU)                  |
| **Accurate COUNT DISTINCT** | OC computed via `CASE WHEN` SQL so distinct counts don't double-count across branches |
| **Demo mode**               | Auto-detects synthetic data and shows a portfolio banner                              |
| **Excel export**            | Pivot table with Volume, OC, Dropsize — styled with color-coded metric headers        |

---

## Tech decisions

### Why DuckDB instead of Pandas?

```python
# Pandas loads everything into RAM — likely to crash or OOM on large files
df = pd.read_parquet("data/*.parquet")           # ❌ 15M rows → crash

# DuckDB runs SQL directly on Parquet — only loads the result into memory
result = duckdb.sql("""
    SELECT "REGION", SUM(CAST("ACTUAL" AS DOUBLE)) AS vol
    FROM read_parquet('data/*.parquet', union_by_name=True)
    WHERE "YEAR TRX" = '2026'
    GROUP BY "REGION"
""").df()                                         # ✅ fast, low RAM
```

### Why Tailscale instead of deploying to the cloud?

- Zero cost — no server, no hosting fee
- Data never leaves the machine — critical for internal sales data
- Setup time under 10 minutes — install + login, done
- Works across different networks (home, office, mobile hotspot)

### Accurate Outlet Coverage across dimensions

A naive `SUM(oc_per_branch)` double-counts accounts that purchased from multiple branches under the same brand or region. The fix runs `COUNT(DISTINCT)` at the correct aggregation level by building a `CASE WHEN` expression in SQL:

```sql
SELECT
    CASE
        WHEN "BRAND" = 'ZEPHYR' THEN 'ZEPHYR'
        WHEN "BRAND" = 'SOLARA' THEN 'SOLARA'
        -- ...
    END AS brand,
    COUNT(DISTINCT "ACCOUNT") AS oc   -- ✅ counted once per brand, not summed
FROM read_parquet('data/*.parquet', union_by_name=True)
GROUP BY brand
```

### Dropsize

Dropsize = `SUM(ACTUAL) / COUNT(DISTINCT ACCOUNT)` per dimension and period. It measures how deeply each active outlet is engaged — a high dropsize means each outlet is ordering more on average. It is re-computed at the correct aggregation level to avoid division errors.

---

## Quick start

```bash
# 1. Clone
git clone https://github.com/yourusername/fmcg-sales-dashboard.git
cd fmcg-sales-dashboard

# 2. Install dependencies
pip install -r requirements.txt

# 3. Generate synthetic demo data
python generate_demo.py
# → creates demo_data/sales_demo.parquet

# 4. Run the dashboard
streamlit run app_demo.py
# → opens at http://localhost:8501
```

The app auto-detects `demo_data/sales_demo.parquet` and runs in demo mode. To point it at real data, update `DATA_PATH` in `app_demo.py`.

---

## Project structure

```
fmcg-sales-dashboard/
├── app_demo.py           Main Streamlit app (demo + production)
├── generate_demo.py      Synthetic data generator
├── export_pivot.py       Standalone Excel pivot exporter
├── requirements.txt
├── .gitignore
├── README.md
└── demo_data/
    └── sales_demo.parquet    Generated by generate_demo.py
```

---

## Secure team sharing (production setup)

```bash
# On the host machine
# 1. Install Tailscale: tailscale.com/download
# 2. Log in with a shared team account or invite members via admin.tailscale.com
# 3. Get your Tailscale IP
tailscale ip -4
# → e.g. 100.64.1.5

# 4. Run the dashboard
streamlit run app_demo.py --server.port 8501

# Team members
# Install Tailscale → log in → open http://100.64.1.5:8501 in browser
```

---

## Export

Run `export_pivot.py` separately to generate a full pivot table as Excel:

```bash
python export_pivot.py
# → sales_pivot.xlsx
```

Excel structure:

- **Row 1** — Metric (Volume / OC / Dropsize), color-coded per metric
- **Row 2** — Period (Jan 2024, Feb 2024, …)
- **Columns 1–6** — Region, Branch, RGM, Brand, Sub Brand, SKU
- **Freeze pane** at column 7 row 3 — scroll right while keeping dimension labels visible

---

## Notes

- All data in this repository is **fully synthetic** — no real company data is included.
- The `ACTUAL` column is stored as `VARCHAR` in source files; all aggregations use explicit `CAST("ACTUAL" AS DOUBLE)`.
- RGM (Regional General Manager) territories are defined as a hardcoded lookup table mapping Region + Branch to RGM name.
- Brand hierarchy (Brand → Sub Brand → SKU) is derived from product naming conventions via string parsing, not stored in the raw data.

---

_Developed as a conceptual internal tool for an FMCG commercial team. This portfolio version utilizes synthetic data with anonymized brand and territory names._
