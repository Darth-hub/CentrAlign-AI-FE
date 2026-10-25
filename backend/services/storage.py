"""Private persistent upload storage. Keys are generated server-side."""
from pathlib import Path
import uuid
from config import settings

def save_document(data):
    if len(data) > 10 * 1024 * 1024: raise ValueError("Document exceeds 10 MB")
    root = Path(settings.storage_path)
    root.mkdir(parents=True, exist_ok=True)
    key = str(uuid.uuid4())
    path = root / key
    path.write_bytes(data)
    path.chmod(0o600)
    return key

def read_document(key):
    if str(uuid.UUID(key)) != key: raise ValueError("Invalid document key")
    return (Path(settings.storage_path) / key).read_bytes()
