import threading
_thread_locks = {}
_registry_lock = threading.Lock()

def get_thread_lock(key):
    with _registry_lock:
        if key not in _thread_locks:
            _thread_locks[key] = threading.RLock()
        return _thread_locks[key]
