# PostgreSQL Setup Guide
## Sea to Summit — Planning Database

Follow the steps for your operating system before running `day2_pipeline.py`.

---

## Step 1 — Install PostgreSQL

### Mac (recommended: Homebrew)
```bash
brew install postgresql@16
brew services start postgresql@16
```

### Windows
1. Download the installer from https://www.postgresql.org/download/windows/
2. Run the installer — accept all defaults
3. When asked, set a password for the `postgres` user — **remember this**
4. PostgreSQL will start automatically as a Windows service

### Linux (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib -y
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

---

## Step 2 — Create the Planning Database and User

### Mac / Linux
Open a terminal and run:
```bash
psql postgres
```

Then inside the psql prompt, run these commands:
```sql
-- Create a dedicated user for the planning pipeline
CREATE USER sts_planner WITH PASSWORD 'planning2024';

-- Create the database
CREATE DATABASE sts_planning OWNER sts_planner;

-- Grant all privileges
GRANT ALL PRIVILEGES ON DATABASE sts_planning TO sts_planner;

-- Exit
\q
```

### Windows
Open **pgAdmin 4** (installed with PostgreSQL) or use the **SQL Shell (psql)**:
```sql
CREATE USER sts_planner WITH PASSWORD 'planning2024';
CREATE DATABASE sts_planning OWNER sts_planner;
GRANT ALL PRIVILEGES ON DATABASE sts_planning TO sts_planner;
\q
```

---

## Step 3 — Install Python Libraries

```bash
pip install pandas numpy openpyxl psycopg2-binary sqlalchemy
```

---

## Step 4 — Configure Your Connection

Open `day2_pipeline.py` and update the connection settings at the top
if you used different values in Step 2:

```python
PG_CONFIG = {
    "host":     "localhost",
    "port":     5433,
    "database": "sts_planning",
    "user":     "sts_planner",
    "password": "planning2024",
}
```

---

## Step 5 — Run the Pipeline

```bash
python day1_generate_data.py    # only needed once
python day2_pipeline.py
```

---

## Step 6 — Verify the Database (Optional but Impressive in Demo)

Connect to the database and query it directly:

```bash
psql -U sts_planner -d sts_planning
```

Then run:
```sql
-- Check row count
SELECT COUNT(*) FROM sales_planning;

-- Check regions
SELECT region, COUNT(*) AS rows FROM sales_planning GROUP BY region;

-- See inventory risk summary
SELECT inventory_risk, COUNT(*) AS sku_regions
FROM sales_planning
WHERE date = (SELECT MAX(date) FROM sales_planning)
GROUP BY inventory_risk
ORDER BY inventory_risk;

-- Top 5 SKUs by revenue
SELECT sku, product_name, ROUND(SUM(revenue_usd)::numeric, 0) AS total_revenue_usd
FROM sales_planning
GROUP BY sku, product_name
ORDER BY total_revenue_usd DESC
LIMIT 5;

\q
```

---

## Troubleshooting

**"connection refused"**
→ PostgreSQL is not running. Start it:
- Mac: `brew services start postgresql@16`
- Linux: `sudo systemctl start postgresql`
- Windows: Open Services → find PostgreSQL → Start

**"password authentication failed"**
→ Double-check the password in PG_CONFIG matches what you set in Step 2.

**"psycopg2 not found"**
→ Run: `pip install psycopg2-binary`

**Mac: "psql: command not found"**
→ Add PostgreSQL to your PATH:
```bash
echo 'export PATH="/opt/homebrew/opt/postgresql@16/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```
