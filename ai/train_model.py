import sqlite3
import pandas as pd
from pathlib import Path

from sklearn.ensemble import ExtraTreesRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import joblib


# ==========================================
# 1. Find database
# ==========================================

BASE_DIR = Path(__file__).resolve().parent.parent

DATABASE_PATH = BASE_DIR / "database" / "system_monitor.db"


# ==========================================
# 2. Load data
# ==========================================

connection = sqlite3.connect(DATABASE_PATH)

query = """
SELECT timestamp,
       cpu,
       memory,
       disk,
       network_sent,
       network_received,
       running_processes
FROM system_metrics
ORDER BY id ASC
"""

df = pd.read_sql_query(query, connection)

connection.close()


print("\nTotal raw records:", len(df))


# ==========================================
# 3. Sort by time
# ==========================================

df["timestamp"] = pd.to_datetime(df["timestamp"])

df = df.sort_values("timestamp").reset_index(drop=True)


# ==========================================
# 4. Create past CPU features
# ==========================================

# Previous CPU readings
for i in range(1, 11):
    df[f"cpu_lag_{i}"] = df["cpu"].shift(i)


# ==========================================
# 5. Historical CPU statistics
# ==========================================

# IMPORTANT:
# shift(1) ensures the current CPU is NOT included

past_cpu = df["cpu"].shift(1)

df["cpu_avg_3"] = past_cpu.rolling(3).mean()

df["cpu_avg_5"] = past_cpu.rolling(5).mean()

df["cpu_min_5"] = past_cpu.rolling(5).min()

df["cpu_max_5"] = past_cpu.rolling(5).max()

df["cpu_std_5"] = past_cpu.rolling(5).std()


# ==========================================
# 6. Previous CPU change
# ==========================================

df["cpu_change"] = (
    df["cpu"].shift(1) - df["cpu"].shift(2)
)


# ==========================================
# 7. Previous system information
# ==========================================

df["memory_lag_1"] = df["memory"].shift(1)

df["disk_lag_1"] = df["disk"].shift(1)

df["processes_lag_1"] = (
    df["running_processes"].shift(1)
)


# ==========================================
# 8. Target = NEXT CPU
# ==========================================

df["target_cpu"] = df["cpu"].shift(-1)


# ==========================================
# 9. Remove missing rows
# ==========================================

df = df.dropna().reset_index(drop=True)


# ==========================================
# 10. Define features
# ==========================================

features = []

# Previous 10 CPU readings
for i in range(1, 11):
    features.append(f"cpu_lag_{i}")


features += [
    "cpu_avg_3",
    "cpu_avg_5",
    "cpu_min_5",
    "cpu_max_5",
    "cpu_std_5",
    "cpu_change",
    "memory_lag_1",
    "disk_lag_1",
    "processes_lag_1"
]


X = df[features]

y = df["target_cpu"]


# ==========================================
# 11. Time-based 80/20 split
# ==========================================

split_index = int(len(df) * 0.8)


X_train = X.iloc[:split_index]

X_test = X.iloc[split_index:]


y_train = y.iloc[:split_index]

y_test = y.iloc[split_index:]


# ==========================================
# 12. Create model
# ==========================================

model = ExtraTreesRegressor(
    n_estimators=500,
    max_depth=None,
    min_samples_leaf=2,
    max_features=1.0,
    random_state=42,
    n_jobs=-1
)


# ==========================================
# 13. Train model
# ==========================================

print("\nTraining CPU prediction model...")

model.fit(X_train, y_train)


# ==========================================
# 14. Predict
# ==========================================

predictions = model.predict(X_test)


# ==========================================
# 15. Evaluation
# ==========================================

mae = mean_absolute_error(
    y_test,
    predictions
)

rmse = mean_squared_error(
    y_test,
    predictions
) ** 0.5

r2 = r2_score(
    y_test,
    predictions
)


# ==========================================
# 16. Naive baseline
# ==========================================

# Baseline:
# Assume next CPU will be the current CPU

baseline_predictions = df["cpu"].iloc[
    split_index:
].values


baseline_mae = mean_absolute_error(
    y_test,
    baseline_predictions
)


# ==========================================
# 17. Display results
# ==========================================

print("\n======================================")
print("       CPU PREDICTION MODEL")
print("======================================")

print(
    "Total records:",
    len(df)
)

print(
    "Training records:",
    len(X_train)
)

print(
    "Testing records:",
    len(X_test)
)


print("\nMODEL PERFORMANCE")

print(
    "MAE:",
    round(mae, 2)
)

print(
    "RMSE:",
    round(rmse, 2)
)

print(
    "R2 Score:",
    round(r2, 4)
)


print("\nBASELINE PERFORMANCE")

print(
    "Naive Baseline MAE:",
    round(baseline_mae, 2)
)


# ==========================================
# 18. Actual vs Predicted
# ==========================================

results = pd.DataFrame({

    "Actual Next CPU": y_test.values,

    "Predicted Next CPU": predictions

})


results["Absolute Error"] = abs(
    results["Actual Next CPU"]
    - results["Predicted Next CPU"]
)


print("\n======================================")
print("       SAMPLE PREDICTIONS")
print("======================================")

print(
    results.head(20)
    .to_string(index=False)
)


# ==========================================
# 19. Save model
# ==========================================

model_path = BASE_DIR / "ai" / "cpu_prediction_model.pkl"

joblib.dump(
    model,
    model_path
)


# ==========================================
# 20. Save feature list
# ==========================================

feature_path = BASE_DIR / "ai" / "cpu_features.pkl"

joblib.dump(
    features,
    feature_path
)


print("\n======================================")

print("MODEL SAVED")

print(model_path)

print("\nFEATURE LIST SAVED")

print(feature_path)

print("\nCPU MODEL TRAINING COMPLETE")