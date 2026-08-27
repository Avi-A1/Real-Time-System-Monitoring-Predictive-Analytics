import sqlite3
import pandas as pd
from pathlib import Path
import joblib

from sklearn.ensemble import (
    ExtraTreesRegressor,
    RandomForestRegressor,
    GradientBoostingRegressor
)

from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


# ==========================================
# 1. DATABASE
# ==========================================

BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_PATH = BASE_DIR / "database" / "system_monitor.db"


# ==========================================
# 2. LOAD DATA
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
# 3. SORT BY TIME
# ==========================================

df["timestamp"] = pd.to_datetime(df["timestamp"])

df = df.sort_values("timestamp").reset_index(drop=True)


# ==========================================
# 4. HISTORICAL CPU FEATURES
# ==========================================

for i in range(1, 11):
    df[f"cpu_lag_{i}"] = df["cpu"].shift(i)


# ==========================================
# 5. HISTORICAL CPU STATISTICS
# ==========================================

past_cpu = df["cpu"].shift(1)

df["cpu_avg_3"] = past_cpu.rolling(3).mean()

df["cpu_avg_5"] = past_cpu.rolling(5).mean()

df["cpu_min_5"] = past_cpu.rolling(5).min()

df["cpu_max_5"] = past_cpu.rolling(5).max()

df["cpu_std_5"] = past_cpu.rolling(5).std()


# ==========================================
# 6. HISTORICAL CPU CHANGE
# ==========================================

df["cpu_change"] = (
    df["cpu"].shift(1)
    - df["cpu"].shift(2)
)


# ==========================================
# 7. PREVIOUS SYSTEM INFORMATION
# ==========================================

df["memory_lag_1"] = df["memory"].shift(1)

df["disk_lag_1"] = df["disk"].shift(1)

df["processes_lag_1"] = (
    df["running_processes"].shift(1)
)


# ==========================================
# 8. FUTURE TARGET
# ==========================================

# Predict the average CPU usage
# over the next 5 readings.
#
# Your readings are approximately 6 seconds apart.
# Therefore:
#
# 5 readings ≈ 30 seconds
#
# IMPORTANT:
# This target contains future values ONLY as the
# value we are trying to predict.
# None of these future values are used as features.

df["target_cpu"] = (
    df["cpu"]
    .rolling(5)
    .mean()
    .shift(-5)
)


# ==========================================
# 9. FEATURES
# ==========================================

features = []

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
# 10. REMOVE MISSING VALUES
# ==========================================

valid = X.notna().all(axis=1) & y.notna()

X = X.loc[valid].reset_index(drop=True)

y = y.loc[valid].reset_index(drop=True)


# ==========================================
# 11. TIME-BASED SPLIT
# ==========================================

split_index = int(len(X) * 0.8)

X_train = X.iloc[:split_index]

X_test = X.iloc[split_index:]

y_train = y.iloc[:split_index]

y_test = y.iloc[split_index:]


# ==========================================
# 12. MODELS
# ==========================================

models = {

    "Extra Trees": ExtraTreesRegressor(
        n_estimators=500,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1
    ),

    "Random Forest": RandomForestRegressor(
        n_estimators=500,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1
    ),

    "Gradient Boosting": GradientBoostingRegressor(
        n_estimators=300,
        learning_rate=0.03,
        max_depth=3,
        min_samples_leaf=3,
        random_state=42
    )
}


# ==========================================
# 13. MODEL COMPARISON
# ==========================================

results = []


print("\n======================================")
print("  30-SECOND CPU PREDICTION")
print("======================================")


for name, model in models.items():

    print("\nTraining:", name)

    model.fit(
        X_train,
        y_train
    )

    predictions = model.predict(
        X_test
    )

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

    results.append({
        "Model": name,
        "MAE": mae,
        "RMSE": rmse,
        "R2": r2
    })


# ==========================================
# 14. DISPLAY RESULTS
# ==========================================

results_df = pd.DataFrame(results)

results_df = results_df.sort_values(
    "MAE"
)


print("\n======================================")
print("       FINAL COMPARISON")
print("======================================")


print(
    results_df.to_string(
        index=False,
        formatters={
            "MAE": "{:.2f}".format,
            "RMSE": "{:.2f}".format,
            "R2": "{:.4f}".format
        }
    )
)


print("\nBest model:")

print(
    results_df.iloc[0]["Model"]
)


print(
    "Best MAE:",
    round(results_df.iloc[0]["MAE"], 2)
)


# ==========================================
# 15. SAMPLE PREDICTIONS
# ==========================================

best_model_name = results_df.iloc[0]["Model"]

best_model = models[best_model_name]

predictions = best_model.predict(X_test)


sample_results = pd.DataFrame({

    "Actual Future Avg CPU":
        y_test.values,

    "Predicted Future Avg CPU":
        predictions

})


sample_results["Absolute Error"] = abs(
    sample_results["Actual Future Avg CPU"]
    - sample_results["Predicted Future Avg CPU"]
)


print("\n======================================")
print("       SAMPLE PREDICTIONS")
print("======================================")


print(
    sample_results
    .head(20)
    .to_string(index=False)
)
# Save best model
model_path = BASE_DIR / "ai" / "cpu_prediction_model.pkl"

joblib.dump(
    best_model,
    model_path
)

print("\nBest model saved to:")
print(model_path)