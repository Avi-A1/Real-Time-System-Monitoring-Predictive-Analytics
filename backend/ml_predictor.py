import sqlite3
import pandas as pd
import joblib
from pathlib import Path


# ==========================================
# 1. PROJECT PATHS
# ==========================================

BASE_DIR = Path(__file__).resolve().parent.parent

DATABASE_PATH = BASE_DIR / "database" / "system_monitor.db"

MODEL_PATH = BASE_DIR / "ai" / "cpu_prediction_model.pkl"

FEATURE_PATH = BASE_DIR / "ai" / "cpu_features.pkl"


# ==========================================
# 2. LOAD TRAINED MODEL
# ==========================================

model = joblib.load(MODEL_PATH)


# ==========================================
# 3. LOAD FEATURE LIST
# ==========================================

features = joblib.load(FEATURE_PATH)


# ==========================================
# 4. GET PREDICTION
# ==========================================

def get_prediction():

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
    ORDER BY id DESC
    LIMIT 20
    """

    df = pd.read_sql_query(
        query,
        connection
    )

    connection.close()


    # ==========================================
    # 5. CHECK HISTORICAL DATA
    # ==========================================

    if len(df) < 10:

        return {
            "status": "waiting",
            "message": "Not enough historical data for prediction."
        }


    # ==========================================
    # 6. RESTORE CHRONOLOGICAL ORDER
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
    # 7. CREATE CPU LAG FEATURES
    # ==========================================

    for i in range(1, 11):

        df[f"cpu_lag_{i}"] = (
            df["cpu"].shift(i)
        )


    # ==========================================
    # 8. HISTORICAL CPU STATISTICS
    # ==========================================

    # Use ONLY previous CPU readings.
    # This prevents the current CPU value from
    # leaking into historical statistics.

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
    # 9. CPU CHANGE
    # ==========================================

    df["cpu_change"] = (
        df["cpu"].shift(1)
        -
        df["cpu"].shift(2)
    )


    # ==========================================
    # 10. PREVIOUS SYSTEM INFORMATION
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
    # 11. GET LATEST FEATURE ROW
    # ==========================================

    latest = df.iloc[-1]


    X_latest = pd.DataFrame(
        [[latest[feature] for feature in features]],
        columns=features
    )


    # ==========================================
    # 12. CHECK FOR MISSING FEATURES
    # ==========================================

    if X_latest.isna().any().any():

        return {
            "status": "waiting",
            "message": "Waiting for enough historical data."
        }


    # ==========================================
    # 13. MAKE PREDICTION
    # ==========================================

    prediction = model.predict(
        X_latest
    )[0]


    # ==========================================
    # 14. RETURN RESULT
    # ==========================================

    return {

        "status": "success",

        "timestamp":
            latest["timestamp"].isoformat(),

        "current_cpu":
            round(float(latest["cpu"]), 2),

        "predicted_future_cpu":
            round(float(prediction), 2),

        "prediction_type":
            "Future CPU average",

        "model":
            "Gradient Boosting"
    }


# ==========================================
# 15. TEST DIRECTLY
# ==========================================

if __name__ == "__main__":

    result = get_prediction()

    print("\n==============================")
    print("       LIVE CPU PREDICTION")
    print("==============================")

    print(result)