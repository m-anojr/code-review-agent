import threading

counter = 0
results = []


def increment():
    """Increment shared counter without synchronization."""
    global counter
    for _ in range(10000):
        # bug: race condition -- read-modify-write is not atomic
        counter += 1


def append_result(value):
    """Append to shared list from multiple threads without locking."""
    # bug: list.append is thread-safe in CPython due to GIL, but this pattern
    # is unsafe in general and the surrounding logic often is not
    processed = expensive_transform(value)
    results.append(processed)


def expensive_transform(value):
    return value * 2


def run_workers(data):
    threads = []
    for item in data:
        t = threading.Thread(target=append_result, args=(item,))
        threads.append(t)
        t.start()
    for t in threads:
        t.join()
    return results
