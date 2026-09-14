from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
from contextlib import asynccontextmanager

from backend.system_monitor import get_system_stats
from backend.ml_predictor import get_prediction
from backend.anomaly_predictor import get_anomaly_prediction

import asyncio
import sys
from pathlib import Path


# ==========================================
# 1. PROJECT PATHS
# ==========================================

PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parent
    .parent
)


# Allow Python to find database module
sys.path.append(
    str(PROJECT_ROOT / "database")
)


from database import (
    create_database,
    save_system_data,
    get_recent_data
)


# ==========================================
# 2. CONFIGURATION
# ==========================================

COLLECTION_INTERVAL = 5


# ==========================================
# 3. SYSTEM MONITORING
# ==========================================

async def monitor_system():
    """
    Collect and save system data continuously.
    """

    while True:

        try:

            data = get_system_stats()

            save_system_data(data)

            print(
                f"System data saved: {data}"
            )

        except Exception as error:

            print(
                f"Monitoring error: {error}"
            )

        await asyncio.sleep(
            COLLECTION_INTERVAL
        )


# ==========================================
# 4. FASTAPI LIFESPAN
# ==========================================

@asynccontextmanager
async def lifespan(app: FastAPI):

    """
    Run background monitoring when
    FastAPI starts.
    """

    create_database()

    monitoring_task = (
        asyncio.create_task(
            monitor_system()
        )
    )

    print(
        "System monitoring started."
    )

    yield

    monitoring_task.cancel()

    print(
        "System monitoring stopped."
    )


# ==========================================
# 5. FASTAPI APPLICATION
# ==========================================

app = FastAPI(

    title="Smart System Monitor API",

    description=(
        "Real-time system monitoring "
        "and predictive analytics"
    ),

    version="1.0.0",

    lifespan=lifespan
)


# ==========================================
# 6. CORS
# ==========================================

app.add_middleware(

    CORSMiddleware,

    allow_origins=["*"],

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"],
)


# ==========================================
# 7. HOME
# ==========================================

@app.get("/")
def home():

    return {

        "message":
            "Smart System Monitor API is running"

    }


# ==========================================
# 8. CURRENT SYSTEM
# ==========================================

@app.get("/system")
def system_stats():

    """
    Return current system statistics.
    """

    return get_system_stats()


# ==========================================
# 9. HISTORY
# ==========================================

@app.get("/history")
def system_history(
    limit: int = 100
):

    """
    Return historical system statistics.
    """

    return get_recent_data(limit)


# ==========================================
# 10. CPU PREDICTION
# ==========================================

@app.get("/prediction")
def cpu_prediction():

    """
    Return ML-based future CPU prediction.
    """

    try:

        return get_prediction()

    except Exception as error:

        return {

            "status": "error",

            "message":
                "CPU prediction failed.",

            "error":
                str(error)

        }


# ==========================================
# 11. ANOMALY DETECTION
# ==========================================

@app.get("/anomaly")
def anomaly_detection():

    """
    Return live anomaly detection result,
    anomaly score, explanation and severity.
    """

    try:

        return get_anomaly_prediction()

    except Exception as error:

        return {

            "status": "error",

            "message":
                "Anomaly detection failed.",

            "error":
                str(error)

        }