import os
import time

import psutil


def lower_priority():
    try:
        os.nice(15)
    except OSError:
        pass
    try:
        psutil.Process().ionice(psutil.IOPRIO_CLASS_IDLE)
    except Exception:
        pass


def wait_if_busy(tcfg, log=None):
    cores = os.cpu_count() or 1
    while True:
        cpu = psutil.cpu_percent(interval=1)
        load = os.getloadavg()[0]
        if cpu <= tcfg["cpu_percent"] and load <= cores * tcfg["load_per_core"]:
            return
        if log:
            log.info("busy cpu=%.0f%% load=%.2f -> wait %ss", cpu, load, tcfg["wait_seconds"])
        time.sleep(tcfg["wait_seconds"])
