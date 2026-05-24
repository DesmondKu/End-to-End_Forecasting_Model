"""
DAY 2 — Data Cleaning Pipeline & Consolidated Planning Database
================================================================
This script does what "AI alone cannot do reliably":
- Reads 3 messy, inconsistent regional Excel files
- Standardises column names, dates, currencies and categories
- Removes duplicates and fills missing values intelligently
- Consolidates everything into ONE trusted planning dataset
- Saves to PostgreSQL — a production-grade shared database
- Exports a clean master Excel file for planners who still need Excel
- Prints a full audit report so stakeholders can trust the data

This is the FOUNDATION that makes forecasting and AI possible.

BEFORE RUNNING: See SETUP_POSTGRESQL.md for database setup instructions.
"""

import pandas as pd
import numpy as np
import os
import warnings
from sqlalchemy import create_engine, text

warnings.filterwarnings("ignore")

# ── PostgreSQL connection settings ─────────────────────────────────────────────
# Update these if you used different values during setup
PG_CONFIG = {
    "host":     "localhost",
    "port":     5433,
    "database": "sts_planning",
    "user":     "sts_planner",
    "password": "planning2024",
}

INPUT_DIR  = "raw_regional_data"
OUTPUT_DIR = "planning_database"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# USD exchange rates (for normalising all revenue to USD)
FX_RATES = {"AUD": 0.645, "EUR": 1.09, "USD": 1.0}

print("=" * 65)
print("  SEA TO SUMMIT — SUPPLY CHAIN DATA PIPELINE")
print("  Day 2: Clean, Standardise & Consolidate")
print("  Database: PostgreSQL")
print("=" * 65)


# ══════════════════════════════════════════════════════════════════
# CONNECT TO POSTGRESQL
# ══════════════════════════════════════════════════════════════════
print("\n🔌 Connecting to PostgreSQL...")

try:
    connection_string = (
        f"postgresql+psycopg2://{PG_CONFIG['user']}:{PG_CONFIG['password']}"
        f"@{PG_CONFIG['host']}:{PG_CONFIG['port']}/{PG_CONFIG['database']}"
    )
    engine = create_engine(connection_string)

    # Test the connection
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version()")).fetchone()
        pg_version = result[0].split(",")[0]  # e.g. "PostgreSQL 16.2"

    print(f"   ✅ Connected → {pg_version}")
    print(f"   ✅ Database  → {PG_CONFIG['database']} on {PG_CONFIG['host']}")

except Exception as e:
    print(f"\n   ❌ CONNECTION FAILED: {e}")
    print("\n   → Check that PostgreSQL is running.")
    print("   → See SETUP_POSTGRESQL.md for step-by-step instructions.")
    exit(1)


# ══════════════════════════════════════════════════════════════════
# STEP 1 — Read all 3 regional files
# ══════════════════════════════════════════════════════════════════
print("\n📂 STEP 1: Reading regional files...")

au_raw = pd.read_excel(f"{INPUT_DIR}/Australia_Sales_Planning.xlsx")
eu_raw = pd.read_excel(f"{INPUT_DIR}/Europe_Demand_Report.xlsx")
us_raw = pd.read_excel(f"{INPUT_DIR}/USA_Sales_Data.xlsx")

print(f"   AU raw rows: {len(au_raw):>4}  |  columns: {list(au_raw.columns)}")
print(f"   EU raw rows: {len(eu_raw):>4}  |  columns: {list(eu_raw.columns)}")
print(f"   US raw rows: {len(us_raw):>4}  |  columns: {list(us_raw.columns)}")


# ══════════════════════════════════════════════════════════════════
# STEP 2 — Standardise each region to a common schema
# ══════════════════════════════════════════════════════════════════
print("\n🔧 STEP 2: Standardising column names and formats...")

def standardise_australia(df: pd.DataFrame) -> pd.DataFrame:
    """Map AU columns → standard schema."""
    out = pd.DataFrame()
    out["sku"]               = df["SKU_Code"].str.strip()
    out["product_name"]      = df["Product"].str.strip()
    out["category"]          = df["Category"].str.strip()
    out["date"]              = pd.to_datetime(df["Month"], errors="coerce")
    out["units_sold"]        = pd.to_numeric(df["Units_Sold"], errors="coerce")
    out["local_price"]       = pd.to_numeric(df["RRP"], errors="coerce")
    out["local_revenue"]     = pd.to_numeric(df["Revenue_AUD"], errors="coerce")
    out["current_inventory"] = pd.to_numeric(df["Stock_on_Hand"], errors="coerce")
    out["currency"]          = "AUD"
    out["region"]            = "Australia"
    return out

def standardise_europe(df: pd.DataFrame) -> pd.DataFrame:
    """Map EU columns → standard schema."""
    out = pd.DataFrame()
    out["sku"]               = df["Item_Number"].str.strip()
    out["product_name"]      = df["Item_Description"].str.strip()
    out["category"]          = df["Product_Group"].str.strip()
    out["date"]              = pd.to_datetime(df["Reporting_Period"],
                                              dayfirst=True, errors="coerce")
    out["units_sold"]        = pd.to_numeric(df["Qty_Sold"], errors="coerce")
    out["local_price"]       = pd.to_numeric(df["Price_EUR"], errors="coerce")
    out["local_revenue"]     = pd.to_numeric(df["Net_Sales_EUR"], errors="coerce")
    out["current_inventory"] = pd.to_numeric(df["Inventory_Units"], errors="coerce")
    out["currency"]          = "EUR"
    out["region"]            = "Europe"
    return out

def standardise_usa(df: pd.DataFrame) -> pd.DataFrame:
    """Map US columns → standard schema."""
    out = pd.DataFrame()
    out["sku"]               = df["product_id"].str.strip()
    out["product_name"]      = df["product_description"].str.strip()
    out["category"]          = df["product_category"].str.strip()
    out["date"]              = pd.to_datetime(df["period"], errors="coerce")
    out["units_sold"]        = pd.to_numeric(df["quantity"], errors="coerce")
    out["local_price"]       = pd.to_numeric(df["list_price_usd"], errors="coerce")
    out["local_revenue"]     = pd.to_numeric(df["net_revenue_usd"], errors="coerce")
    out["current_inventory"] = pd.to_numeric(df["on_hand_units"], errors="coerce")
    out["currency"]          = "USD"
    out["region"]            = "USA"
    return out

au_std = standardise_australia(au_raw)
eu_std = standardise_europe(eu_raw)
us_std = standardise_usa(us_raw)

print("   ✅ All 3 regions mapped to standard schema")


# ══════════════════════════════════════════════════════════════════
# STEP 3 — Combine into one dataset
# ══════════════════════════════════════════════════════════════════
print("\n🔗 STEP 3: Combining all regions...")
combined = pd.concat([au_std, eu_std, us_std], ignore_index=True)
rows_before_dedup = len(combined)
print(f"   Combined rows before cleaning: {rows_before_dedup}")


# ══════════════════════════════════════════════════════════════════
# STEP 4 — Remove duplicates
# ══════════════════════════════════════════════════════════════════
print("\n🔍 STEP 4: Removing duplicate rows...")
combined = combined.drop_duplicates(subset=["sku", "region", "date"])
rows_removed = rows_before_dedup - len(combined)
print(f"   Duplicates removed : {rows_removed}")
print(f"   Rows remaining     : {len(combined)}")


# ══════════════════════════════════════════════════════════════════
# STEP 5 — Fix category inconsistencies
# ══════════════════════════════════════════════════════════════════
print("\n🏷️  STEP 5: Fixing category inconsistencies...")

# Build a SKU → category lookup from the clean rows
sku_category_map = (
    combined[combined["category"].notna() &
             ~combined["category"].isin(["TBC", "UNKNOWN", ""])]
    .groupby("sku")["category"]
    .agg(lambda x: x.mode()[0] if len(x) > 0 else np.nan)
    .to_dict()
)

# Fix bad/missing categories using the lookup
bad_mask = combined["category"].isna() | combined["category"].isin(["TBC", "UNKNOWN", ""])
combined.loc[bad_mask, "category"] = combined.loc[bad_mask, "sku"].map(sku_category_map)

# Standardise capitalisation
combined["category"] = combined["category"].str.title().str.strip()

fixed_cats = bad_mask.sum()
print(f"   Categories fixed   : {fixed_cats}")
print(f"   Unique categories  : {sorted(combined['category'].dropna().unique())}")


# ══════════════════════════════════════════════════════════════════
# STEP 6 — Fill missing units_sold intelligently
# ══════════════════════════════════════════════════════════════════
print("\n📊 STEP 6: Filling missing units sold...")
missing_units_before = combined["units_sold"].isna().sum()

combined["month"] = combined["date"].dt.month

# Fill with median for same SKU + region + month (same seasonal period)
combined["units_sold"] = combined.groupby(
    ["sku", "region", "month"]
)["units_sold"].transform(lambda x: x.fillna(x.median()))

# Any still remaining → fill with SKU + region median
combined["units_sold"] = combined.groupby(
    ["sku", "region"]
)["units_sold"].transform(lambda x: x.fillna(x.median()))

combined["units_sold"] = combined["units_sold"].round(0).astype("Int64")
missing_units_after = combined["units_sold"].isna().sum()
print(f"   Missing units before: {missing_units_before}")
print(f"   Missing units after : {missing_units_after}")

# Fill missing inventory with region + SKU median
combined["current_inventory"] = combined.groupby(
    ["sku", "region"]
)["current_inventory"].transform(lambda x: x.fillna(x.median()))


# ══════════════════════════════════════════════════════════════════
# STEP 7 — Normalise revenue to USD for global comparisons
# ══════════════════════════════════════════════════════════════════
print("\n💱 STEP 7: Normalising revenue to USD...")
combined["fx_rate_to_usd"] = combined["currency"].map(FX_RATES)
combined["price_usd"]      = (combined["local_price"] * combined["fx_rate_to_usd"]).round(2)
combined["revenue_usd"]    = (combined["local_revenue"] * combined["fx_rate_to_usd"]).round(2)
print("   ✅ Revenue normalised — local currency retained for reference")


# ══════════════════════════════════════════════════════════════════
# STEP 8 — Add planning metrics
# ══════════════════════════════════════════════════════════════════
print("\n📐 STEP 8: Adding planning metrics...")

combined["year"]       = combined["date"].dt.year
combined["month_name"] = combined["date"].dt.strftime("%b")

combined["rolling_3m_avg"] = (
    combined.sort_values("date")
    .groupby(["sku", "region"])["units_sold"]
    .transform(lambda x: x.rolling(3, min_periods=1).mean().round(1))
)

combined["yoy_growth_pct"] = (
    combined.sort_values("date")
    .groupby(["sku", "region"])["units_sold"]
    .transform(lambda x: x.pct_change(12).mul(100).round(1))
)

# Inventory coverage = current stock ÷ 3-month avg monthly demand
combined["inventory_coverage_months"] = (
    combined["current_inventory"] / combined["rolling_3m_avg"].replace(0, np.nan)
).round(1)

def risk_flag(months):
    if pd.isna(months):  return "Unknown"
    elif months < 1:     return "Critical - Stockout Risk"
    elif months < 2:     return "High - Low Stock"
    elif months < 3:     return "Medium - Monitor"
    else:                return "Healthy"

combined["inventory_risk"] = combined["inventory_coverage_months"].apply(risk_flag)

# Convert Int64 → int for PostgreSQL compatibility
combined["units_sold"] = combined["units_sold"].astype(float).astype("int64")

print("   ✅ Rolling 3-month average, YoY growth, inventory coverage added")


# ══════════════════════════════════════════════════════════════════
# STEP 9 — Save to PostgreSQL
# ══════════════════════════════════════════════════════════════════
print("\n🗄️  STEP 9: Saving to PostgreSQL...")

# Columns to write — clean selection for the database
db_columns = [
    "region", "category", "sku", "product_name",
    "date", "year", "month", "month_name",
    "units_sold", "rolling_3m_avg", "yoy_growth_pct",
    "local_price", "currency", "fx_rate_to_usd", "price_usd",
    "local_revenue", "revenue_usd",
    "current_inventory", "inventory_coverage_months", "inventory_risk",
]

db_df = combined[db_columns].copy()

# Write main fact table — replace if it already exists
db_df.to_sql(
    name="sales_planning",
    con=engine,
    if_exists="replace",   # drop and recreate on each run
    index=False,
    method="multi",        # faster batch insert
    chunksize=500,
)
print(f"   ✅ Table 'sales_planning' written → {len(db_df):,} rows")

# Create supporting views in PostgreSQL
with engine.connect() as conn:

    conn.execute(text("DROP VIEW IF EXISTS monthly_summary"))
    conn.execute(text("""
        CREATE VIEW monthly_summary AS
        SELECT
            region,
            category,
            sku,
            product_name,
            year,
            month,
            month_name,
            SUM(units_sold)                    AS total_units,
            ROUND(SUM(revenue_usd)::numeric, 2) AS total_revenue_usd,
            ROUND(AVG(rolling_3m_avg)::numeric, 1) AS avg_3m_demand,
            ROUND(AVG(inventory_coverage_months)::numeric, 1) AS avg_coverage_months,
            MAX(inventory_risk)                AS inventory_risk,
            MAX(current_inventory)             AS current_inventory
        FROM sales_planning
        GROUP BY region, category, sku, product_name, year, month, month_name
    """))
    print("   ✅ View 'monthly_summary' created")

    conn.execute(text("DROP VIEW IF EXISTS inventory_risk_snapshot"))
    conn.execute(text("""
        CREATE VIEW inventory_risk_snapshot AS
        SELECT
            region,
            category,
            sku,
            product_name,
            current_inventory,
            ROUND(rolling_3m_avg::numeric, 1)           AS avg_monthly_demand,
            ROUND(inventory_coverage_months::numeric, 1) AS coverage_months,
            inventory_risk
        FROM sales_planning
        WHERE date = (SELECT MAX(date) FROM sales_planning)
        ORDER BY inventory_coverage_months ASC NULLS LAST
    """))
    print("   ✅ View 'inventory_risk_snapshot' created")

    conn.execute(text("DROP VIEW IF EXISTS regional_performance"))
    conn.execute(text("""
        CREATE VIEW regional_performance AS
        SELECT
            region,
            category,
            year,
            SUM(units_sold)                     AS total_units,
            ROUND(SUM(revenue_usd)::numeric, 0)  AS total_revenue_usd,
            COUNT(DISTINCT sku)                  AS active_skus
        FROM sales_planning
        GROUP BY region, category, year
        ORDER BY region, category, year
    """))
    print("   ✅ View 'regional_performance' created")

    conn.commit()

print(f"\n   Database summary:")
with engine.connect() as conn:
    row_count  = conn.execute(text("SELECT COUNT(*) FROM sales_planning")).scalar()
    sku_count  = conn.execute(text("SELECT COUNT(DISTINCT sku) FROM sales_planning")).scalar()
    date_range = conn.execute(text("SELECT MIN(date), MAX(date) FROM sales_planning")).fetchone()
    print(f"   {'Rows':<25} {row_count:,}")
    print(f"   {'Unique SKUs':<25} {sku_count}")
    print(f"   {'Date range':<25} {date_range[0]} → {date_range[1]}")


# ══════════════════════════════════════════════════════════════════
# STEP 10 — Export clean master Excel file
# ══════════════════════════════════════════════════════════════════
print("\n📤 STEP 10: Exporting clean master Excel file...")

EXCEL_PATH = f"{OUTPUT_DIR}/STS_Master_Planning_Data.xlsx"

clean_export = db_df.sort_values(["region", "sku", "date"])

with pd.ExcelWriter(EXCEL_PATH, engine="openpyxl") as writer:
    clean_export.to_excel(writer, sheet_name="All Regions", index=False)
    clean_export[clean_export["region"] == "Australia"].to_excel(
        writer, sheet_name="Australia", index=False)
    clean_export[clean_export["region"] == "Europe"].to_excel(
        writer, sheet_name="Europe", index=False)
    clean_export[clean_export["region"] == "USA"].to_excel(
        writer, sheet_name="USA", index=False)

    # Inventory risk tab — latest snapshot
    risk_summary = (
        combined[combined["date"] == combined["date"].max()]
        [[
            "region", "category", "sku", "product_name",
            "current_inventory", "rolling_3m_avg",
            "inventory_coverage_months", "inventory_risk"
        ]]
        .sort_values("inventory_coverage_months")
    )
    risk_summary.to_excel(writer, sheet_name="Inventory Risk", index=False)

print(f"   ✅ Excel exported → {EXCEL_PATH}")
print(f"   ✅ Sheets: All Regions | Australia | Europe | USA | Inventory Risk")


# ══════════════════════════════════════════════════════════════════
# FINAL AUDIT REPORT
# ══════════════════════════════════════════════════════════════════
print("\n" + "=" * 65)
print("  PIPELINE AUDIT REPORT")
print("=" * 65)

total_revenue = combined["revenue_usd"].sum()
total_units   = int(combined["units_sold"].sum())

print(f"\n  📅 Date range        : {combined['date'].min().date()} → {combined['date'].max().date()}")
print(f"  🌏 Regions           : {sorted(combined['region'].unique())}")
print(f"  📦 Unique SKUs       : {combined['sku'].nunique()}")
print(f"  🏷️  Categories        : {sorted(combined['category'].dropna().unique())}")
print(f"  📊 Total rows        : {len(combined):,}")
print(f"  📦 Total units sold  : {total_units:,}")
print(f"  💰 Total revenue     : ${total_revenue:,.0f} USD")

print(f"\n  Data Quality Summary:")
print(f"  {'Metric':<35} {'Before':>8}  {'After':>8}")
print(f"  {'-'*53}")
print(f"  {'Duplicate rows removed':<35} {rows_removed:>8}")
print(f"  {'Missing units filled':<35} {missing_units_before:>8}  {missing_units_after:>8}")
print(f"  {'Bad categories fixed':<35} {fixed_cats:>8}  {'0':>8}")
print(f"  {'Currencies normalised':<35} {'3':>8}  {'1 (USD)':>8}")

print(f"\n  Inventory Risk Distribution (latest snapshot):")
latest = combined[combined["date"] == combined["date"].max()]
for risk, count in latest["inventory_risk"].value_counts().items():
    pct = count / len(latest) * 100
    print(f"    {risk:<35} {count:>3} SKU-regions  ({pct:.0f}%)")

print(f"\n  PostgreSQL objects created:")
print(f"    Table : sales_planning")
print(f"    View  : monthly_summary")
print(f"    View  : inventory_risk_snapshot")
print(f"    View  : regional_performance")

print("\n" + "=" * 65)
print("  DAY 2 COMPLETE — PostgreSQL Planning Database Ready")
print("=" * 65)
print(f"""
  Connect to verify:
    psql -U {PG_CONFIG['user']} -d {PG_CONFIG['database']}

  Useful queries:
    SELECT COUNT(*) FROM sales_planning;
    SELECT * FROM inventory_risk_snapshot LIMIT 10;
    SELECT * FROM regional_performance;

  Excel file:
    {EXCEL_PATH}

  → Run day3_forecast.py next to build demand forecasts.
""")


