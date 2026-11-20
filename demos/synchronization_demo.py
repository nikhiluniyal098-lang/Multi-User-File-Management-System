from multiprocessing import Process, Event
from pathlib import Path
import time
from services.file_lock import locked_file

def worker(label, path, ready=None):
    if ready:
        ready.wait()
    print(f"{label}: requesting exclusive lock")
    with locked_file(path, "r+b", exclusive=True, timeout=8) as handle:
        print(f"{label}: acquired lock")
        handle.seek(0); content=handle.read()
        handle.seek(0); handle.write(content + label.encode())
        handle.flush()
        time.sleep(2)
        print(f"{label}: releasing lock")

if __name__ == "__main__":
    target=Path(__file__).resolve().parents[1]/"storage"/"temp"/"lock-demo.bin"
    target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(b"start-")
    gate=Event()
    p1=Process(target=worker,args=("Process-A",target,None))
    p2=Process(target=worker,args=("Process-B",target,gate))
    p1.start(); time.sleep(.4); p2.start(); gate.set()
    p1.join(); p2.join()
    print("Final content:",target.read_bytes())
