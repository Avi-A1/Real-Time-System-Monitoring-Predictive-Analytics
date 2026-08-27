import sqlite3
import pandas as pd
from pathlib import Path
import matplotlib.pyplot as plt

BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_PATH = BASE_DIR / "database" / "system_monitor.db"
connection = sqlite3.connect(DATABASE_PATH)

query = "SELECT * FROM system_metrics ORDER BY id ASC"

df = pd.read_sql_query(query, connection)

connection.close()

print(df)


print("\nDataset shape:", df.shape)
print("\nColumn names:")
print(df.columns.tolist())
print("\n--- Dataset Information ---")
print(df.describe())

print("\n--- Missing Values ---")
print(df.isnull().sum())

plt.figure(figsize=(10, 5))
plt.plot(df["cpu"])
plt.title("CPU Usage Over Time")
plt.xlabel("Reading")
plt.ylabel("CPU Usage (%)")
plt.grid(True)
plt.show()