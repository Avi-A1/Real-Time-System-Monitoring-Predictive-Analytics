from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
from contextlib import asynccontextmanager
from system_monitor import get_system_stats
import asyncio
import sys
from pathlib import Path


# Find the project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Allow Python to find the database module
sys.path.append(str(PROJECT_ROOT / "database"))

from database import create_database, save_system_data, get_recent_data


COLLECTION_INTERVAL = 5


async def monitor_system():
    """Collect and save system data continuously."""

    while True:
        try:
            data = get_system_stats()
            save_system_data(data)

            print(f"System data saved: {data}")

        except Exception as error:
            print(f"Monitoring error: {error}")

        await asyncio.sleep(COLLECTION_INTERVAL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run tasks when the FastAPI application starts and stops."""

    create_database()

    monitoring_task = asyncio.create_task(monitor_system())

    print("System monitoring started.")

    yield

    monitoring_task.cancel()

    print("System monitoring stopped.")


app = FastAPI(
    title="Smart System Monitor API",
    description="Real-time system monitoring and predictive analytics",
    version="1.0.0",
    lifespan=lifespan
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {
        "message": "Smart System Monitor API is running"
    }


@app.get("/system")
def system_stats():
    """Return the current system statistics."""
    return get_system_stats()


@app.get("/history")
def system_history(limit: int = 100):
    """Return historical system statistics."""
    return get_recent_data(limit)