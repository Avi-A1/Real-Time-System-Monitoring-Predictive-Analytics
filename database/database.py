import sqlite3
from pathlib import Path
from datetime import datetime, timezone


# =====================================================
# DATABASE PATH
# =====================================================

BASE_DIR = Path(__file__).resolve().parent.parent

DATABASE_DIR = BASE_DIR / "database"
DATABASE_DIR.mkdir(exist_ok=True)

DATABASE_PATH = DATABASE_DIR / "system_monitor.db"


# =====================================================
# CONNECTION
# =====================================================

def get_connection():
    """Create database connection."""
    connection = sqlite3.connect(
        DATABASE_PATH,
        timeout=10
    )

    connection.execute(
        "PRAGMA foreign_keys = ON"
    )

    return connection


# =====================================================
# CREATE DATABASE
# =====================================================

def create_database():
    """Create database tables and indexes."""

    connection = get_connection()
    cursor = connection.cursor()

    # Main monitoring table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS system_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            cpu REAL NOT NULL,
            memory REAL NOT NULL,
            disk REAL NOT NULL,
            network_sent INTEGER NOT NULL,
            network_received INTEGER NOT NULL,
            running_processes INTEGER NOT NULL,

            network_upload_speed REAL DEFAULT 0,
            network_download_speed REAL DEFAULT 0,
            operating_system TEXT DEFAULT 'Unknown',
            processor TEXT DEFAULT 'Unknown',
            ram TEXT DEFAULT 'Unknown'
        )
    """)

    # Alert table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS system_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            metric TEXT NOT NULL,
            value REAL NOT NULL,
            threshold REAL NOT NULL,
            severity TEXT NOT NULL,
            message TEXT NOT NULL,
            status TEXT DEFAULT 'ACTIVE',
            resolved_at TEXT
        )
    """)

    # Monitoring sessions
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS monitoring_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            start_time TEXT NOT NULL,
            end_time TEXT,
            status TEXT DEFAULT 'ACTIVE',
            total_records INTEGER DEFAULT 0
        )
    """)

    # Indexes for faster queries
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS
        idx_metrics_timestamp
        ON system_metrics(timestamp)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS
        idx_alerts_status
        ON system_alerts(status)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS
        idx_alerts_timestamp
        ON system_alerts(timestamp)
    """)

    # -------------------------------------------------
    # Compatibility with OLD database
    # -------------------------------------------------

    columns = {
        row[1]
        for row in cursor.execute(
            "PRAGMA table_info(system_metrics)"
        ).fetchall()
    }

    extra_columns = {
        "network_upload_speed":
            "REAL DEFAULT 0",

        "network_download_speed":
            "REAL DEFAULT 0",

        "operating_system":
            "TEXT DEFAULT 'Unknown'",

        "processor":
            "TEXT DEFAULT 'Unknown'",

        "ram":
            "TEXT DEFAULT 'Unknown'"
    }

    for name, data_type in extra_columns.items():

        if name not in columns:
            cursor.execute(
                f"""
                ALTER TABLE system_metrics
                ADD COLUMN {name} {data_type}
                """
            )

    connection.commit()
    connection.close()


# =====================================================
# VALIDATE DATA
# =====================================================

def validate_system_data(data):
    """Validate monitoring data."""

    required = [
        "cpu",
        "memory",
        "disk",
        "network_sent",
        "network_received",
        "running_processes"
    ]

    for field in required:
        if field not in data:
            raise ValueError(
                f"Missing field: {field}"
            )

    if not 0 <= float(data["cpu"]) <= 100:
        raise ValueError("Invalid CPU value")

    if not 0 <= float(data["memory"]) <= 100:
        raise ValueError("Invalid memory value")

    if not 0 <= float(data["disk"]) <= 100:
        raise ValueError("Invalid disk value")

    if float(data["network_sent"]) < 0:
        raise ValueError(
            "Network sent cannot be negative"
        )

    if float(data["network_received"]) < 0:
        raise ValueError(
            "Network received cannot be negative"
        )

    if int(data["running_processes"]) < 0:
        raise ValueError(
            "Process count cannot be negative"
        )


# =====================================================
# SAVE SYSTEM DATA
# =====================================================

def save_system_data(data):
    """Save one monitoring record."""

    validate_system_data(data)

    connection = get_connection()
    cursor = connection.cursor()

    timestamp = datetime.now(
        timezone.utc
    ).isoformat()

    cursor.execute("""
        INSERT INTO system_metrics (
            timestamp,
            cpu,
            memory,
            disk,
            network_sent,
            network_received,
            running_processes,
            network_upload_speed,
            network_download_speed,
            operating_system,
            processor,
            ram
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        timestamp,
        data["cpu"],
        data["memory"],
        data["disk"],
        data["network_sent"],
        data["network_received"],
        data["running_processes"],

        data.get(
            "network_upload_speed",
            0
        ),

        data.get(
            "network_download_speed",
            0
        ),

        data.get(
            "operating_system",
            "Unknown"
        ),

        data.get(
            "processor",
            "Unknown"
        ),

        data.get(
            "ram",
            "Unknown"
        )
    ))

    # Update active monitoring session
    cursor.execute("""
        UPDATE monitoring_sessions
        SET total_records =
            total_records + 1
        WHERE status = 'ACTIVE'
    """)

    connection.commit()
    connection.close()


# =====================================================
# GET RECENT DATA
# =====================================================

def get_recent_data(limit=100):
    """Return latest monitoring records."""

    try:
        limit = int(limit)
    except (TypeError, ValueError):
        limit = 100

    limit = max(
        1,
        min(limit, 1000)
    )

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


# =====================================================
# SYSTEM STATISTICS
# =====================================================

def get_system_statistics():
    """Return overall monitoring statistics."""

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            COUNT(*),
            AVG(cpu),
            MIN(cpu),
            MAX(cpu),
            AVG(memory),
            MIN(memory),
            MAX(memory),
            AVG(disk),
            MIN(disk),
            MAX(disk),
            MAX(running_processes)
        FROM system_metrics
    """)

    row = cursor.fetchone()

    connection.close()

    return {
        "total_records": row[0],

        "cpu": {
            "average": row[1],
            "minimum": row[2],
            "maximum": row[3]
        },

        "memory": {
            "average": row[4],
            "minimum": row[5],
            "maximum": row[6]
        },

        "disk": {
            "average": row[7],
            "minimum": row[8],
            "maximum": row[9]
        },

        "max_running_processes": row[10]
    }


# =====================================================
# TIME RANGE DATA
# =====================================================

def get_data_by_time_range(
    start_time,
    end_time
):
    """Get monitoring data for a time range."""

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT *
        FROM system_metrics
        WHERE timestamp BETWEEN ? AND ?
        ORDER BY timestamp ASC
    """, (
        start_time,
        end_time
    ))

    rows = cursor.fetchall()

    connection.close()

    return rows


# =====================================================
# ALERTS
# =====================================================

def create_alert(
    metric,
    value,
    threshold,
    severity,
    message
):
    """Create a system alert."""

    connection = get_connection()
    cursor = connection.cursor()

    timestamp = datetime.now(
        timezone.utc
    ).isoformat()

    cursor.execute("""
        INSERT INTO system_alerts (
            timestamp,
            metric,
            value,
            threshold,
            severity,
            message
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        timestamp,
        metric,
        value,
        threshold,
        severity,
        message
    ))

    connection.commit()

    alert_id = cursor.lastrowid

    connection.close()

    return alert_id


def get_active_alerts():
    """Return active alerts."""

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT *
        FROM system_alerts
        WHERE status = 'ACTIVE'
        ORDER BY id DESC
    """)

    rows = cursor.fetchall()

    connection.close()

    return rows


def resolve_alert(alert_id):
    """Mark an alert as resolved."""

    connection = get_connection()
    cursor = connection.cursor()

    resolved_at = datetime.now(
        timezone.utc
    ).isoformat()

    cursor.execute("""
        UPDATE system_alerts
        SET status = 'RESOLVED',
            resolved_at = ?
        WHERE id = ?
    """, (
        resolved_at,
        alert_id
    ))

    connection.commit()
    connection.close()


# =====================================================
# DATABASE HEALTH
# =====================================================

def database_health_check():
    """Check database connection."""

    try:
        connection = get_connection()

        connection.execute(
            "SELECT 1"
        )

        connection.close()

        return {
            "status": "healthy",
            "database": str(DATABASE_PATH)
        }

    except Exception as error:

        return {
            "status": "error",
            "message": str(error)
        }


# =====================================================
# DELETE OLD DATA
# =====================================================

def delete_old_data(days=30):
    """Delete records older than given days."""

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        DELETE FROM system_metrics
        WHERE timestamp <
        datetime('now', ?)
    """, (
        f"-{int(days)} days",
    ))

    deleted = cursor.rowcount

    connection.commit()
    connection.close()

    return deleted


# =====================================================
# MONITORING SESSION
# =====================================================

def start_monitoring_session():

    connection = get_connection()
    cursor = connection.cursor()

    start_time = datetime.now(
        timezone.utc
    ).isoformat()

    cursor.execute("""
        UPDATE monitoring_sessions
        SET status = 'STOPPED',
            end_time = ?
        WHERE status = 'ACTIVE'
    """, (
        start_time,
    ))

    cursor.execute("""
        INSERT INTO monitoring_sessions (
            start_time,
            status
        )
        VALUES (?, 'ACTIVE')
    """, (
        start_time,
    ))

    connection.commit()

    session_id = cursor.lastrowid

    connection.close()

    return session_id


def stop_monitoring_session():

    connection = get_connection()
    cursor = connection.cursor()

    end_time = datetime.now(
        timezone.utc
    ).isoformat()

    cursor.execute("""
        UPDATE monitoring_sessions
        SET status = 'STOPPED',
            end_time = ?
        WHERE status = 'ACTIVE'
    """, (
        end_time,
    ))

    connection.commit()
    connection.close()


# =====================================================
# TEST
# =====================================================

if __name__ == "__main__":

    create_database()

    print(
        "Database initialized successfully."
    )

    print(
        f"Database: {DATABASE_PATH}"
    )

    print(
        "Health:",
        database_health_check()
    )
