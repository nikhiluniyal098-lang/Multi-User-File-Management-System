import threading
from services.synchronization import get_thread_lock

def test_mutex_serializes_threads():
    lock=get_thread_lock("unit-test")
    values=[]
    def worker(n):
        with lock:
            values.append(n)
    ts=[threading.Thread(target=worker,args=(i,)) for i in range(8)]
    [t.start() for t in ts]; [t.join() for t in ts]
    assert sorted(values)==list(range(8))
