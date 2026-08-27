import sqlite3
import pandas as pd
from pathlib import Path


# ==========================================
# 1. FIND DATABASE
# ==========================================

BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_PATH = BASE_DIR / "database" / "system_monitor.db"


# ==========================================
# 2. LOAD DATA
# ==========================================

connection = sqlite3.connect(DATABASE_PATH)

df = pd.read_sql_query(
    "SELECT * FROM system_metrics ORDER BY id",
    connection
)

connection.close()


print("\n==============================")
print("DATASET OVERVIEW")
print("==============================")

print("Total records:", len(df))
print("Total columns:", len(df.columns))

print("\nColumns:")
print(df.columns.tolist())


# ==========================================
# 3. DATA TYPES
# ==========================================

print("\n==============================")
print("DATA TYPES")
print("==============================")

print(df.dtypes)


# ==========================================
# 4. MISSING VALUES
# ==========================================

print("\n==============================")
print("MISSING VALUES")
print("==============================")

print(df.isnull().sum())


# ==========================================
# 5. DUPLICATE ROWS
# ==========================================

print("\n==============================")
print("DUPLICATES")
print("==============================")

print("Duplicate rows:", df.duplicated().sum())


# ==========================================
# 6. STATISTICAL SUMMARY
# ==========================================

print("\n==============================")
print("STATISTICAL SUMMARY")
print("==============================")

print(df.describe().round(2))


# ==========================================
# 7. UNIQUE VALUES
# ==========================================

print("\n==============================")
print("UNIQUE VALUES")
print("==============================")

for column in df.columns:
    print(column, ":", df[column].nunique())


# ==========================================
# 8. TIME INFORMATION
# ==========================================

print("\n==============================")
print("TIME ANALYSIS")
print("==============================")

df["timestamp"] = pd.to_datetime(df["timestamp"])

time_difference = df["timestamp"].diff().dt.total_seconds()

print("First timestamp:", df["timestamp"].min())
print("Last timestamp:", df["timestamp"].max())

print("Average interval:",
      round(time_difference.mean(), 2), "seconds")

print("Minimum interval:",
      round(time_difference.min(), 2), "seconds")

print("Maximum interval:",
      round(time_difference.max(), 2), "seconds")


# ==========================================
# 9. CORRELATION
# ==========================================

print("\n==============================")
print("CORRELATION MATRIX")
print("==============================")

numeric_columns = [
    "cpu",
    "memory",
    "disk",
    "network_sent",
    "network_received",
    "running_processes"
]

print(
    df[numeric_columns]
    .corr()
    .round(2)
)


# ==========================================
# 10. POTENTIAL EXTREME VALUES
# ==========================================

print("\n==============================")
print("EXTREME VALUES")
print("==============================")

for column in numeric_columns:

    print(f"\n{column}")

    print("Minimum:", df[column].min())
    print("Maximum:", df[column].max())
    print("Mean:", round(df[column].mean(), 2))
    print("Median:", round(df[column].median(), 2))


print("\n==============================")
print("ANALYSIS COMPLETE")
print("==============================")