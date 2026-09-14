import sqlite3
import pandas as pd
from pathlib import Path
import joblib

from sklearn.ensemble import (
    ExtraTreesRegressor,
    RandomForestRegressor,
    GradientBoostingRegressor
)

from sklearn.model_selection import TimeSeriesSplit, GridSearchCV

from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score
)


# ==========================================
# 1. DATABASE
# ==========================================

BASE_DIR = Path(__file__).resolve().parent.parent

DATABASE_PATH = (
    BASE_DIR / "database" / "system_monitor.db"
)


# ==========================================
# 2. LOAD DATA
# ==========================================

connection = sqlite3.connect(
    DATABASE_PATH
)

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

df = pd.read_sql_query(
    query,
    connection
)

connection.close()

print("\nTotal raw records:", len(df))


# ==========================================
# 3. SORT BY TIME
# ==========================================

df["timestamp"] = pd.to_datetime(
    df["timestamp"]
)

df = (
    df
    .sort_values("timestamp")
    .reset_index(drop=True)
)


# ==========================================
# 4. CPU LAG FEATURES
# ==========================================

for i in range(1, 11):

    df[f"cpu_lag_{i}"] = (
        df["cpu"].shift(i)
    )


# ==========================================
# 5. HISTORICAL CPU STATISTICS
# ==========================================

# IMPORTANT:
# Only previous readings are used here.

past_cpu = df["cpu"].shift(1)


df["cpu_avg_3"] = (
    past_cpu
    .rolling(3)
    .mean()
)

df["cpu_avg_5"] = (
    past_cpu
    .rolling(5)
    .mean()
)

df["cpu_min_5"] = (
    past_cpu
    .rolling(5)
    .min()
)

df["cpu_max_5"] = (
    past_cpu
    .rolling(5)
    .max()
)

df["cpu_std_5"] = (
    past_cpu
    .rolling(5)
    .std()
)


# ==========================================
# 6. CPU CHANGE
# ==========================================

df["cpu_change"] = (
    df["cpu"].shift(1)
    -
    df["cpu"].shift(2)
)


# ==========================================
# 7. PREVIOUS SYSTEM INFORMATION
# ==========================================

df["memory_lag_1"] = (
    df["memory"].shift(1)
)

df["disk_lag_1"] = (
    df["disk"].shift(1)
)

df["processes_lag_1"] = (
    df["running_processes"].shift(1)
)


# ==========================================
# 8. FUTURE TARGET
# ==========================================

# Predict the average CPU usage
# of the NEXT 5 readings.
#
# Current time = t
#
# Target:
# t+1, t+2, t+3, t+4, t+5
#
# Approximately 30 seconds ahead.

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

    features.append(
        f"cpu_lag_{i}"
    )


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


# ==========================================
# 10. CREATE DATASET
# ==========================================

X = df[features]

y = df["target_cpu"]


# ==========================================
# 11. REMOVE NaN VALUES
# ==========================================

valid = (
    X.notna().all(axis=1)
    &
    y.notna()
)


X = (
    X
    .loc[valid]
    .reset_index(drop=True)
)

y = (
    y
    .loc[valid]
    .reset_index(drop=True)
)


# ==========================================
# 12. TIME-BASED TRAIN/TEST SPLIT
# ==========================================

split_index = int(
    len(X) * 0.8
)


X_train = X.iloc[
    :split_index
]

X_test = X.iloc[
    split_index:
]


y_train = y.iloc[
    :split_index
]

y_test = y.iloc[
    split_index:
]


print("\n======================================")
print("        DATASET INFORMATION")
print("======================================")

print(
    "Usable records:",
    len(X)
)

print(
    "Training records:",
    len(X_train)
)

print(
    "Testing records:",
    len(X_test)
)


# ==========================================
# 13. BASELINE MODELS
# ==========================================

extra_trees = ExtraTreesRegressor(
    n_estimators=500,
    min_samples_leaf=2,
    random_state=42,
    n_jobs=-1
)


random_forest = RandomForestRegressor(
    n_estimators=500,
    min_samples_leaf=2,
    random_state=42,
    n_jobs=-1
)


# ==========================================
# 14. TRAIN BASELINE MODELS
# ==========================================

print("\n======================================")
print("       BASELINE MODELS")
print("======================================")


extra_trees.fit(
    X_train,
    y_train
)

extra_predictions = extra_trees.predict(
    X_test
)


random_forest.fit(
    X_train,
    y_train
)

rf_predictions = random_forest.predict(
    X_test
)


# ==========================================
# 15. GRADIENT BOOSTING TUNING
# ==========================================

print("\n======================================")
print("     TUNING GRADIENT BOOSTING")
print("======================================")


base_gb = GradientBoostingRegressor(
    random_state=42
)


# Time-series validation.
#
# This prevents future records from being
# used to predict earlier records during tuning.

time_split = TimeSeriesSplit(
    n_splits=4
)


parameter_grid = {

    "n_estimators": [
        100,
        200,
        300
    ],

    "learning_rate": [
        0.02,
        0.03,
        0.05
    ],

    "max_depth": [
        2,
        3,
        4
    ],

    "min_samples_leaf": [
        2,
        3,
        5
    ],

    "subsample": [
        0.8,
        1.0
    ]
}


grid_search = GridSearchCV(

    estimator=base_gb,

    param_grid=parameter_grid,

    scoring="neg_mean_absolute_error",

    cv=time_split,

    n_jobs=-1,

    verbose=1
)


grid_search.fit(
    X_train,
    y_train
)


best_gb = grid_search.best_estimator_


print("\nBest Gradient Boosting parameters:")

print(
    grid_search.best_params_
)


print(
    "\nBest cross-validation MAE:",
    round(
        -grid_search.best_score_,
        2
    )
)


# ==========================================
# 16. TEST ALL FINAL MODELS
# ==========================================

gb_predictions = best_gb.predict(
    X_test
)


# ==========================================
# 17. MODEL EVALUATION FUNCTION
# ==========================================

def evaluate_model(
    name,
    actual,
    predicted
):

    mae = mean_absolute_error(
        actual,
        predicted
    )

    rmse = mean_squared_error(
        actual,
        predicted
    ) ** 0.5

    r2 = r2_score(
        actual,
        predicted
    )

    return {

        "Model": name,

        "MAE": mae,

        "RMSE": rmse,

        "R2": r2
    }


# ==========================================
# 18. COLLECT RESULTS
# ==========================================

results = []


results.append(
    evaluate_model(
        "Tuned Gradient Boosting",
        y_test,
        gb_predictions
    )
)


results.append(
    evaluate_model(
        "Random Forest",
        y_test,
        rf_predictions
    )
)


results.append(
    evaluate_model(
        "Extra Trees",
        y_test,
        extra_predictions
    )
)


# ==========================================
# 19. NAIVE BASELINE
# ==========================================

# Predict future CPU average using
# the current CPU reading.

baseline_predictions = (
    df.loc[valid, "cpu"]
    .iloc[split_index:]
    .values
)


baseline_mae = mean_absolute_error(
    y_test,
    baseline_predictions
)


baseline_rmse = mean_squared_error(
    y_test,
    baseline_predictions
) ** 0.5


baseline_r2 = r2_score(
    y_test,
    baseline_predictions
)


# ==========================================
# 20. FINAL COMPARISON
# ==========================================

results_df = pd.DataFrame(
    results
)


results_df = (
    results_df
    .sort_values("MAE")
    .reset_index(drop=True)
)


print("\n======================================")
print("          FINAL COMPARISON")
print("======================================")


print(
    results_df.to_string(
        index=False,
        formatters={

            "MAE":
                "{:.2f}".format,

            "RMSE":
                "{:.2f}".format,

            "R2":
                "{:.4f}".format
        }
    )
)


print("\nNaive Baseline:")

print(
    "MAE:",
    round(baseline_mae, 2)
)

print(
    "RMSE:",
    round(baseline_rmse, 2)
)

print(
    "R2:",
    round(baseline_r2, 4)
)


# ==========================================
# 21. BEST MODEL
# ==========================================

best_model_name = (
    results_df.iloc[0]["Model"]
)


if best_model_name == "Tuned Gradient Boosting":

    best_model = best_gb

    final_predictions = gb_predictions


elif best_model_name == "Random Forest":

    best_model = random_forest

    final_predictions = rf_predictions


else:

    best_model = extra_trees

    final_predictions = extra_predictions


best_mae = (
    results_df.iloc[0]["MAE"]
)


print("\nBest model:")

print(
    best_model_name
)


print(
    "Best MAE:",
    round(best_mae, 2)
)


# ==========================================
# 22. IMPROVEMENT OVER BASELINE
# ==========================================

improvement = (
    (baseline_mae - best_mae)
    /
    baseline_mae
) * 100


print(
    "\nImprovement over naive baseline:",
    round(improvement, 2),
    "%"
)


# ==========================================
# 23. SAMPLE PREDICTIONS
# ==========================================

sample_results = pd.DataFrame({

    "Actual Future Avg CPU":
        y_test.values,

    "Predicted Future Avg CPU":
        final_predictions

})


sample_results[
    "Absolute Error"
] = abs(

    sample_results[
        "Actual Future Avg CPU"
    ]

    -

    sample_results[
        "Predicted Future Avg CPU"
    ]
)


print("\n======================================")
print("          SAMPLE PREDICTIONS")
print("======================================")


print(
    sample_results
    .head(20)
    .to_string(
        index=False
    )
)


# ==========================================
# 24. SAVE BEST MODEL
# ==========================================

model_path = (
    BASE_DIR
    / "ai"
    / "cpu_prediction_model.pkl"
)


joblib.dump(
    best_model,
    model_path
)


print("\nBest model saved to:")

print(model_path)


# ==========================================
# 25. SAVE FEATURE LIST
# ==========================================

feature_path = (
    BASE_DIR
    / "ai"
    / "cpu_features.pkl"
)


joblib.dump(
    features,
    feature_path
)


print("\nFeature list saved to:")

print(feature_path)


# ==========================================
# 26. SAVE MODEL METRICS
# ==========================================

metrics_path = (
    BASE_DIR
    / "ai"
    / "cpu_model_metrics.csv"
)


results_df.to_csv(
    metrics_path,
    index=False
)


print("\nModel metrics saved to:")

print(metrics_path)


# ==========================================
# 27. SAVE TUNING PARAMETERS
# ==========================================

params_path = (
    BASE_DIR
    / "ai"
    / "cpu_model_parameters.pkl"
)


joblib.dump(
    best_model.get_params(),
    params_path
)


print("\nModel parameters saved to:")

print(params_path)


# ==========================================
# 28. COMPLETE
# ==========================================

print("\n======================================")
print("      FINAL CPU MODEL COMPLETE")
print("======================================")