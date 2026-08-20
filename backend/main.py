from fastapi import FastAPI
from system_monitor import get_system_stats

import sys
from pathlib import Path

# Allow Python to find the database module
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT / "database"))

from database import create_database, save_system_data, get_recent_data


app = FastAPI(
    title="Smart System Monitor API",
    description="Real-time system monitoring and predictive analytics",
    version="1.0.0"
)


# Create the database when the application starts
create_database()


@app.get("/")
def home():
    return {
        "message": "Smart System Monitor API is running"
    }


@app.get("/system")
def system_stats():
    data = get_system_stats()

    # Save the current reading to the database
    save_system_data(data)

    return data


@app.get("/history")
def system_history(limit: int = 100):
    return get_recent_data(limit)