from pathlib import Path
from multiprocessing import Process
import time
from services.deadlock_prevention import ordered_file_locks

def work(name, items):
    print(name, "requests", [i for i,_ in items])
    with ordered_file_locks(items, exclusive=True, timeout=10) as locks:
        print(name, "acquired", [i for i,_ in locks])
        time.sleep(1)
    print(name, "released all locks")

if __name__ == "__main__":
    base=Path(__file__).resolve().parents[1]/"storage"/"temp"
    base.mkdir(parents=True,exist_ok=True)
    f10=base/"file10.bin"; f20=base/"file20.bin"
    f10.touch(exist_ok=True); f20.touch(exist_ok=True)
    p1=Process(target=work,args=("Process-A",[(10,f10),(20,f20)]))
    p2=Process(target=work,args=("Process-B",[(20,f20),(10,f10)]))
    p1.start(); p2.start(); p1.join(); p2.join()
    print("Both processes used ascending ID order; circular wait is prevented.")
