import sqlite3
import pandas as pd
import numpy as np
import joblib
from pathlib import Path


# ==========================================
# 1. PROJECT PATHS
# ==========================================

BASE_DIR = Path(__file__).resolve().parent.parent

DATABASE_PATH = (
    BASE_DIR
    / "database"
    / "system_monitor.db"
)

MODEL_PATH = (
    BASE_DIR
    / "ai"
    / "anomaly_model.pkl"
)

SCALER_PATH = (
    BASE_DIR
    / "ai"
    / "anomaly_scaler.pkl"
)


# ==========================================
# 2. LOAD TRAINED MODEL
# ==========================================

model = joblib.load(MODEL_PATH)

scaler = joblib.load(SCALER_PATH)


# ==========================================
# 3. FEATURE LIST
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


# ==========================================
# 4. ANOMALY EXPLANATION
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
            f"Critical process-count change "
            f"({row['process_change']:.0f})"
        )

        severity_score += 4


    elif abs(row["process_change"]) >= 10:

        reasons.append(
            f"Large process-count change "
            f"({row['process_change']:.0f})"
        )

        severity_score += 3


    elif abs(row["process_change"]) >= 5:

        reasons.append(
            f"Process-count change "
            f"({row['process_change']:.0f})"
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


# ==========================================
# 5. LIVE ANOMALY PREDICTION
# ==========================================

def get_anomaly_prediction():

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
    ORDER BY id DESC
    LIMIT 10
    """


    df = pd.read_sql_query(
        query,
        connection
    )


    connection.close()


    # ==========================================
    # CHECK DATA
    # ==========================================

    if len(df) < 6:

        return {
            "status": "waiting",
            "message":
                "Not enough historical data for anomaly detection."
        }


    # ==========================================
    # SORT CHRONOLOGICALLY
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
    # TIME DIFFERENCE
    # ==========================================

    df["time_diff"] = (
        df["timestamp"]
        .diff()
        .dt.total_seconds()
    )


    # ==========================================
    # CHANGE FEATURES
    # ==========================================

    df["cpu_change"] = (
        df["cpu"].diff()
    )

    df["memory_change"] = (
        df["memory"].diff()
    )

    df["process_change"] = (
        df["running_processes"].diff()
    )


    # ==========================================
    # NETWORK CHANGES
    # ==========================================

    df["network_sent_change"] = (
        df["network_sent"].diff()
    )

    df["network_received_change"] = (
        df["network_received"].diff()
    )


    # ==========================================
    # NETWORK RATES
    # ==========================================

    df["network_sent_rate"] = (
        df["network_sent_change"]
        / df["time_diff"]
    )

    df["network_received_rate"] = (
        df["network_received_change"]
        / df["time_diff"]
    )


    # ==========================================
    # ROLLING FEATURES
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
    # DEVIATION
    # ==========================================

    df["cpu_deviation"] = (
        df["cpu"]
        - df["cpu_rolling_mean"]
    )

    df["memory_deviation"] = (
        df["memory"]
        - df["memory_rolling_mean"]
    )


    # ==========================================
    # REMOVE INVALID VALUES
    # ==========================================

    df = df.replace(
        [np.inf, -np.inf],
        np.nan
    )


    df = df.dropna().reset_index(
        drop=True
    )


    if len(df) == 0:

        return {
            "status": "waiting",
            "message":
                "Waiting for enough historical data."
        }


    # ==========================================
    # GET LATEST ROW
    # ==========================================

    latest = df.iloc[-1]


    # ==========================================
    # CREATE FEATURE MATRIX
    # ==========================================

    X_latest = pd.DataFrame(
        [
            [
                latest[feature]
                for feature in features
            ]
        ],
        columns=features
    )


    # ==========================================
    # SCALE FEATURES
    # ==========================================

    X_scaled = scaler.transform(
        X_latest
    )


    # ==========================================
    # PREDICT
    # ==========================================

    prediction = model.predict(
        X_scaled
    )[0]


    anomaly_score = model.decision_function(
        X_scaled
    )[0]


    # ==========================================
    # NORMAL
    # ==========================================

    if prediction == 1:

        return {

            "status": "success",

            "timestamp":
                latest["timestamp"].isoformat(),

            "anomaly": False,

            "status_label": "Normal",

            "severity": "NONE",

            "anomaly_score":
                round(float(anomaly_score), 6),

            "cpu":
                round(float(latest["cpu"]), 2),

            "memory":
                round(float(latest["memory"]), 2),

            "running_processes":
                int(latest["running_processes"]),

            "reason":
                "System metrics are within the learned normal pattern.",

            "model":
                "Isolation Forest"

        }


    # ==========================================
    # ANOMALY
    # ==========================================

    reason, severity = explain_anomaly(
        latest
    )


    return {

        "status": "success",

        "timestamp":
            latest["timestamp"].isoformat(),

        "anomaly": True,

        "status_label": "Anomaly",

        "severity":
            severity,

        "anomaly_score":
            round(float(anomaly_score), 6),

        "cpu":
            round(float(latest["cpu"]), 2),

        "memory":
            round(float(latest["memory"]), 2),

        "running_processes":
            int(latest["running_processes"]),

        "cpu_change":
            round(float(latest["cpu_change"]), 2),

        "memory_change":
            round(float(latest["memory_change"]), 2),

        "process_change":
            round(float(latest["process_change"]), 2),

        "reason":
            reason,

        "model":
            "Isolation Forest"

    }


# ==========================================
# 6. DIRECT TEST
# ==========================================

if __name__ == "__main__":

    result = get_anomaly_prediction()

    print("\n================================")
    print(" LIVE ANOMALY PREDICTION")
    print("================================")

    print(result)