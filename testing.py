# main.py
from async_logger import init_logger, log, shutdown_logger
from multiprocessing import Process
import multiprocessing
import time


def worker(n):
    for i in range(3):
        log(f"Child {n} log {i}")


if __name__ == "__main__":
    multiprocessing.set_start_method("spawn")
    init_logger()

    procs = [Process(target=worker, args=(i,)) for i in range(2)]
    for p in procs:
        p.start()
    for p in procs:
        p.join()

    log("Main process final log")
    time.sleep(1)
    shutdown_logger()
