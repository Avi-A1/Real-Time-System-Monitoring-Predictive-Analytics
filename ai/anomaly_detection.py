import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path

from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import joblib


# ==========================================
# 1. DATABASE PATH
# ==========================================

BASE_DIR = Path(__file__).resolve().parent.parent

DATABASE_PATH = BASE_DIR / "database" / "system_monitor.db"

MODEL_PATH = BASE_DIR / "ai" / "anomaly_model.pkl"
SCALER_PATH = BASE_DIR / "ai" / "anomaly_scaler.pkl"


# ==========================================
# 2. LOAD DATA
# ==========================================

connection = sqlite3.connect(DATABASE_PATH)

df = pd.read_sql_query(
    "SELECT * FROM system_metrics ORDER BY id",
    connection
)

connection.close()

print("\nTotal records:", len(df))


# ==========================================
# 3. SORT DATA BY TIME
# ==========================================

df["timestamp"] = pd.to_datetime(df["timestamp"])

df = df.sort_values("timestamp").reset_index(drop=True)


# ==========================================
# 4. TIME INTERVAL
# ==========================================

df["time_diff"] = (
    df["timestamp"]
    .diff()
    .dt.total_seconds()
)


# ==========================================
# 5. CHANGE FEATURES
# ==========================================

df["cpu_change"] = df["cpu"].diff()

df["memory_change"] = df["memory"].diff()

df["process_change"] = (
    df["running_processes"].diff()
)


# Network counters are cumulative,
# therefore use their change.

df["network_sent_change"] = (
    df["network_sent"].diff()
)

df["network_received_change"] = (
    df["network_received"].diff()
)


# ==========================================
# 6. NETWORK RATE
# ==========================================

df["network_sent_rate"] = (
    df["network_sent_change"] /
    df["time_diff"]
)

df["network_received_rate"] = (
    df["network_received_change"] /
    df["time_diff"]
)


# ==========================================
# 7. ROLLING FEATURES
# ==========================================

df["cpu_rolling_mean"] = (
    df["cpu"]
    .rolling(window=5)
    .mean()
)

df["memory_rolling_mean"] = (
    df["memory"]
    .rolling(window=5)
    .mean()
)

df["cpu_rolling_std"] = (
    df["cpu"]
    .rolling(window=5)
    .std()
)

df["memory_rolling_std"] = (
    df["memory"]
    .rolling(window=5)
    .std()
)


# ==========================================
# 8. DEVIATION FROM RECENT BEHAVIOUR
# ==========================================

df["cpu_deviation"] = (
    df["cpu"] -
    df["cpu_rolling_mean"]
)

df["memory_deviation"] = (
    df["memory"] -
    df["memory_rolling_mean"]
)


# ==========================================
# 9. REMOVE INVALID VALUES
# ==========================================

df = df.replace(
    [np.inf, -np.inf],
    np.nan
)

df = df.dropna().reset_index(drop=True)


# ==========================================
# 10. SELECT FEATURES
# ==========================================

features = [
    "cpu",
    "memory",
    "running_processes",

    "cpu_change",
    "memory_change",
    "process_change",

    "network_sent_change",
    "network_received_change",

    "network_sent_rate",
    "network_received_rate",

    "cpu_deviation",
    "memory_deviation",

    "cpu_rolling_std",
    "memory_rolling_std"
]


X = df[features]


# ==========================================
# 11. SCALE FEATURES
# ==========================================

scaler = StandardScaler()

X_scaled = scaler.fit_transform(X)


# ==========================================
# 12. ISOLATION FOREST
# ==========================================

model = IsolationForest(
    n_estimators=500,
    max_samples="auto",

    # Explicit contamination
    contamination=0.05,

    # Reproducible results
    random_state=42,

    # Use all CPU cores
    n_jobs=-1
)


model.fit(X_scaled)


# ==========================================
# 13. PREDICT ANOMALIES
# ==========================================

df["anomaly_prediction"] = (
    model.predict(X_scaled)
)

df["anomaly_score"] = (
    model.decision_function(X_scaled)
)


# Isolation Forest:
#  1  = Normal
# -1  = Anomaly

df["status"] = (
    df["anomaly_prediction"]
    .map({
        1: "Normal",
        -1: "Anomaly"
    })
)


# ==========================================
# 14. COUNT RESULTS
# ==========================================

normal_count = (
    df["anomaly_prediction"] == 1
).sum()

anomaly_count = (
    df["anomaly_prediction"] == -1
).sum()


anomaly_percentage = (
    anomaly_count / len(df)
) * 100


# ==========================================
# 15. DISPLAY RESULTS
# ==========================================

print("\n==============================")
print("ANOMALY DETECTION RESULTS")
print("==============================")

print("Records analysed:", len(df))

print("Normal records:", normal_count)

print("Anomaly records:", anomaly_count)

print(
    "Anomaly percentage:",
    round(anomaly_percentage, 2),
    "%"
)


# ==========================================
# 16. DISPLAY DETECTED ANOMALIES
# ==========================================

print("\nDetected Anomalies:")

anomalies = df[
    df["anomaly_prediction"] == -1
]


columns_to_show = [
    "timestamp",
    "cpu",
    "memory",
    "running_processes",
    "cpu_change",
    "memory_change",
    "process_change",
    "anomaly_score",
    "status"
]


print(
    anomalies[columns_to_show]
    .head(20)
    .to_string(index=False)
)


# ==========================================
# 17. SAVE MODEL
# ==========================================

joblib.dump(
    model,
    MODEL_PATH
)

joblib.dump(
    scaler,
    SCALER_PATH
)


# ==========================================
# 18. SAVE RESULTS
# ==========================================

output_path = (
    BASE_DIR /
    "ai" /
    "anomaly_results.csv"
)

df.to_csv(
    output_path,
    index=False
)


# ==========================================
# 19. FINAL INFORMATION
# ==========================================

print("\n==============================")
print("MODEL INFORMATION")
print("==============================")

print("Anomaly contamination: 5%")

print("Model saved to:")
print(MODEL_PATH)

print("\nScaler saved to:")
print(SCALER_PATH)

print("\nResults saved to:")
print(output_path)

print("\n==============================")
print("ANALYSIS COMPLETE")
print("==============================")
# ==========================================
# 20. ANOMALY EXPLANATION
# ==========================================

def explain_anomaly(row):

    reasons = []
    severity_score = 0

    # ==========================================
    # CPU CONDITIONS
    # ==========================================

    if row["cpu"] >= 90:
        reasons.append(
            f"Critical CPU usage ({row['cpu']:.1f}%)"
        )
        severity_score += 4

    elif row["cpu"] >= 80:
        reasons.append(
            f"Very high CPU usage ({row['cpu']:.1f}%)"
        )
        severity_score += 3

    elif abs(row["cpu_change"]) >= 30:
        reasons.append(
            f"Large CPU change ({row['cpu_change']:.1f}%)"
        )
        severity_score += 3

    elif abs(row["cpu_change"]) >= 20:
        reasons.append(
            f"Significant CPU change ({row['cpu_change']:.1f}%)"
        )
        severity_score += 2


    # ==========================================
    # MEMORY CONDITIONS
    # ==========================================

    if row["memory"] >= 95:
        reasons.append(
            f"Critical memory usage ({row['memory']:.1f}%)"
        )
        severity_score += 4

    elif row["memory"] >= 90:
        reasons.append(
            f"High memory usage ({row['memory']:.1f}%)"
        )
        severity_score += 2

    if abs(row["memory_change"]) >= 10:
        reasons.append(
            f"Large memory change ({row['memory_change']:.1f}%)"
        )
        severity_score += 3

    elif abs(row["memory_change"]) >= 5:
        reasons.append(
            f"Significant memory change ({row['memory_change']:.1f}%)"
        )
        severity_score += 2


    # ==========================================
    # PROCESS CONDITIONS
    # ==========================================

    if abs(row["process_change"]) >= 20:
        reasons.append(
            f"Critical process-count change ({row['process_change']:.0f})"
        )
        severity_score += 4

    elif abs(row["process_change"]) >= 10:
        reasons.append(
            f"Large process-count change ({row['process_change']:.0f})"
        )
        severity_score += 3

    elif abs(row["process_change"]) >= 5:
        reasons.append(
            f"Process-count change ({row['process_change']:.0f})"
        )
        severity_score += 1


    # ==========================================
    # FALLBACK
    # ==========================================

    if not reasons:
        reasons.append(
            "Unusual combination of system metrics"
        )
        severity_score += 1


    # ==========================================
    # SEVERITY
    # ==========================================

    if severity_score >= 6:
        severity = "CRITICAL"

    elif severity_score >= 4:
        severity = "HIGH"

    elif severity_score >= 2:
        severity = "MEDIUM"

    else:
        severity = "LOW"


    return "; ".join(reasons), severity



explanation_results = df.apply(
    lambda row:
        explain_anomaly(row)
        if row["anomaly_prediction"] == -1
        else ("", ""),
    axis=1
)

df["anomaly_reason"] = explanation_results.apply(
    lambda x: x[0]
)

df["severity"] = explanation_results.apply(
    lambda x: x[1]
)


# ==========================================
# 21. DISPLAY EXPLANATIONS
# ==========================================

print("\n==============================")
print("ANOMALY EXPLANATIONS")
print("==============================")


explanation_columns = [
    "timestamp",
    "cpu",
    "memory",
    "running_processes",
    "anomaly_score",
    "anomaly_reason",
    "severity"
]


print(
    df[
        df["anomaly_prediction"] == -1
    ][explanation_columns]
    .head(20)
    .to_string(index=False)
)


# ==========================================
# 22. SAVE UPDATED RESULTS
# ==========================================

df.to_csv(
    output_path,
    index=False
)

print("\nUpdated anomaly results saved to:")
print(output_path)