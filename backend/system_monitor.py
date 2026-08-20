import psutil


def get_system_stats():
    # CPU usage
    cpu = psutil.cpu_percent(interval=1)

    # Memory usage
    memory = psutil.virtual_memory()

    # Disk usage
    disk = psutil.disk_usage('/')

    # Network statistics
    network = psutil.net_io_counters()

    # Number of running processes
    processes = len(psutil.pids())

    return {
        "cpu": cpu,
        "memory": memory.percent,
        "disk": disk.percent,
        "network_sent": network.bytes_sent,
        "network_received": network.bytes_recv,
        "running_processes": processes
    }


if __name__ == "__main__":
    print(get_system_stats())