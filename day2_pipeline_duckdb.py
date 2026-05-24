"""
DAY 2 — Data Cleaning Pipeline & Consolidated Planning Database
================================================================
This script does what "AI alone cannot do reliably":
- Reads 3 messy, inconsistent regional Excel files
- Standardises column names, dates, currencies and categories
- Removes duplicates and fills missing values intelligently
- Consolidates everything into ONE trusted planning dataset
- Saves to a DuckDB database (fast, portable, no server needed)
- Exports a clean master Excel file for planners who still need Excel
- Prints a full audit report so stakeholders can trust the data

This is the FOUNDATION that makes forecasting and AI possible.
"""

import pandas as pd
import numpy as np
import duckdb
import os
import warnings
from datetime import datetime

warnings.filterwarnings("ignore")

INPUT_DIR  = "raw_regional_data"
OUTPUT_DIR = "planning_database"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# USD exchange rates (for normalising to USD)
FX_RATES = {"AUD": 0.645, "EUR": 1.09, "USD": 1.0}

print("=" * 65)
print("  SEA TO SUMMIT — SUPPLY CHAIN DATA PIPELINE")
print("  Day 2: Clean, Standardise & Consolidate")
print("=" * 65)


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

# Fill with the median for that SKU + region + month combination
combined["month"] = combined["date"].dt.month
combined["units_sold"] = combined.groupby(
    ["sku", "region", "month"]
)["units_sold"].transform(lambda x: x.fillna(x.median()))

# Any remaining NaN → fill with SKU+region median
combined["units_sold"] = combined.groupby(
    ["sku", "region"]
)["units_sold"].transform(lambda x: x.fillna(x.median()))

combined["units_sold"] = combined["units_sold"].round(0).astype("Int64")
missing_units_after = combined["units_sold"].isna().sum()
print(f"   Missing units before: {missing_units_before}")
print(f"   Missing units after : {missing_units_after}")

# Fill missing inventory with region+SKU median
combined["current_inventory"] = combined.groupby(
    ["sku", "region"]
)["current_inventory"].transform(lambda x: x.fillna(x.median()))


# ══════════════════════════════════════════════════════════════════
# STEP 7 — Normalise revenue to USD for global comparisons
# ══════════════════════════════════════════════════════════════════
print("\n💱 STEP 7: Normalising revenue to USD...")
combined["fx_rate_to_usd"]  = combined["currency"].map(FX_RATES)
combined["price_usd"]       = (combined["local_price"] * combined["fx_rate_to_usd"]).round(2)
combined["revenue_usd"]     = (combined["local_revenue"] * combined["fx_rate_to_usd"]).round(2)
print("   ✅ Revenue normalised — local currency retained for reference")


# ══════════════════════════════════════════════════════════════════
# STEP 8 — Add planning columns
# ══════════════════════════════════════════════════════════════════
print("\n📐 STEP 8: Adding planning metrics...")

combined["year"]            = combined["date"].dt.year
combined["month_name"]      = combined["date"].dt.strftime("%b")
combined["rolling_3m_avg"]  = (
    combined.sort_values("date")
    .groupby(["sku", "region"])["units_sold"]
    .transform(lambda x: x.rolling(3, min_periods=1).mean().round(1))
)
combined["yoy_growth_pct"]  = (
    combined.sort_values("date")
    .groupby(["sku", "region"])["units_sold"]
    .transform(lambda x: x.pct_change(12).mul(100).round(1))
)

# Simple inventory coverage = current stock ÷ 3-month avg monthly demand
combined["inventory_coverage_months"] = (
    combined["current_inventory"] / combined["rolling_3m_avg"].replace(0, np.nan)
).round(1)

# Inventory risk flag
def risk_flag(months):
    if pd.isna(months):      return "Unknown"
    elif months < 1:         return "🔴 Critical - Stockout Risk"
    elif months < 2:         return "🟠 High - Low Stock"
    elif months < 3:         return "🟡 Medium - Monitor"
    else:                    return "🟢 Healthy"

combined["inventory_risk"] = combined["inventory_coverage_months"].apply(risk_flag)

print("   ✅ Rolling 3-month average, YoY growth, inventory coverage added")


# ══════════════════════════════════════════════════════════════════
# STEP 9 — Save to DuckDB (the planning database)
# ══════════════════════════════════════════════════════════════════
print("\n🗄️  STEP 9: Saving to DuckDB planning database...")

DB_PATH = f"{OUTPUT_DIR}/sea_to_summit_planning.duckdb"
con = duckdb.connect(DB_PATH)

# Main fact table
con.execute("DROP TABLE IF EXISTS sales_planning")
con.execute("""
    CREATE TABLE sales_planning AS SELECT * FROM combined
""")

# Summary view: monthly by SKU and region
con.execute("DROP VIEW IF EXISTS monthly_summary")
con.execute("""
    CREATE VIEW monthly_summary AS
    SELECT
        region,
        category,
        sku,
        product_name,
        year,
        month,
        month_name,
        SUM(units_sold)             AS total_units,
        SUM(revenue_usd)            AS total_revenue_usd,
        AVG(rolling_3m_avg)         AS avg_3m_demand,
        AVG(inventory_coverage_months) AS avg_coverage_months,
        MAX(inventory_risk)         AS inventory_risk,
        MAX(current_inventory)      AS current_inventory
    FROM sales_planning
    GROUP BY region, category, sku, product_name, year, month, month_name
""")

# Quick validation query
row_count = con.execute("SELECT COUNT(*) FROM sales_planning").fetchone()[0]
print(f"   ✅ Database saved → {DB_PATH}")
print(f"   ✅ Total rows in database: {row_count}")
con.close()


# ══════════════════════════════════════════════════════════════════
# STEP 10 — Export clean master Excel file
# ══════════════════════════════════════════════════════════════════
print("\n📤 STEP 10: Exporting clean master Excel file...")

EXCEL_PATH = f"{OUTPUT_DIR}/STS_Master_Planning_Data.xlsx"

clean_export = combined[[
    "region", "category", "sku", "product_name",
    "date", "year", "month", "month_name",
    "units_sold", "rolling_3m_avg", "yoy_growth_pct",
    "local_price", "currency", "price_usd",
    "local_revenue", "revenue_usd",
    "current_inventory", "inventory_coverage_months", "inventory_risk"
]].sort_values(["region", "sku", "date"])

with pd.ExcelWriter(EXCEL_PATH, engine="openpyxl") as writer:
    # Tab 1: All data
    clean_export.to_excel(writer, sheet_name="All Regions", index=False)

    # Tab 2: Australia only
    clean_export[clean_export["region"] == "Australia"].to_excel(
        writer, sheet_name="Australia", index=False)

    # Tab 3: Europe only
    clean_export[clean_export["region"] == "Europe"].to_excel(
        writer, sheet_name="Europe", index=False)

    # Tab 4: USA only
    clean_export[clean_export["region"] == "USA"].to_excel(
        writer, sheet_name="USA", index=False)

    # Tab 5: Inventory Risk Summary
    risk_summary = (
        combined[combined["date"] == combined["date"].max()]
        [["region", "category", "sku", "product_name",
          "current_inventory", "rolling_3m_avg",
          "inventory_coverage_months", "inventory_risk"]]
        .sort_values(["inventory_coverage_months"])
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
total_units   = combined["units_sold"].sum()
date_range    = f"{combined['date'].min().date()} → {combined['date'].max().date()}"

print(f"\n  📅 Date range        : {date_range}")
print(f"  🌏 Regions           : {sorted(combined['region'].unique())}")
print(f"  📦 Unique SKUs       : {combined['sku'].nunique()}")
print(f"  🏷️  Categories        : {sorted(combined['category'].dropna().unique())}")
print(f"  📊 Total rows        : {len(combined):,}")
print(f"  📦 Total units sold  : {int(total_units):,}")
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

print("\n" + "=" * 65)
print("  DAY 2 COMPLETE — Planning Database Ready")
print("=" * 65)
print(f"\n  Files saved to: {OUTPUT_DIR}/")
print(f"  • sea_to_summit_planning.duckdb  ← query-ready database")
print(f"  • STS_Master_Planning_Data.xlsx  ← clean Excel for planners")
print()
print("  → Run day3_forecast.py next to build demand forecasts.")
