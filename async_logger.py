# async_logger.py

import threading
import multiprocessing
import queue
import time
import os

# Internal state
_log_queue = None  # multiprocessing.Queue, shared via fork
_batch_thread = None
_stop_event = None
_initialized = False


def init_logger():
    global _log_queue, _batch_thread, _stop_event, _initialized

    if _initialized:
        return

    # Only initialize the queue in the main process
    if multiprocessing.current_process().name == "MainProcess":
        _log_queue = multiprocessing.Queue()
        _stop_event = threading.Event()
        _batch_thread = threading.Thread(target=_batch_worker, daemon=True)
        _batch_thread.start()
        _initialized = True
    else:
        # In subprocess: just assume the queue exists from the forked main process
        _initialized = True


def log(msg):
    if _log_queue is None:
        raise RuntimeError("Logger not initialized or used before init in main process")

    try:
        _log_queue.put_nowait((os.getpid(), msg))
    except Exception as e:
        print(f"Logging failed: {e}")


def shutdown_logger():
    global _stop_event, _batch_thread
    if _stop_event:
        _stop_event.set()
        _batch_thread.join(timeout=5)
        _stop_event = None


def _batch_worker():
    buffer = []
    while not _stop_event.is_set():
        try:
            item = _log_queue.get(timeout=0.5)
            buffer.append(item)
        except queue.Empty:
            pass

        if buffer:
            _flush(buffer)
            buffer.clear()

    # Final flush on shutdown
    while not _log_queue.empty():
        try:
            buffer.append(_log_queue.get_nowait())
        except queue.Empty:
            break
    if buffer:
        _flush(buffer)


def _flush(buffer):
    # Replace with actual write-to-disk or network logic
    print(f"[{os.getpid()}] Flushing {len(buffer)} logs")
    for pid, msg in buffer:
        print(f"[pid={pid}] {msg}")
