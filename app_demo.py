import streamlit as st
import duckdb
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import io, os

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Commercial Analytics Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Data path ─────────────────────────────────────────────────────────────────
DATA_PATH = "demo_data/sales_demo.parquet" if os.path.exists("demo_data/sales_demo.parquet") \
            else r"C:/path/to/your/data/*.parquet"
IS_DEMO   = "demo_data" in DATA_PATH

# ── Design tokens ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── Base ── */
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.block-container { padding: 1.5rem 2rem 2rem; max-width: 1400px; }

/* ── Sidebar ── */
[data-testid="stSidebar"] { background: #0f172a; }
[data-testid="stSidebar"] * { color: #cbd5e1 !important; }
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stMultiSelect label { color: #94a3b8 !important; font-size: 12px !important; text-transform: uppercase; letter-spacing: .05em; }
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 { color: #f1f5f9 !important; font-size: 13px !important; font-weight: 600 !important; }
[data-testid="stSidebar"] [data-baseweb="tag"] { background: #1e293b !important; }
[data-testid="stSidebar"] .stButton > button { width: 100%; background: #1e293b; border: 1px solid #334155; color: #94a3b8; border-radius: 6px; font-size: 12px; }
[data-testid="stSidebar"] .stButton > button:hover { background: #334155; color: #f1f5f9; }
[data-testid="stSidebar"] hr { border-color: #1e293b !important; }

/* ── KPI cards ── */
.kpi-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin-bottom: 24px; }
.kpi-card { background: #fff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 16px 20px; position: relative; overflow: hidden; }
.kpi-card::before { content:''; position:absolute; top:0; left:0; width:4px; height:100%; background: var(--accent, #3b82f6); border-radius: 12px 0 0 12px; }
.kpi-label { font-size: 11px; font-weight: 600; color: #94a3b8; text-transform: uppercase; letter-spacing: .06em; margin-bottom: 6px; }
.kpi-value { font-size: 26px; font-weight: 700; color: #0f172a; line-height: 1.1; }
.kpi-delta { font-size: 12px; font-weight: 500; margin-top: 6px; }
.kpi-delta.up   { color: #10b981; }
.kpi-delta.down { color: #ef4444; }
.kpi-delta.flat { color: #94a3b8; }
@media (prefers-color-scheme: dark) {
  .kpi-card { background: #1e293b; border-color: #334155; }
  .kpi-value { color: #f1f5f9; }
}

/* ── Section headers ── */
.section-header { display: flex; align-items: center; gap: 10px; margin: 28px 0 14px; }
.section-header h2 { font-size: 15px; font-weight: 600; color: #0f172a; margin: 0; }
.section-badge { font-size: 11px; font-weight: 500; background: #eff6ff; color: #3b82f6; padding: 3px 10px; border-radius: 20px; }
.section-divider { flex: 1; height: 1px; background: #e2e8f0; }

/* ── Insight boxes ── */
.insight-box { background: #f8fafc; border-left: 4px solid #3b82f6; border-radius: 0 8px 8px 0; padding: 12px 16px; margin: 10px 0; font-size: 13px; color: #334155; line-height: 1.6; }
.insight-box.warning { border-color: #f59e0b; background: #fffbeb; color: #78350f; }
.insight-box.success { border-color: #10b981; background: #ecfdf5; color: #064e3b; }

/* ── Chart container ── */
.chart-card { background: #fff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 20px; margin-bottom: 16px; }
@media (prefers-color-scheme: dark) {
  .chart-card { background: #1e293b; border-color: #334155; }
  .section-header h2 { color: #f1f5f9; }
  .insight-box { background: #1e293b; color: #cbd5e1; }
}

/* ── Demo banner ── */
.demo-banner { background: linear-gradient(90deg,#1d4ed8,#7c3aed); border-radius: 10px; padding: 10px 18px; color: #fff; font-size: 13px; font-weight: 500; margin-bottom: 20px; display: flex; align-items: center; gap: 10px; }

/* ── Tab styling ── */
.stTabs [data-baseweb="tab-list"] { gap: 4px; background: #f1f5f9; padding: 4px; border-radius: 8px; }
.stTabs [data-baseweb="tab"] { border-radius: 6px; font-size: 13px; font-weight: 500; padding: 6px 14px; }
.stTabs [aria-selected="true"] { background: #fff !important; }

/* ── Growth badges ── */
.g-up   { color: #10b981; font-weight: 600; }
.g-down { color: #ef4444; font-weight: 600; }
</style>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
""", unsafe_allow_html=True)

# ── Constants ─────────────────────────────────────────────────────────────────
MONTH_ORDER = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]

TERRITORY = {
    "NOVA":   {"WESTLAND":["W01#GREENFIELD","W02#LAKEVIEW","W03#RIVERBEND","W04#CEDARTON","W05#MAPLEWOOD"],
               "EASTLAND":["E01#BRIGHTPORT","E02#HILLCREST","E03#STONEGATE","E04#FAIRVIEW"]},
    "CREST":  {"NORTHLAND":["N01#PINEWOOD","N02#IRONDALE","N03#SUNRIDGE","N04#COLDWATER"],
               "CENTRAL":  ["C01#MIDVALE","C02#REDSTONE","C03#ELMHURST","C04#FOXBURY","C05#GRAYMONT"]},
    "APEX":   {"SOUTHLAND":["S01#BAYSIDE","S02#PALMCOVE","S03#DRIFTWOOD","S04#SANDALWOOD"],
               "HIGHLAND": ["H01#SUMMIT","H02#RIDGEVIEW","H03#CLIFTON","H04#MONTROSE","H05#EASTVALE"]},
    "VERTEX": {"FAREAST":  ["F01#HORIZON","F02#SEAVIEW","F03#OAKDALE"],
               "ISLAND":   ["I01#CORAL","I02#TIDEMARK"]},
}
BRANCH_TO_RGM    = {br: rgm  for rgm,regs in TERRITORY.items() for reg,brs in regs.items() for br in brs}
BRANCH_TO_REGION = {br: reg  for rgm,regs in TERRITORY.items() for reg,brs in regs.items() for br in brs}
RGM_OPTIONS      = sorted(TERRITORY.keys())

PRODUCTS = {
    "ZEPHYR":  {"ZEPHYR MINT":["ZEPHYR MINT CLASSIC BAG","ZEPHYR MINT COOL BAG","ZEPHYR MINT STRONG ROLL"],
                "ZEPHYR BERRY":["ZEPHYR BERRY WILD BAG","ZEPHYR BERRY SOFT BAG"],
                "ZEPHYR CITRUS":["ZEPHYR CITRUS FRESH BAG","ZEPHYR CITRUS BURST ROLL"]},
    "SOLARA":  {"SOLARA BLEND":["SOLARA BLEND RICH BOX","SOLARA BLEND MILD BOX","SOLARA BLEND DARK BOX"],
                "SOLARA LITE": ["SOLARA LITE SMOOTH BOX","SOLARA LITE CRISP BOX"]},
    "VERDANT": {"VERDANT GREEN":["VERDANT GREEN ORIGINAL BAG","VERDANT GREEN HONEY TPL","VERDANT GREEN LEMON BAG"],
                "VERDANT HERB": ["VERDANT HERB CLASSIC POUCH","VERDANT HERB SPICE POUCH"]},
    "LUMINOS": {"LUMINOS SPICE":["LUMINOS SPICE ORIGINAL BAG","LUMINOS SPICE WARM BAG"],
                "LUMINOS BREW": ["LUMINOS BREW DARK BOX","LUMINOS BREW LIGHT BOX"]},
    "CRIVA":   {"CRIVA CHOCO": ["CRIVA CHOCO DELIGHT TIN","CRIVA CHOCO CRISP DUS","CRIVA CHOCO WAFER BOX"],
                "CRIVA BUTTER":["CRIVA BUTTER RICH BOX","CRIVA BUTTER LIGHT DUS"]},
    "NUTRIVA": {"NUTRIVA OAT": ["NUTRIVA OAT ORIGINAL BOX","NUTRIVA OAT HONEY BOX","NUTRIVA OAT CHOCO BOX"],
                "NUTRIVA GRAIN":["NUTRIVA GRAIN CRISP BOX","NUTRIVA GRAIN MALT BOX"]},
}
ALL_BRANDS   = list(PRODUCTS.keys())
ALL_SUBBRANDS= [sb for p in PRODUCTS.values() for sb in p.keys()]
ALL_SBL      = [s  for p in PRODUCTS.values() for sbs in p.values() for s in sbs]
SBL_TO_SB    = {s:sb for p in PRODUCTS.values() for sb,sl in p.items() for s in sl}
SBL_TO_BR    = {s:br for br,p in PRODUCTS.items() for sbs in p.values() for s in sbs}
CATEGORY     = {"ZEPHYR":"Candy","SOLARA":"Beverage","VERDANT":"Beverage",
                "LUMINOS":"Beverage","CRIVA":"Biscuit","NUTRIVA":"Biscuit"}

# Color palette
BRAND_COLORS = {"ZEPHYR":"#3b82f6","SOLARA":"#f59e0b","VERDANT":"#10b981",
                "LUMINOS":"#8b5cf6","CRIVA":"#ef4444","NUTRIVA":"#06b6d4"}
RGM_COLORS   = {"NOVA":"#3b82f6","CREST":"#10b981","APEX":"#f59e0b","VERTEX":"#8b5cf6"}

# ── Helpers ───────────────────────────────────────────────────────────────────
def sql_esc(v): return str(v).replace("'","''")

def month_to_num_sql(col='"MONTH TRX"'):
    return "CASE " + " ".join(f"WHEN {col}='{m}' THEN {i+1}" for i,m in enumerate(MONTH_ORDER)) + " ELSE 99 END"

def build_where(f):
    clauses = []
    for col,vals in f.items():
        if vals:
            iv = ",".join(f"'{sql_esc(v)}'" for v in vals)
            clauses.append(f'"{col}" IN ({iv})')
    return ("WHERE "+" AND ".join(clauses)) if clauses else ""

def add_filter(where, extra_clause):
    """Safely append an extra SQL clause to an existing WHERE string."""
    if not extra_clause:
        return where
    if where.strip():
        return where + " AND " + extra_clause
    return "WHERE " + extra_clause

def fmt_num(n, prefix="", suffix=""):
    if n is None or (isinstance(n,float) and pd.isna(n)): return "—"
    if abs(n) >= 1_000_000: return f"{prefix}{n/1_000_000:.1f}M{suffix}"
    if abs(n) >= 1_000:     return f"{prefix}{n/1_000:.1f}K{suffix}"
    return f"{prefix}{n:,.0f}{suffix}"

def fmt_growth(v):
    if v is None or (isinstance(v,float) and pd.isna(v)): return "—"
    arrow = "▲" if v>=0 else "▼"
    cls   = "up" if v>=0 else "down"
    return f'<span class="g-{cls}">{arrow} {abs(v):.1%}</span>'

def section(title, badge=None):
    b = f'<span class="section-badge">{badge}</span>' if badge else ""
    st.markdown(f"""<div class="section-header">
      <h2>{title}</h2>{b}<div class="section-divider"></div></div>""", unsafe_allow_html=True)

def insight(text, kind="info"):
    st.markdown(f'<div class="insight-box {kind if kind!="info" else ""}">{text}</div>', unsafe_allow_html=True)

# kpi_card replaced by inline render_kpi() below

# ── Cache helpers ─────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def get_unique(col):
    return [r[0] for r in duckdb.sql(f"""
        SELECT DISTINCT "{col}" FROM read_parquet('{DATA_PATH}',union_by_name=True)
        WHERE "{col}" IS NOT NULL ORDER BY "{col}"
    """).fetchall()]

@st.cache_data(show_spinner=False)
def get_meta():
    rows = []
    for brand,subs in PRODUCTS.items():
        for sb,sbls in subs.items():
            for sbl in sbls:
                rows.append({"SUBBRAND LIST":sbl,"SUB BRAND":sb,"BRAND":brand,"CATEGORY":CATEGORY[brand]})
    return pd.DataFrame(rows)

df_meta = get_meta()

# ── Load options ──────────────────────────────────────────────────────────────
opts_year   = get_unique("YEAR TRX")
opts_region = get_unique("REGION")
opts_branch = get_unique("BRANCH")
opts_brand  = ALL_BRANDS
opts_sb     = ALL_SUBBRANDS
opts_sbl    = ALL_SBL

latest_year = max(opts_year)
ytd_raw = duckdb.sql(f"""
    SELECT DISTINCT "MONTH TRX" FROM read_parquet('{DATA_PATH}',union_by_name=True)
    WHERE "YEAR TRX"='{latest_year}'
""").fetchall()
ytd_months    = [r[0] for r in ytd_raw if r[0] in MONTH_ORDER]
ytd_max_month = max([MONTH_ORDER.index(m)+1 for m in ytd_months]) if ytd_months else 12

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 📊 Sales Dashboard")
    st.markdown("---")

    st.markdown("**PERIOD**")
    sel_year  = st.multiselect("Year", opts_year, default=opts_year, label_visibility="collapsed")
    sel_month = st.multiselect("Month", MONTH_ORDER, label_visibility="collapsed",
                               placeholder="All months")

    st.markdown("**TERRITORY**")
    sel_rgm    = st.multiselect("RGM",    RGM_OPTIONS, label_visibility="collapsed", placeholder="All RGM")
    sel_region = st.multiselect("Region", opts_region,  label_visibility="collapsed", placeholder="All regions")
    sel_branch = st.multiselect("Branch", [b.split("#")[1] for b in opts_branch],
                                label_visibility="collapsed", placeholder="All branches")

    st.markdown("**PRODUCT**")
    sel_brand = st.multiselect("Brand",       opts_brand, label_visibility="collapsed", placeholder="All brands")
    sel_sb    = st.multiselect("Sub Brand",   opts_sb,    label_visibility="collapsed", placeholder="All sub brands")
    sel_sbl   = st.multiselect("SKU",         opts_sbl,   label_visibility="collapsed", placeholder="All SKUs")

    st.markdown("---")
    if st.button("↺ Reset filters"):
        st.cache_data.clear(); st.rerun()

# ── Resolve filters ───────────────────────────────────────────────────────────
# Resolve RGM/Branch
rgm_branches, rgm_regions = [], []
if sel_rgm:
    for rgm,regs in TERRITORY.items():
        if rgm in sel_rgm:
            for reg,brs in regs.items():
                rgm_branches += brs; rgm_regions.append(reg)

# Resolve branch display → raw
sel_branch_raw = [b for b in opts_branch if b.split("#")[1] in sel_branch] if sel_branch else []

# Resolve product
df_mf = df_meta.copy()
if sel_brand: df_mf = df_mf[df_mf["BRAND"].isin(sel_brand)]
if sel_sb:    df_mf = df_mf[df_mf["SUB BRAND"].isin(sel_sb)]
resolved_sbl = list(df_mf["SUBBRAND LIST"].unique())
if sel_sbl:
    resolved_sbl = list(set(resolved_sbl)&set(sel_sbl)) if (sel_brand or sel_sb) else sel_sbl

f = {}
if sel_year:   f["YEAR TRX"] = [str(y) for y in sel_year]
if sel_month:  f["MONTH TRX"] = sel_month
if sel_region:     f["REGION"] = sel_region
elif rgm_regions:  f["REGION"] = list(set(rgm_regions))
if sel_branch_raw:     f["BRANCH"] = sel_branch_raw
elif rgm_branches:     f["BRANCH"] = rgm_branches
if sel_rgm and not sel_region and not sel_branch: f["RGM"] = sel_rgm

# Build WHERE base dari territory & period filters
WHERE_base    = build_where(f)
f_no_year     = {k:v for k,v in f.items() if k!="YEAR TRX"}
WHERE_NY_base = build_where(f_no_year)

# Tambahkan filter SUBBRAND LIST jika ada (brand/sub brand dipilih)
def add_sbl_filter(where, sbl_list):
    """Tambahkan filter SUBBRAND LIST ke WHERE yang sudah ada."""
    if not sbl_list:
        return where
    iv = ", ".join(f"'{sql_esc(v)}'" for v in sbl_list)
    clause = f'"SUBBRAND LIST" IN ({iv})'
    return add_filter(where, clause)

WHERE    = add_sbl_filter(WHERE_base,    resolved_sbl if (sel_brand or sel_sb or sel_sbl) else [])
WHERE_NY = add_sbl_filter(WHERE_NY_base, resolved_sbl if (sel_brand or sel_sb or sel_sbl) else [])

# ── Header ────────────────────────────────────────────────────────────────────
if IS_DEMO:
    st.markdown("""
<div style="
    background: linear-gradient(90deg, #1d4ed8, #7c3aed);
    border-radius: 10px;
    padding: 12px 20px;
    color: #ffffff;
    font-size: 13px;
    font-weight: 500;
    margin-top: 20px;
    margin-bottom: 8px;
    display: flex;
    align-items: center;
    gap: 10px;
    box-sizing: border-box;
    width: 100%;
    white-space: normal;
    word-break: break-word;
">
🎭 &nbsp;<strong>Portfolio Demo</strong> &nbsp;—&nbsp; All data is synthetic.
Fully interactive mockup built to demonstrate commercial analytics.
</div>
""", unsafe_allow_html=True)

st.markdown("## Commercial Analytics Dashboard")
st.caption(f"Data: `{DATA_PATH}` · Filters active: {len([v for v in f.values() if v])} of {len(f)} dimensions")

# ══════════════════════════════════════════════════════════════════════════════
# 1. KPI SUMMARY
# ══════════════════════════════════════════════════════════════════════════════
section("Key Performance Indicators", "Summary")

@st.cache_data(show_spinner=False)
def get_kpi(where):
    return duckdb.sql(f"""
        SELECT
            COUNT(DISTINCT "ACCOUNT") AS oc,
            SUM(CAST("ACTUAL" AS DOUBLE)) AS vol,
            COUNT(DISTINCT "YEAR TRX"||'-'||"MONTH TRX") AS n_period
        FROM read_parquet('{DATA_PATH}',union_by_name=True) {where}
    """).fetchone()

@st.cache_data(show_spinner=False)
def get_kpi_prev(where_ny, latest_year):
    """Compute YoY delta: current year vs previous year (same YTD months)."""
    mn = month_to_num_sql()
    rows = duckdb.sql(f"""
        SELECT "YEAR TRX",
               COUNT(DISTINCT "ACCOUNT") AS oc,
               SUM(CAST("ACTUAL" AS DOUBLE)) AS vol
        FROM read_parquet('{DATA_PATH}',union_by_name=True) {add_filter(where_ny, f"({mn}) <= {ytd_max_month}")}
        GROUP BY "YEAR TRX" ORDER BY "YEAR TRX"
    """).df()
    return rows

with st.spinner(""):
    kpi  = get_kpi(WHERE)
    kpip = get_kpi_prev(WHERE_NY, latest_year)

oc    = kpi[0] or 0
vol   = kpi[2] or 0
n_per = kpi[2] or 1
avg   = (kpi[1] or 0) / n_per if n_per>0 else 0
ds    = (kpi[1] or 0) / oc if oc>0 else 0

# YoY for current vs previous year
years_avail = kpip["YEAR TRX"].tolist()
yoy_vol = yoy_oc = None
if len(years_avail) >= 2:
    cur  = kpip[kpip["YEAR TRX"]==latest_year]
    prev = kpip[kpip["YEAR TRX"]==str(int(latest_year)-1)]
    if not cur.empty and not prev.empty:
        yoy_vol = float(cur["vol"].iloc[0])/float(prev["vol"].iloc[0])-1 if float(prev["vol"].iloc[0])>0 else None
        yoy_oc  = float(cur["oc"].iloc[0])/float(prev["oc"].iloc[0])-1  if float(prev["oc"].iloc[0])>0  else None

# KPI cards via st.columns — reliable across all Streamlit versions
kc1, kc2, kc3, kc4 = st.columns(4)

def render_kpi(col, label, value, delta=None, delta_label="", accent="#3b82f6"):
    delta_html = ""
    if delta is not None:
        cls = "up" if delta >= 0 else "down"
        ar  = "▲" if delta >= 0 else "▼"
        delta_html = f'<div class="kpi-delta {cls}">{ar} {abs(delta):.1%} {delta_label}</div>'
    col.markdown(f'''<div class="kpi-card" style="--accent:{accent}">
  <div class="kpi-label">{label}</div>
  <div class="kpi-value">{value}</div>
  {delta_html}
</div>''', unsafe_allow_html=True)

render_kpi(kc1, "Volume (YTD)",     fmt_num(kpi[1] or 0), yoy_vol, "vs prior year", "#3b82f6")
render_kpi(kc2, "Outlet Coverage",  fmt_num(oc),           yoy_oc,  "vs prior year", "#10b981")
render_kpi(kc3, "Avg Vol / Month",  fmt_num(avg),          accent="#f59e0b")
render_kpi(kc4, "Dropsize (Vol/OC)",f"{ds:.2f}",           accent="#8b5cf6")

# ══════════════════════════════════════════════════════════════════════════════
# 2. VOLUME TREND
# ══════════════════════════════════════════════════════════════════════════════
section("Volume & Coverage Trend")

tr1, tr2 = st.columns([3,1])
with tr2:
    trend_metric = st.radio("Metric", ["Volume","Outlet Coverage","Dropsize"], label_visibility="collapsed")
    color_by     = st.selectbox("Break by", ["None","RGM","Region","Brand","Category"], label_visibility="collapsed")

y_col = {"Volume":"vol","Outlet Coverage":"oc","Dropsize":"ds"}[trend_metric]

@st.cache_data(show_spinner=False)
def get_trend(where, grp=None):
    mn = month_to_num_sql()
    g  = f', "{grp}" AS dim' if grp else ""
    gb = f', "{grp}"'        if grp else ""
    df = duckdb.sql(f"""
        SELECT "YEAR TRX" AS yr, "MONTH TRX" AS mo, {mn} AS mn
               {g},
               SUM(CAST("ACTUAL" AS DOUBLE)) AS vol,
               COUNT(DISTINCT "ACCOUNT") AS oc
        FROM read_parquet('{DATA_PATH}',union_by_name=True) {where}
        GROUP BY yr,mo,mn {gb} ORDER BY yr,mn
    """).df()
    df["period"] = df["mo"]+" "+df["yr"]
    df["sort"]   = df["yr"].astype(str)+df["mn"].astype(str).str.zfill(2)
    df = df.sort_values("sort")
    df["ds"] = df["vol"]/df["oc"].replace(0,float("nan"))
    return df

@st.cache_data(show_spinner=False)
def get_trend_rgm(where):
    mn = month_to_num_sql()
    cases = " ".join(f'WHEN "RGM"=\'{r}\' THEN \'{r}\'' for r in RGM_OPTIONS)
    df = duckdb.sql(f"""
        SELECT "YEAR TRX" AS yr, "MONTH TRX" AS mo, {mn} AS mn,
               CASE {cases} ELSE 'Other' END AS dim,
               SUM(CAST("ACTUAL" AS DOUBLE)) AS vol,
               COUNT(DISTINCT "ACCOUNT") AS oc
        FROM read_parquet('{DATA_PATH}',union_by_name=True) {where}
        GROUP BY yr,mo,mn,dim ORDER BY yr,mn
    """).df()
    df["period"] = df["mo"]+" "+df["yr"]
    df["sort"]   = df["yr"].astype(str)+df["mn"].astype(str).str.zfill(2)
    df = df.sort_values("sort")
    df["ds"] = df["vol"]/df["oc"].replace(0,float("nan"))
    return df

with tr1:
    with st.spinner(""):
        grp_map = {"None":None,"RGM":"RGM","Region":"REGION","Brand":"BRAND","Category":"CATEGORY"}
        grp     = grp_map[color_by]
        if color_by=="RGM":
            df_tr = get_trend_rgm(WHERE)
        else:
            df_tr = get_trend(WHERE, grp)

        period_order = list(dict.fromkeys(df_tr.sort_values("sort")["period"].tolist()))
        df_tr["period"] = pd.Categorical(df_tr["period"], categories=period_order, ordered=True)

        color_col = "dim" if grp else None
        color_map = BRAND_COLORS if color_by=="Brand" else (RGM_COLORS if color_by=="RGM" else None)

        fig = px.line(df_tr.sort_values("period"), x="period", y=y_col,
                      color=color_col, markers=True,
                      color_discrete_map=color_map or {},
                      labels={"period":"","vol":"Volume","oc":"Outlet Coverage","ds":"Dropsize","dim":color_by},
                      height=340)
        fig.update_layout(
            plot_bgcolor="white", paper_bgcolor="white",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
            margin=dict(l=0,r=0,t=10,b=0),
            xaxis=dict(tickangle=-45, showgrid=False, linecolor="#e2e8f0"),
            yaxis=dict(gridcolor="#f1f5f9", linecolor="#e2e8f0"),
            hovermode="x unified", font=dict(family="Inter", size=12),
        )
        fig.update_traces(line=dict(width=2.5))
        st.plotly_chart(fig, use_container_width=True)

        # Pivot table below
        if color_col:
            pv = df_tr.pivot_table(index="dim", columns="period", values=y_col, aggfunc="sum")
        else:
            pv = df_tr.set_index("period")[[y_col]].T
            pv.index = [trend_metric]
        pv = pv.fillna(0)[[c for c in period_order if c in pv.columns]]
        fmt = "{:,.2f}" if y_col=="ds" else "{:,.0f}"
        st.dataframe(pv.style.format(fmt),
                     use_container_width=True, height=180)

# ══════════════════════════════════════════════════════════════════════════════
# 3. YTD COMPARISON
# ══════════════════════════════════════════════════════════════════════════════
section("YTD Performance Comparison", f"YTD Jan–{MONTH_ORDER[ytd_max_month-1]}")
st.caption(f"YTD calculated through **{MONTH_ORDER[ytd_max_month-1]}** across all years for fair comparison.")

@st.cache_data(show_spinner=False)
def get_ytd(dim_col, where_ny, ytd_max):
    mn = month_to_num_sql()
    if dim_col == "BRAND":
        df = duckdb.sql(f"""
            SELECT "YEAR TRX" AS yr, "BRAND" AS dim,
                   SUM(CAST("ACTUAL" AS DOUBLE)) AS vol,
                   COUNT(DISTINCT "ACCOUNT") AS oc
            FROM read_parquet('{DATA_PATH}',union_by_name=True)
            {add_filter(where_ny, f"({mn})<={ytd_max}")}
            GROUP BY yr, dim
        """).df()
    elif dim_col == "RGM":
        df = duckdb.sql(f"""
            SELECT "YEAR TRX" AS yr, "RGM" AS dim,
                   SUM(CAST("ACTUAL" AS DOUBLE)) AS vol,
                   COUNT(DISTINCT "ACCOUNT") AS oc
            FROM read_parquet('{DATA_PATH}',union_by_name=True)
            {add_filter(where_ny, f"({mn})<={ytd_max}")}
            GROUP BY yr, dim
        """).df()
    else:
        df = duckdb.sql(f"""
            SELECT "YEAR TRX" AS yr, "REGION" AS dim,
                   SUM(CAST("ACTUAL" AS DOUBLE)) AS vol,
                   COUNT(DISTINCT "ACCOUNT") AS oc
            FROM read_parquet('{DATA_PATH}',union_by_name=True)
            {add_filter(where_ny, f"({mn})<={ytd_max}")}
            GROUP BY yr, dim
        """).df()
    df["ds"] = df["vol"]/df["oc"].replace(0,float("nan"))
    return df

ytd_dim_label = st.radio("View by", ["Region","RGM","Brand"], horizontal=True, label_visibility="collapsed")
ytd_dim_map   = {"Region":"REGION","RGM":"RGM","Brand":"BRAND"}
ytd_metric    = st.radio("YTD Metric", ["Volume","Outlet Coverage"], horizontal=True, label_visibility="collapsed")
ytd_y         = "vol" if ytd_metric=="Volume" else "oc"

with st.spinner(""):
    df_ytd  = get_ytd(ytd_dim_map[ytd_dim_label], WHERE_NY, ytd_max_month)
    years_y = sorted(df_ytd["yr"].unique().tolist())
    dims_y  = df_ytd.groupby("dim")[ytd_y].sum().sort_values(ascending=False).index.tolist()
    pivot_y = df_ytd.pivot_table(index="dim",columns="yr",values=ytd_y,aggfunc="sum").fillna(0)

    # Grouped bar
    fig_ytd = go.Figure()
    bar_colors = ["#cbd5e1","#93c5fd","#3b82f6"][-len(years_y):]
    for i,yr in enumerate(years_y):
        vals = [pivot_y.loc[d,yr] if yr in pivot_y.columns else 0 for d in dims_y]
        fig_ytd.add_trace(go.Bar(name=str(yr), x=dims_y, y=vals,
                                  marker_color=bar_colors[i%len(bar_colors)],
                                  text=[fmt_num(v) for v in vals], textposition="outside",
                                  textfont=dict(size=11)))
    fig_ytd.update_layout(
        barmode="group", height=360, plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(l=0,r=0,t=10,b=0),
        legend=dict(orientation="h",yanchor="bottom",y=1.02),
        xaxis=dict(showgrid=False,linecolor="#e2e8f0"),
        yaxis=dict(gridcolor="#f1f5f9",linecolor="#e2e8f0"),
        font=dict(family="Inter",size=12), hovermode="x unified",
    )
    st.plotly_chart(fig_ytd, use_container_width=True)

    # Growth table
    if len(years_y) >= 2:
        rows_g = []
        for dim in dims_y:
            row = {"Dimension": dim}
            for yr in years_y:
                row[f"YTD {yr}"] = fmt_num(pivot_y.loc[dim,yr]) if yr in pivot_y.columns else "—"
            for i in range(1,len(years_y)):
                p,c = years_y[i-1], years_y[i]
                vp  = pivot_y.loc[dim,p] if p in pivot_y.columns else 0
                vc  = pivot_y.loc[dim,c] if c in pivot_y.columns else 0
                g   = (vc/vp-1) if vp>0 else None
                row[f"Growth {p}→{c}"] = fmt_growth(g) if g is not None else "—"
            rows_g.append(row)
        df_g = pd.DataFrame(rows_g)
        st.write(df_g.to_html(index=False, escape=False, classes="dataframe"), unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# 4. BRAND & PRODUCT MIX
# ══════════════════════════════════════════════════════════════════════════════
section("Brand & Product Mix")

col1, col2 = st.columns(2)

@st.cache_data(show_spinner=False)
def get_brand_vol(where):
    return duckdb.sql(f"""
        SELECT "BRAND", "CATEGORY",
               SUM(CAST("ACTUAL" AS DOUBLE)) AS vol,
               COUNT(DISTINCT "ACCOUNT") AS oc
        FROM read_parquet('{DATA_PATH}',union_by_name=True) {where}
        GROUP BY "BRAND","CATEGORY" ORDER BY vol DESC
    """).df()

@st.cache_data(show_spinner=False)
def get_sb_vol(where, topn=12):
    return duckdb.sql(f"""
        SELECT "SUB BRAND",
               SUM(CAST("ACTUAL" AS DOUBLE)) AS vol,
               COUNT(DISTINCT "ACCOUNT") AS oc
        FROM read_parquet('{DATA_PATH}',union_by_name=True) {where}
        GROUP BY "SUB BRAND" ORDER BY vol DESC LIMIT {topn}
    """).df()

with col1:
    df_br = get_brand_vol(WHERE)
    fig_pie = px.pie(df_br, names="BRAND", values="vol", hole=0.42, height=320,
                     color="BRAND", color_discrete_map=BRAND_COLORS)
    fig_pie.update_traces(textposition="inside", textinfo="percent+label",
                          textfont_size=11)
    fig_pie.update_layout(showlegend=False, margin=dict(l=0,r=0,t=0,b=0),
                          paper_bgcolor="rgba(0,0,0,0)", font=dict(family="Inter"))
    st.markdown("**Volume share by Brand**")
    st.plotly_chart(fig_pie, use_container_width=True)

with col2:
    df_sb = get_sb_vol(WHERE)
    df_sb["ds"] = df_sb["vol"]/df_sb["oc"].replace(0,float("nan"))
    fig_bar = px.bar(df_sb, x="vol", y="SUB BRAND", orientation="h",
                     color="vol", color_continuous_scale=["#dbeafe","#1d4ed8"],
                     height=320, labels={"vol":"Volume","SUB BRAND":"Sub Brand"})
    fig_bar.update_layout(yaxis=dict(categoryorder="total ascending"),
                          coloraxis_showscale=False, margin=dict(l=0,r=0,t=0,b=0),
                          plot_bgcolor="white", paper_bgcolor="rgba(0,0,0,0)",
                          font=dict(family="Inter",size=12),
                          xaxis=dict(showgrid=False), yaxis2=dict(showgrid=False))
    st.markdown("**Top Sub Brands by Volume**")
    st.plotly_chart(fig_bar, use_container_width=True)

# Dropsize ranking
section("Dropsize Analysis", "Vol ÷ OC")
st.caption("Dropsize = average volume per active outlet per period. Higher dropsize = deeper engagement per account.")

@st.cache_data(show_spinner=False)
def get_ds_brand(where):
    return duckdb.sql(f"""
        SELECT "BRAND",
               SUM(CAST("ACTUAL" AS DOUBLE)) AS vol,
               COUNT(DISTINCT "ACCOUNT") AS oc
        FROM read_parquet('{DATA_PATH}',union_by_name=True) {where}
        GROUP BY "BRAND"
    """).df()

@st.cache_data(show_spinner=False)
def get_ds_region(where):
    return duckdb.sql(f"""
        SELECT "REGION",
               SUM(CAST("ACTUAL" AS DOUBLE)) AS vol,
               COUNT(DISTINCT "ACCOUNT") AS oc
        FROM read_parquet('{DATA_PATH}',union_by_name=True) {where}
        GROUP BY "REGION"
    """).df()

dc1, dc2 = st.columns(2)
with dc1:
    df_dsb = get_ds_brand(WHERE)
    df_dsb["ds"] = df_dsb["vol"]/df_dsb["oc"].replace(0,float("nan"))
    df_dsb = df_dsb.sort_values("ds",ascending=True)
    fig_ds = px.bar(df_dsb, x="ds", y="BRAND", orientation="h",
                    color="BRAND", color_discrete_map=BRAND_COLORS, height=280,
                    labels={"ds":"Dropsize","BRAND":"Brand"})
    fig_ds.update_layout(showlegend=False, plot_bgcolor="white", paper_bgcolor="rgba(0,0,0,0)",
                         margin=dict(l=0,r=0,t=0,b=0), font=dict(family="Inter",size=12),
                         xaxis=dict(showgrid=False), yaxis=dict(showgrid=False))
    st.markdown("**Dropsize by Brand**")
    st.plotly_chart(fig_ds, use_container_width=True)

with dc2:
    df_dsr = get_ds_region(WHERE)
    df_dsr["ds"] = df_dsr["vol"]/df_dsr["oc"].replace(0,float("nan"))
    df_dsr = df_dsr.sort_values("ds",ascending=True)
    fig_dsr = px.bar(df_dsr, x="ds", y="REGION", orientation="h",
                     color="ds", color_continuous_scale=["#d1fae5","#065f46"], height=280,
                     labels={"ds":"Dropsize","REGION":"Region"})
    fig_dsr.update_layout(coloraxis_showscale=False, plot_bgcolor="white",
                          paper_bgcolor="rgba(0,0,0,0)", margin=dict(l=0,r=0,t=0,b=0),
                          font=dict(family="Inter",size=12),
                          xaxis=dict(showgrid=False), yaxis=dict(showgrid=False))
    st.markdown("**Dropsize by Region**")
    st.plotly_chart(fig_dsr, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# 5. OUTLET COVERAGE HEATMAP
# ══════════════════════════════════════════════════════════════════════════════
section("Outlet Coverage Distribution", "OC")

@st.cache_data(show_spinner=False)
def get_oc_matrix(where):
    return duckdb.sql(f"""
        SELECT "REGION", "BRAND",
               COUNT(DISTINCT "ACCOUNT") AS oc
        FROM read_parquet('{DATA_PATH}',union_by_name=True) {where}
        GROUP BY "REGION","BRAND"
    """).df()

df_oc = get_oc_matrix(WHERE)
pv_oc = df_oc.pivot_table(index="REGION", columns="BRAND", values="oc", aggfunc="sum").fillna(0)
fig_hm = px.imshow(pv_oc, color_continuous_scale="Blues", aspect="auto",
                   text_auto=True, height=300,
                   labels=dict(color="Outlets"))
fig_hm.update_layout(margin=dict(l=0,r=0,t=0,b=0), font=dict(family="Inter",size=11),
                     coloraxis_showscale=False, paper_bgcolor="rgba(0,0,0,0)")
fig_hm.update_traces(texttemplate="%{z:,.0f}", textfont_size=10)
st.markdown("**Unique Outlets: Region × Brand**")
st.plotly_chart(fig_hm, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# 6. EXPORT
# ══════════════════════════════════════════════════════════════════════════════
section("Export")
if st.button("⬇ Download Pivot Table (Excel)"):
    with st.spinner("Building pivot..."):
        mn = month_to_num_sql()
        df_exp = duckdb.sql(f"""
            SELECT "REGION", "BRANCH", "RGM", "BRAND", "SUB BRAND", "SUBBRAND LIST",
                   "YEAR TRX" AS yr, "MONTH TRX" AS mo, {mn} AS mn,
                   SUM(CAST("ACTUAL" AS DOUBLE)) AS vol,
                   COUNT(DISTINCT "ACCOUNT") AS oc
            FROM read_parquet('{DATA_PATH}',union_by_name=True) {WHERE}
            GROUP BY 1,2,3,4,5,6,7,8,9 ORDER BY yr,mn
        """).df()
        df_exp["period"]  = df_exp["mo"]+" "+df_exp["yr"]
        df_exp["ds"]      = df_exp["vol"]/df_exp["oc"].replace(0,float("nan"))
        ROWS   = ["REGION","BRANCH","RGM","BRAND","SUB BRAND","SUBBRAND LIST"]
        PERIOD = df_exp.sort_values(["yr","mn"])["period"].drop_duplicates().tolist()

        def add_lvl(pv, name):
            pv = pv.copy()
            pv.columns = pd.MultiIndex.from_tuples([(name,c) for c in pv.columns])
            return pv

        pv_v = df_exp.pivot_table(index=ROWS,columns="period",values="vol",aggfunc="sum").reindex(columns=PERIOD).fillna(0)
        pv_o = df_exp.pivot_table(index=ROWS,columns="period",values="oc", aggfunc="sum").reindex(columns=PERIOD).fillna(0)
        pv_d = pv_v/pv_o.replace(0,float("nan"))
        df_final = pd.concat([add_lvl(pv_v,"Volume"),add_lvl(pv_o,"OC"),add_lvl(pv_d,"Dropsize")],axis=1).fillna(0)
        buf = io.BytesIO()
        with pd.ExcelWriter(buf,engine="openpyxl") as w:
            df_final.to_excel(w,sheet_name="Pivot")
        buf.seek(0)
    st.download_button("📥 Download Excel", data=buf, file_name="sales_pivot.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

with st.expander("🔍 Raw data preview (500 rows)"):
    @st.cache_data(show_spinner=False)
    def get_sample(where):
        return duckdb.sql(f"SELECT * FROM read_parquet('{DATA_PATH}',union_by_name=True) {where} LIMIT 500").df()
    st.dataframe(get_sample(WHERE), use_container_width=True, height=340)
