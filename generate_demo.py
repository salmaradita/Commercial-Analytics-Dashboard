"""
generate_demo.py — Synthetic FMCG data generator (anonymized)
Run: python generate_demo.py
Output: demo_data/sales_demo.parquet
"""
import pandas as pd
import numpy as np
import random, os
from pathlib import Path

random.seed(42)
np.random.seed(42)

# ── Anonymized territory mapping ──────────────────────────────────────────────
# RGM → Region → Branch (all fictional)
TERRITORY = {
    "NOVA": {
        "WESTLAND": ["W01#GREENFIELD","W02#LAKEVIEW","W03#RIVERBEND","W04#CEDARTON","W05#MAPLEWOOD"],
        "EASTLAND": ["E01#BRIGHTPORT","E02#HILLCREST","E03#STONEGATE","E04#FAIRVIEW"],
    },
    "CREST": {
        "NORTHLAND": ["N01#PINEWOOD","N02#IRONDALE","N03#SUNRIDGE","N04#COLDWATER"],
        "CENTRAL":   ["C01#MIDVALE","C02#REDSTONE","C03#ELMHURST","C04#FOXBURY","C05#GRAYMONT"],
    },
    "APEX": {
        "SOUTHLAND": ["S01#BAYSIDE","S02#PALMCOVE","S03#DRIFTWOOD","S04#SANDALWOOD"],
        "HIGHLAND":  ["H01#SUMMIT","H02#RIDGEVIEW","H03#CLIFTON","H04#MONTROSE","H05#EASTVALE"],
    },
    "VERTEX": {
        "FAREAST":   ["F01#HORIZON","F02#SEAVIEW","F03#OAKDALE"],
        "ISLAND":    ["I01#CORAL","I02#TIDEMARK"],
    },
}

# Flatten for easy lookup
BRANCH_TO_RGM   = {}
BRANCH_TO_REGION = {}
for rgm, regions in TERRITORY.items():
    for region, branches in regions.items():
        for br in branches:
            BRANCH_TO_RGM[br]    = rgm
            BRANCH_TO_REGION[br] = region

# ── Anonymized product hierarchy ──────────────────────────────────────────────
# BRAND → SUB BRAND → [SUBBRAND LIST items]
PRODUCTS = {
    "ZEPHYR": {
        "ZEPHYR MINT":  ["ZEPHYR MINT CLASSIC BAG","ZEPHYR MINT COOL BAG","ZEPHYR MINT STRONG ROLL"],
        "ZEPHYR BERRY": ["ZEPHYR BERRY WILD BAG","ZEPHYR BERRY SOFT BAG"],
        "ZEPHYR CITRUS":["ZEPHYR CITRUS FRESH BAG","ZEPHYR CITRUS BURST ROLL"],
    },
    "SOLARA": {
        "SOLARA BLEND":  ["SOLARA BLEND RICH BOX","SOLARA BLEND MILD BOX","SOLARA BLEND DARK BOX"],
        "SOLARA LITE":   ["SOLARA LITE SMOOTH BOX","SOLARA LITE CRISP BOX"],
    },
    "VERDANT": {
        "VERDANT GREEN": ["VERDANT GREEN ORIGINAL BAG","VERDANT GREEN HONEY TPL","VERDANT GREEN LEMON BAG"],
        "VERDANT HERB":  ["VERDANT HERB CLASSIC POUCH","VERDANT HERB SPICE POUCH"],
    },
    "LUMINOS": {
        "LUMINOS SPICE": ["LUMINOS SPICE ORIGINAL BAG","LUMINOS SPICE WARM BAG"],
        "LUMINOS BREW":  ["LUMINOS BREW DARK BOX","LUMINOS BREW LIGHT BOX"],
    },
    "CRIVA": {
        "CRIVA CHOCO":   ["CRIVA CHOCO DELIGHT TIN","CRIVA CHOCO CRISP DUS","CRIVA CHOCO WAFER BOX"],
        "CRIVA BUTTER":  ["CRIVA BUTTER RICH BOX","CRIVA BUTTER LIGHT DUS"],
    },
    "NUTRIVA": {
        "NUTRIVA OAT":   ["NUTRIVA OAT ORIGINAL BOX","NUTRIVA OAT HONEY BOX","NUTRIVA OAT CHOCO BOX"],
        "NUTRIVA GRAIN": ["NUTRIVA GRAIN CRISP BOX","NUTRIVA GRAIN MALT BOX"],
    },
}

# Build lookup: subbrand_list → sub_brand → brand
SBL_TO_SB = {}
SBL_TO_BR = {}
SB_TO_BR  = {}
ALL_SBL   = []
for brand, subs in PRODUCTS.items():
    for sb, sbl_list in subs.items():
        SB_TO_BR[sb] = brand
        for sbl in sbl_list:
            SBL_TO_SB[sbl] = sb
            SBL_TO_BR[sbl] = brand
            ALL_SBL.append(sbl)

# Brand category
CATEGORY = {
    "ZEPHYR":"Candy","SOLARA":"Beverage","VERDANT":"Beverage",
    "LUMINOS":"Beverage","CRIVA":"Biscuit","NUTRIVA":"Biscuit"
}

MONTHS     = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
YEARS      = [2024, 2025, 2026]
MAX_MONTH  = {2024:12, 2025:12, 2026:7}

# ── Generate accounts per branch ──────────────────────────────────────────────
account_pool = {}
for br in BRANCH_TO_RGM:
    n   = random.randint(60, 280)
    rgm = BRANCH_TO_RGM[br]
    accs = [f"AC-{rgm[:2]}{br.split('#')[0][1:]}-{i:04d}" for i in range(n)]
    account_pool[br] = accs

# ── Generate transactions ─────────────────────────────────────────────────────
print("Generating synthetic transactions...")
rows = []
all_branches = list(BRANCH_TO_RGM.keys())

for year in YEARS:
    print(f"  {year}...")
    max_m = MAX_MONTH[year]
    for mi in range(max_m):
        month = MONTHS[mi]
        seasonal   = 1 + 0.18 * np.sin((mi - 2) * np.pi / 6)
        yr_growth  = {2024:1.0, 2025:1.14, 2026:1.09}[year]

        for br in all_branches:
            accs    = account_pool[br]
            n_active = max(1, int(len(accs) * random.uniform(0.55, 0.92)))
            active  = random.sample(accs, n_active)

            for acc in active:
                n_sku = random.choices([1,2,3], weights=[0.50,0.35,0.15])[0]
                skus  = random.sample(ALL_SBL, n_sku)
                for sku in skus:
                    base   = random.randint(80, 600)
                    actual = int(base * seasonal * yr_growth * random.uniform(0.75, 1.25))
                    if actual < 1: actual = 1
                    rows.append({
                        "REGION":       BRANCH_TO_REGION[br],
                        "BRANCH":       br,
                        "RGM":          BRANCH_TO_RGM[br],
                        "ACCOUNT":      acc,
                        "SUBBRAND LIST":sku,
                        "SUB BRAND":    SBL_TO_SB[sku],
                        "BRAND":        SBL_TO_BR[sku],
                        "CATEGORY":     CATEGORY[SBL_TO_BR[sku]],
                        "YEAR TRX":     str(year),
                        "MONTH TRX":    month,
                        "ACTUAL":       str(actual),
                    })

df = pd.DataFrame(rows)
print(f"  Total rows: {len(df):,}")
os.makedirs("demo_data", exist_ok=True)
df.to_parquet("demo_data/sales_demo.parquet", index=False)
sz = os.path.getsize("demo_data/sales_demo.parquet")/1024/1024
print(f"\nDone! demo_data/sales_demo.parquet — {sz:.1f} MB, {len(df):,} rows")
