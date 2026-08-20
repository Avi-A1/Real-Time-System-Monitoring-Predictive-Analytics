import sqlite3
from pathlib import Path
from datetime import datetime


# Find the main project directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Database will be stored in the database folder
DATABASE_DIR = BASE_DIR / "database"
DATABASE_DIR.mkdir(exist_ok=True)

DATABASE_PATH = DATABASE_DIR / "system_monitor.db"


def get_connection():
    """Create and return a connection to the SQLite database."""
    return sqlite3.connect(DATABASE_PATH)


def create_database():
    """Create the system_metrics table if it doesn't exist."""

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS system_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            cpu REAL NOT NULL,
            memory REAL NOT NULL,
            disk REAL NOT NULL,
            network_sent INTEGER NOT NULL,
            network_received INTEGER NOT NULL,
            running_processes INTEGER NOT NULL
        )
    """)

    connection.commit()
    connection.close()


def save_system_data(data):
    """Save one system-monitoring reading to the database."""

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO system_metrics (
            timestamp,
            cpu,
            memory,
            disk,
            network_sent,
            network_received,
            running_processes
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.now().isoformat(),
        data["cpu"],
        data["memory"],
        data["disk"],
        data["network_sent"],
        data["network_received"],
        data["running_processes"]
    ))

    connection.commit()
    connection.close()


def get_recent_data(limit=100):
    """Get the most recent system readings."""

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT *
        FROM system_metrics
        ORDER BY id DESC
        LIMIT ?
    """, (limit,))

    rows = cursor.fetchall()

    connection.close()

    return rows


if __name__ == "__main__":
    create_database()
    print("Database initialized successfully.")
    print(f"Database location: {DATABASE_PATH}")