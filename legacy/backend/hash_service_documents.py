import hashlib
import os
 
 
def calculate_hash(file_path: str) -> str:
    """
    Calculate the SHA-256 hash of a file.
 
    Args:
        file_path: Path to the file to hash.
 
    Returns:
        The hex-encoded SHA-256 hash of the file's contents.
 
    Raises:
        FileNotFoundError: If file_path does not exist.
    """
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"No such file: {file_path}")
 
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)
 
    return sha256.hexdigest()
 
 
def hash_bytes(data: bytes) -> str:
    """
    Calculate SHA-256 hash directly from bytes.
    Useful when the file is already loaded in memory
    (e.g. an UploadFile in FastAPI, before saving to disk).
    """
    return hashlib.sha256(data).hexdigest()
 
 
def build_hash_response(filename: str, file_path: str) -> dict:
    """Convenience wrapper matching the response shape used across the API."""
    return {
        "filename": filename,
        "sha256_hash": calculate_hash(file_path),
    }
 
 
if __name__ == "__main__":
    # Manual test: python hash_service.py path/to/file.pdf
    import sys
 
    if len(sys.argv) != 2:
        print("Usage: python hash_service.py <file_path>")
    else:
        print(build_hash_response(os.path.basename(sys.argv[1]), sys.argv[1]))
 