import psutil
import platform
import subprocess
import time


# =========================================================
# NETWORK SPEED TRACKING
# =========================================================

_previous_network = None
_previous_time = None


# =========================================================
# GET ACTUAL PROCESSOR NAME
# =========================================================

def get_processor_name():

    # Windows
    if platform.system() == "Windows":

        try:
            result = subprocess.check_output(
                [
                    "powershell",
                    "-Command",
                    "(Get-CimInstance Win32_Processor).Name"
                ],
                text=True,
                stderr=subprocess.DEVNULL
            )

            processor = result.strip()

            if processor:
                return processor

        except Exception:
            pass

    # Linux / macOS / fallback
    processor = platform.processor()

    if processor:
        return processor

    processor = platform.uname().processor

    if processor:
        return processor

    return "Unknown Processor"


# =========================================================
# GET OPERATING SYSTEM
# =========================================================

def get_operating_system():

    system = platform.system()

    # Windows
    if system == "Windows":

        try:

            version = platform.win32_ver()

            build_string = version[1]

            if build_string:

                build = int(
                    build_string.split(".")[-1]
                )

                if build >= 22000:
                    return "Windows 11"

                return "Windows 10"

        except Exception:
            pass

        return "Windows"

    # Linux
    if system == "Linux":
        return "Linux"

    # macOS
    if system == "Darwin":
        return "macOS"

    return system


# =========================================================
# GET NETWORK SPEED
# =========================================================

def get_network_speed():

    global _previous_network
    global _previous_time

    network = psutil.net_io_counters()

    current_time = time.time()

    upload_speed = 0.0
    download_speed = 0.0

    # We need two readings to calculate speed
    if (
        _previous_network is not None
        and _previous_time is not None
    ):

        time_difference = (
            current_time - _previous_time
        )

        if time_difference > 0:

            # Bytes per second
            upload_bytes_per_second = (
                network.bytes_sent
                - _previous_network.bytes_sent
            ) / time_difference

            download_bytes_per_second = (
                network.bytes_recv
                - _previous_network.bytes_recv
            ) / time_difference

            # Bytes/s -> MB/s
            upload_speed = (
                upload_bytes_per_second
                / (1024 * 1024)
            )

            download_speed = (
                download_bytes_per_second
                / (1024 * 1024)
            )

            # Prevent negative values
            upload_speed = max(
                0.0,
                upload_speed
            )

            download_speed = max(
                0.0,
                download_speed
            )

    # Save current reading
    _previous_network = network
    _previous_time = current_time

    return (
        upload_speed,
        download_speed
    )


# =========================================================
# GET SYSTEM STATISTICS
# =========================================================

def get_system_stats():

    # -----------------------------------------------------
    # CPU
    # -----------------------------------------------------

    cpu = psutil.cpu_percent(interval=0.1)


    # -----------------------------------------------------
    # MEMORY
    # -----------------------------------------------------

    memory = psutil.virtual_memory()


    # -----------------------------------------------------
    # DISK
    # -----------------------------------------------------

    disk = psutil.disk_usage('/')


    # -----------------------------------------------------
    # NETWORK
    # -----------------------------------------------------

    network = psutil.net_io_counters()

    upload_speed, download_speed = (
        get_network_speed()
    )


    # -----------------------------------------------------
    # RUNNING PROCESSES
    # -----------------------------------------------------

    processes = len(psutil.pids())


    # -----------------------------------------------------
    # HARDWARE INFORMATION
    # -----------------------------------------------------

    processor = get_processor_name()

    operating_system = get_operating_system()


    # -----------------------------------------------------
    # RAM
    # -----------------------------------------------------

    ram_gb = memory.total / (1024 ** 3)

    ram = f"{ram_gb:.1f} GB"


    # -----------------------------------------------------
    # RETURN DATA
    # -----------------------------------------------------

    return {

        # Existing monitoring values
        "cpu": cpu,

        "memory": memory.percent,

        "disk": disk.percent,

        "network_sent": network.bytes_sent,

        "network_received": network.bytes_recv,

        "running_processes": processes,


        # Network speed
        "network_upload_speed": round(
            upload_speed,
            2
        ),

        "network_download_speed": round(
            download_speed,
            2
        ),


        # Hardware information
        "operating_system": operating_system,

        "processor": processor,

        "ram": ram
    }


# =========================================================
# TEST
# =========================================================

if __name__ == "__main__":

    print(get_system_stats())