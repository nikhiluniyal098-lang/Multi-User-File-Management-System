from pathlib import Path
from services.deadlock_prevention import ordered_file_locks

def test_lock_order_is_sorted(tmp_path):
    a=tmp_path/"a"; b=tmp_path/"b"
    a.write_text("a"); b.write_text("b")
    with ordered_file_locks([(20,b),(10,a)], timeout=2) as acquired:
        assert [item[0] for item in acquired] == [10,20]
