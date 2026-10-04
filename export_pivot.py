"""
export_pivot.py
---------------
Standalone script to export a full pivot table from Parquet data.
Run: python export_pivot.py

Output: sales_pivot.xlsx
Columns: Volume | OC | Dropsize  ×  Jan 2024 → latest month
Rows:    Region > Branch > RGM > Brand > Sub Brand > SKU
"""

import duckdb
import pandas as pd
import os
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

# ── Config ────────────────────────────────────────────────────────────────────
DATA_PATH  = "demo_data/sales_demo.parquet"   # change to your path
OUTPUT     = "sales_pivot.xlsx"

# ── Month ordering ─────────────────────────────────────────────────────────
MONTH_ORDER = ["Jan","Feb","Mar","Apr","May","Jun",
               "Jul","Aug","Sep","Oct","Nov","Dec"]
MONTH_NUM   = {m:i+1 for i,m in enumerate(MONTH_ORDER)}

month_case = "CASE " + " ".join(
    f"WHEN \"MONTH TRX\"='{m}' THEN {i+1}" for i,m in enumerate(MONTH_ORDER)
) + " ELSE 99 END"

# ── Query ─────────────────────────────────────────────────────────────────────
print("Reading data...")
df = duckdb.sql(f"""
    SELECT
        "REGION"                               AS region,
        CASE
            WHEN POSITION('#' IN "BRANCH") > 0
            THEN SPLIT_PART("BRANCH", '#', 2)
            ELSE "BRANCH"
        END                                    AS branch,
        "RGM"                                  AS rgm,
        "BRAND"                                AS brand,
        "SUB BRAND"                            AS sub_brand,
        "SUBBRAND LIST"                        AS sku,
        CAST("YEAR TRX" AS VARCHAR)            AS yr,
        "MONTH TRX"                            AS mo,
        {month_case}                           AS mo_num,
        SUM(CAST("ACTUAL" AS DOUBLE))          AS vol,
        COUNT(DISTINCT "ACCOUNT")              AS oc
    FROM read_parquet('{DATA_PATH}', union_by_name=True)
    GROUP BY region, branch, rgm, brand, sub_brand, sku, yr, mo, mo_num
    ORDER BY yr, mo_num
""").df()

print(f"  Rows: {len(df):,}")

# ── Build period ordering ─────────────────────────────────────────────────────
df["period"] = df["mo"] + " " + df["yr"]
df["sort"]   = df["yr"].astype(str) + df["mo_num"].astype(str).str.zfill(2)
PERIODS      = list(dict.fromkeys(df.sort_values("sort")["period"].tolist()))

# ── Pivot rows ────────────────────────────────────────────────────────────────
ROW_COLS  = ["region","branch","rgm","brand","sub_brand","sku"]
ROW_NAMES = ["Region","Branch","RGM","Brand","Sub Brand","SKU"]

print("Building pivot tables...")
pv_vol = df.pivot_table(index=ROW_COLS, columns="period", values="vol",
                         aggfunc="sum").reindex(columns=PERIODS).fillna(0)
pv_oc  = df.pivot_table(index=ROW_COLS, columns="period", values="oc",
                         aggfunc="sum").reindex(columns=PERIODS).fillna(0)
pv_ds  = pv_vol / pv_oc.replace(0, float("nan"))

pv_vol.index.names = ROW_NAMES
pv_oc.index.names  = ROW_NAMES
pv_ds.index.names  = ROW_NAMES

# ── Add metric level to columns ───────────────────────────────────────────────
def add_level(pv, metric):
    pv = pv.copy()
    pv.columns = pd.MultiIndex.from_tuples(
        [(metric, p) for p in pv.columns],
        names=["Metric", "Period"]
    )
    return pv

df_final = pd.concat([
    add_level(pv_vol, "Volume"),
    add_level(pv_oc,  "OC"),
    add_level(pv_ds,  "Dropsize"),
], axis=1).fillna(0)

print(f"  Pivot shape: {df_final.shape[0]:,} rows × {df_final.shape[1]} columns")

# ── Write to Excel ────────────────────────────────────────────────────────────
print(f"Writing to {OUTPUT}...")

with pd.ExcelWriter(OUTPUT, engine="openpyxl") as writer:
    df_final.to_excel(writer, sheet_name="Pivot")
    ws = writer.sheets["Pivot"]

    N_IDX = len(ROW_NAMES)  # 6 index columns

    # ── Color scheme per metric ───────────────────────────────────────────────
    METRIC_STYLE = {
        "Volume":   {"fill": "DBEAFE", "text": "1E40AF"},   # blue
        "OC":       {"fill": "DCFCE7", "text": "166534"},   # green
        "Dropsize": {"fill": "FEF9C3", "text": "854D0E"},   # amber
    }

    def make_fill(hex_color):
        return PatternFill("solid", fgColor=hex_color)

    # ── Style header rows (1=Metric, 2=Period, 3=index names, data from row 4)
    for col_idx in range(N_IDX + 1, ws.max_column + 1):
        metric_cell = ws.cell(row=1, column=col_idx)
        metric      = metric_cell.value or ""
        style       = METRIC_STYLE.get(metric, {})

        for row in range(1, 3):
            c = ws.cell(row=row, column=col_idx)
            if style:
                c.fill      = make_fill(style["fill"])
                c.font      = Font(bold=True, color=style["text"], size=9)
            c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    # ── Style column index header row ─────────────────────────────────────────
    for col_idx in range(1, N_IDX + 1):
        c = ws.cell(row=2, column=col_idx)
        c.font      = Font(bold=True, size=9, color="1E293B")
        c.fill      = make_fill("F1F5F9")
        c.alignment = Alignment(horizontal="left", vertical="center")

    # ── Style data cells ──────────────────────────────────────────────────────
    for row in ws.iter_rows(min_row=3, max_row=ws.max_row):
        for cell in row:
            cell.font      = Font(size=9)
            cell.alignment = Alignment(
                horizontal="right" if cell.column > N_IDX else "left",
                vertical="center"
            )
            if cell.column > N_IDX and cell.value is not None:
                cell.number_format = "#,##0.00"

    # ── Column widths ─────────────────────────────────────────────────────────
    idx_widths = [14, 14, 10, 12, 16, 22]   # per index column
    for i, w in enumerate(idx_widths[:N_IDX], start=1):
        ws.column_dimensions[get_column_letter(i)].width = w
    for i in range(N_IDX + 1, ws.max_column + 1):
        ws.column_dimensions[get_column_letter(i)].width = 9

    # ── Row heights ───────────────────────────────────────────────────────────
    ws.row_dimensions[1].height = 18
    ws.row_dimensions[2].height = 15

    # ── Freeze panes after index cols + header rows ────────────────────────
    ws.freeze_panes = ws.cell(row=3, column=N_IDX + 1)

print(f"\nDone! Saved to: {OUTPUT}")
print(f"  Sheet  : Pivot")
print(f"  Rows   : {df_final.shape[0]:,}")
print(f"  Columns: {df_final.shape[1]} ({len(PERIODS)} periods × 3 metrics)")
