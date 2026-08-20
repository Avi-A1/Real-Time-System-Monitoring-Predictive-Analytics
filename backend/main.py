from fastapi import FastAPI
from system_monitor import get_system_stats

app = FastAPI(
    title="Smart System Monitor API",
    description="Backend API for real-time system monitoring and predictive analytics",
    version="1.0.0"
)


@app.get("/")
def home():
    return {
        "message": "Smart System Monitor API is running"
    }


@app.get("/system")
def system_stats():
    return get_system_stats()