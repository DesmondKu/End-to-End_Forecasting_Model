"""
DAY 1 — Generate Realistic Regional Planning Data
===================================================
This script simulates what Sea to Summit likely has today:
- 3 regional Excel files (Australia, Europe, USA)
- Each file is messy: different column names, missing values,
  inconsistent formats, duplicate rows — just like real life.

Run this script first. It creates the raw data that Day 2 will clean.
"""

import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta

# ── Settings ──────────────────────────────────────────────────────────────────
np.random.seed(42)
OUTPUT_DIR = "raw_regional_data"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── Product Catalogue (realistic outdoor gear SKUs) ────────────────────────────
SKUS = {
    "STS-SL-001": ("Sleeping Bag - Spark 0", "Sleeping Bags",   149.95),
    "STS-SL-002": ("Sleeping Bag - Spark III", "Sleeping Bags", 199.95),
    "STS-SL-003": ("Sleeping Bag - Trek", "Sleeping Bags",      249.95),
    "STS-PK-001": ("Pack - Altitude 60L", "Packs",             329.95),
    "STS-PK-002": ("Pack - Rapid 20L", "Packs",                179.95),
    "STS-PK-003": ("Pack - Rapid 30L", "Packs",                219.95),
    "STS-PK-004": ("Pack - Altitude 80L", "Packs",             399.95),
    "STS-TW-001": ("Towel - DryLite S", "Towels",               29.95),
    "STS-TW-002": ("Towel - DryLite L", "Towels",               49.95),
    "STS-TW-003": ("Towel - Tek Towel XL", "Towels",            69.95),
    "STS-AC-001": ("Accessory - Dry Bag 8L", "Accessories",     24.95),
    "STS-AC-002": ("Accessory - Dry Bag 20L", "Accessories",    34.95),
    "STS-AC-003": ("Accessory - Compression Sack", "Accessories",19.95),
    "STS-CP-001": ("Camp Kitchen - Folding Table", "Camp",      129.95),
    "STS-CP-002": ("Camp Kitchen - Utensil Set", "Camp",         39.95),
}

# ── Inventory levels per region ────────────────────────────────────────────────
INVENTORY = {
    "AU": {
        "STS-SL-001": 120, "STS-SL-002": 85,  "STS-SL-003": 60,
        "STS-PK-001": 45,  "STS-PK-002": 200, "STS-PK-003": 150,
        "STS-PK-004": 30,  "STS-TW-001": 400, "STS-TW-002": 300,
        "STS-TW-003": 180, "STS-AC-001": 500, "STS-AC-002": 350,
        "STS-AC-003": 420, "STS-CP-001": 55,  "STS-CP-002": 220,
    },
    "EU": {
        "STS-SL-001": 200, "STS-SL-002": 140, "STS-SL-003": 90,
        "STS-PK-001": 70,  "STS-PK-002": 310, "STS-PK-003": 240,
        "STS-PK-004": 50,  "STS-TW-001": 650, "STS-TW-002": 480,
        "STS-TW-003": 290, "STS-AC-001": 800, "STS-AC-002": 560,
        "STS-AC-003": 670, "STS-CP-001": 80,  "STS-CP-002": 350,
    },
    "US": {
        "STS-SL-001": 180, "STS-SL-002": 120, "STS-SL-003": 75,
        "STS-PK-001": 60,  "STS-PK-002": 270, "STS-PK-003": 200,
        "STS-PK-004": 40,  "STS-TW-001": 550, "STS-TW-002": 410,
        "STS-TW-003": 250, "STS-AC-001": 700, "STS-AC-002": 490,
        "STS-AC-003": 580, "STS-CP-001": 65,  "STS-CP-002": 290,
    },
}

# ── Seasonal demand multipliers (outdoor gear is very seasonal) ────────────────
# Months: Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec
AU_SEASONALITY = [0.6, 0.6, 0.8, 1.0, 1.3, 1.4, 1.4, 1.3, 1.1, 0.9, 0.7, 0.6]
EU_SEASONALITY = [0.5, 0.5, 0.7, 1.0, 1.4, 1.6, 1.7, 1.5, 1.1, 0.8, 0.5, 0.5]
US_SEASONALITY = [0.6, 0.6, 0.8, 1.1, 1.4, 1.5, 1.6, 1.4, 1.1, 0.9, 0.7, 0.7]

# Base monthly units sold per SKU (before seasonality)
BASE_DEMAND = {
    "STS-SL-001": 40,  "STS-SL-002": 30,  "STS-SL-003": 20,
    "STS-PK-001": 18,  "STS-PK-002": 75,  "STS-PK-003": 55,
    "STS-PK-004": 12,  "STS-TW-001": 150, "STS-TW-002": 110,
    "STS-TW-003": 65,  "STS-AC-001": 200, "STS-AC-002": 140,
    "STS-AC-003": 170, "STS-CP-001": 22,  "STS-CP-002": 90,
}

REGION_SCALE = {"AU": 0.7, "EU": 1.2, "US": 1.0}


def generate_sales_history(region: str, seasonality: list, messiness: float = 0.15):
    """Generate 2 years of monthly sales history with realistic noise."""
    rows = []
    start = datetime(2023, 1, 1)

    for sku, (name, category, price) in SKUS.items():
        for month_offset in range(24):
            date = start + timedelta(days=month_offset * 30)
            month_idx = date.month - 1

            base = BASE_DEMAND[sku] * REGION_SCALE[region]
            seasonal = base * seasonality[month_idx]
            noise = np.random.normal(1.0, messiness)
            units = max(0, int(seasonal * noise))
            revenue = round(units * price, 2)

            rows.append({
                "sku": sku,
                "product_name": name,
                "category": category,
                "unit_price": price,
                "date": date.strftime("%Y-%m-%d"),
                "units_sold": units,
                "revenue": revenue,
                "current_inventory": INVENTORY[region][sku],
                "region": region,
            })
    return rows


# ══════════════════════════════════════════════════════════════════════════════
# AUSTRALIA FILE — Reasonably clean but uses different column naming
# ══════════════════════════════════════════════════════════════════════════════
print("📦 Generating Australia data...")
au_rows = generate_sales_history("AU", AU_SEASONALITY)
au_df = pd.DataFrame(au_rows)

# Rename columns to simulate how AU team named things
au_df = au_df.rename(columns={
    "sku":               "SKU_Code",
    "product_name":      "Product",
    "category":          "Category",
    "unit_price":        "RRP",
    "date":              "Month",
    "units_sold":        "Units_Sold",
    "revenue":           "Revenue_AUD",
    "current_inventory": "Stock_on_Hand",
    "region":            "Region",
})

# Inject messiness: some missing values, a few duplicates
drop_idx = au_df.sample(frac=0.04).index
au_df.loc[drop_idx, "Units_Sold"] = np.nan
au_df.loc[au_df.sample(frac=0.02).index, "Category"] = np.nan
au_df = pd.concat([au_df, au_df.sample(8)], ignore_index=True)  # duplicate rows

au_df.to_excel(f"{OUTPUT_DIR}/Australia_Sales_Planning.xlsx", index=False)
print(f"   ✅ {len(au_df)} rows → Australia_Sales_Planning.xlsx")


# ══════════════════════════════════════════════════════════════════════════════
# EUROPE FILE — Different column names, dates in DD/MM/YYYY, currency in EUR
# ══════════════════════════════════════════════════════════════════════════════
print("📦 Generating Europe data...")
eu_rows = generate_sales_history("EU", EU_SEASONALITY)
eu_df = pd.DataFrame(eu_rows)

# Convert revenue to EUR
eu_df["revenue"] = (eu_df["revenue"] * 0.61).round(2)
eu_df["unit_price"] = (eu_df["unit_price"] * 0.61).round(2)

# Rename to simulate EU team's naming conventions (very different!)
eu_df = eu_df.rename(columns={
    "sku":               "Item_Number",
    "product_name":      "Item_Description",
    "category":          "Product_Group",
    "unit_price":        "Price_EUR",
    "date":              "Reporting_Period",
    "units_sold":        "Qty_Sold",
    "revenue":           "Net_Sales_EUR",
    "current_inventory": "Inventory_Units",
    "region":            "Market",
})

# EU uses DD/MM/YYYY date format
eu_df["Reporting_Period"] = pd.to_datetime(eu_df["Reporting_Period"]).dt.strftime("%d/%m/%Y")

# Inject messiness: more missing data, some text errors in product group
eu_df.loc[eu_df.sample(frac=0.06).index, "Qty_Sold"] = np.nan
eu_df.loc[eu_df.sample(frac=0.03).index, "Product_Group"] = "TBC"
eu_df.loc[eu_df.sample(frac=0.02).index, "Inventory_Units"] = np.nan
eu_df = pd.concat([eu_df, eu_df.sample(12)], ignore_index=True)

eu_df.to_excel(f"{OUTPUT_DIR}/Europe_Demand_Report.xlsx", index=False)
print(f"   ✅ {len(eu_df)} rows → Europe_Demand_Report.xlsx")


# ══════════════════════════════════════════════════════════════════════════════
# USA FILE — Yet another naming convention, revenue split into columns
# ══════════════════════════════════════════════════════════════════════════════
print("📦 Generating USA data...")
us_rows = generate_sales_history("US", US_SEASONALITY)
us_df = pd.DataFrame(us_rows)

# Rename to simulate US team's own style
us_df = us_df.rename(columns={
    "sku":               "product_id",
    "product_name":      "product_description",
    "category":          "product_category",
    "unit_price":        "list_price_usd",
    "date":              "period",
    "units_sold":        "quantity",
    "revenue":           "gross_revenue_usd",
    "current_inventory": "on_hand_units",
    "region":            "territory",
})

# US team also added a 'discount_pct' column and split out net revenue
us_df["discount_pct"] = np.random.choice([0, 5, 10, 15], size=len(us_df), p=[0.6, 0.2, 0.15, 0.05])
us_df["net_revenue_usd"] = (us_df["gross_revenue_usd"] * (1 - us_df["discount_pct"] / 100)).round(2)

# Inject messiness: mixed case in category, missing quantities
us_df.loc[us_df.sample(frac=0.05).index, "quantity"] = np.nan
us_df.loc[us_df.sample(frac=0.02).index, "product_category"] = us_df["product_category"].str.lower()
us_df.loc[us_df.sample(frac=0.01).index, "product_category"] = "UNKNOWN"
us_df = pd.concat([us_df, us_df.sample(10)], ignore_index=True)

us_df.to_excel(f"{OUTPUT_DIR}/USA_Sales_Data.xlsx", index=False)
print(f"   ✅ {len(us_df)} rows → USA_Sales_Data.xlsx")


# ══════════════════════════════════════════════════════════════════════════════
# Summary
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("DAY 1 COMPLETE — Raw Regional Files Generated")
print("="*60)
print(f"📁 Output folder : {OUTPUT_DIR}/")
print(f"📄 Files created :")
print(f"   • Australia_Sales_Planning.xlsx  ({len(au_df)} rows)")
print(f"   • Europe_Demand_Report.xlsx      ({len(eu_df)} rows)")
print(f"   • USA_Sales_Data.xlsx            ({len(us_df)} rows)")
print()
print("Problems deliberately injected (like real data):")
print("   ✗ Different column names across all 3 files")
print("   ✗ Different date formats (YYYY-MM-DD vs DD/MM/YYYY)")
print("   ✗ Different currencies (AUD, EUR, USD)")
print("   ✗ Missing values in units sold, category, inventory")
print("   ✗ Duplicate rows in each file")
print("   ✗ Inconsistent category naming (TBC, UNKNOWN, mixed case)")
print()
print("→ Run day2_pipeline.py next to clean and consolidate everything.")
