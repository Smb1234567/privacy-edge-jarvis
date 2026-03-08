import os
import psutil


def snapshot_system_metrics() -> dict:
    process = psutil.Process(os.getpid())
    mem_mb = process.memory_info().rss / (1024 * 1024)
    return {
        "process_rss_mb": round(mem_mb, 2),
        "cpu_percent": psutil.cpu_percent(interval=0.1),
        "ram_percent": psutil.virtual_memory().percent,
    }
