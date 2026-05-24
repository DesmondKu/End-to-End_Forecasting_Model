"""
DAY 3 — Demand Forecasting with Facebook Prophet
=================================================
Builds a 6-month demand forecast for every SKU x Region combination.
Outputs a forecast CSV used by Day 5 dashboard.
"""

import pandas as pd
import numpy as np
import json
import os
import warnings
warnings.filterwarnings("ignore")

from prophet import Prophet

INPUT  = "planning_database/combined.parquet"
OUTPUT = "planning_database"

print("=" * 65)
print("  SEA TO SUMMIT — DEMAND FORECASTING (Prophet)")
print("  Day 3: 6-Month Forward Forecast per SKU x Region")
print("=" * 65)

df = pd.read_parquet(INPUT)
df["date"] = pd.to_datetime(df["date"])

combos   = df[["sku","region","product_name","category"]].drop_duplicates()
forecasts = []
actuals   = []

print(f"\n  Forecasting {len(combos)} SKU x Region combinations...\n")

for _, row in combos.iterrows():
    sku, region, pname, cat = row["sku"], row["region"], row["product_name"], row["category"]

    hist = (df[(df["sku"]==sku) & (df["region"]==region)]
            .sort_values("date")[["date","units_sold"]]
            .rename(columns={"date":"ds","units_sold":"y"}))

    hist["y"] = pd.to_numeric(hist["y"], errors="coerce").clip(lower=0)

    if len(hist) < 6:
        continue

    # Store actuals
    for _, r in hist.iterrows():
        actuals.append({
            "sku": sku, "region": region,
            "product_name": pname, "category": cat,
            "date": r["ds"].strftime("%Y-%m-%d"),
            "actual_units": int(r["y"]) if not pd.isna(r["y"]) else 0,
        })

    try:
        m = Prophet(
            yearly_seasonality=True,
            weekly_seasonality=False,
            daily_seasonality=False,
            seasonality_mode="multiplicative",
            interval_width=0.80,
        )
        m.fit(hist)

        future   = m.make_future_dataframe(periods=6, freq="MS")
        forecast = m.predict(future)

        # Only keep future periods
        last_date = hist["ds"].max()
        fcast = forecast[forecast["ds"] > last_date][
            ["ds","yhat","yhat_lower","yhat_upper"]
        ].copy()

        fcast["yhat"]       = fcast["yhat"].clip(lower=0).round(0).astype(int)
        fcast["yhat_lower"] = fcast["yhat_lower"].clip(lower=0).round(0).astype(int)
        fcast["yhat_upper"] = fcast["yhat_upper"].clip(lower=0).round(0).astype(int)

        for _, fr in fcast.iterrows():
            forecasts.append({
                "sku": sku, "region": region,
                "product_name": pname, "category": cat,
                "date": fr["ds"].strftime("%Y-%m-%d"),
                "forecast_units": int(fr["yhat"]),
                "forecast_low":   int(fr["yhat_lower"]),
                "forecast_high":  int(fr["yhat_upper"]),
            })

        print(f"  ✅ {region:<12} {sku}  → next 6m avg: {fcast['yhat'].mean():.0f} units/month")

    except Exception as e:
        print(f"  ⚠️  {region} {sku} skipped: {e}")

# ── Save outputs ───────────────────────────────────────────────────
fcast_df   = pd.DataFrame(forecasts)
actuals_df = pd.DataFrame(actuals)

fcast_df.to_csv(f"{OUTPUT}/forecasts.csv", index=False)
actuals_df.to_csv(f"{OUTPUT}/actuals.csv", index=False)

# Also save as JSON for Day 5 HTML embedding
fcast_df.to_json(f"{OUTPUT}/forecasts.json",   orient="records")
actuals_df.to_json(f"{OUTPUT}/actuals.json",    orient="records")

print(f"\n{'='*65}")
print(f"  DAY 3 COMPLETE")
print(f"{'='*65}")
print(f"  Forecast rows : {len(fcast_df):,}  ({fcast_df['sku'].nunique()} SKUs x 3 regions x 6 months)")
print(f"  Actuals rows  : {len(actuals_df):,}")
print(f"  Files saved   : planning_database/forecasts.csv")
print(f"                  planning_database/actuals.csv")
print(f"\n  → Run day4_inventory.py next.")
