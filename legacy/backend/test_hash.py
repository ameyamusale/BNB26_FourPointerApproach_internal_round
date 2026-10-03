import os
import sys
 
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "app", "services"))
from hash_service import calculate_hash  # noqa: E402
 
ORIGINAL_DIR = os.path.join("..", "dataset", "original")
TAMPERED_DIR = os.path.join("..", "dataset", "tampered")
 
 
def run():
    if not os.path.isdir(ORIGINAL_DIR):
        print(f"Folder not found: {ORIGINAL_DIR}")
        return
 
    original_files = os.listdir(ORIGINAL_DIR)
    if not original_files:
        print("No files in dataset/original — add a sample PDF first.")
        return
 
    for fname in original_files:
        orig_path = os.path.join(ORIGINAL_DIR, fname)
        tampered_path = os.path.join(TAMPERED_DIR, fname)
 
        orig_hash = calculate_hash(orig_path)
        print(f"[ORIGINAL]  {fname} -> {orig_hash}")
 
        if os.path.isfile(tampered_path):
            tampered_hash = calculate_hash(tampered_path)
            print(f"[TAMPERED]  {fname} -> {tampered_hash}")
            assert orig_hash != tampered_hash, "FAIL: hashes should differ!"
            print("  Hashes differ as expected.\n")
        else:
            print(f"  (no matching tampered file for {fname})\n")
 
 
if __name__ == "__main__":
    run()