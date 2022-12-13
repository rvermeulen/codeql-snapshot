from hashlib import sha256
from models.snapshot import Snapshot


def snapshot_hash(snapshot: Snapshot) -> str:
    return sha256_hexdigest(
        f"{snapshot.project_url}-{snapshot.branch}-{snapshot.commit}"
    )


def sha256_hexdigest(content: str | bytes) -> str:
    if isinstance(content, str):
        content = content.encode("UTF-8")

    hash = sha256()
    hash.update(content)
    return hash.hexdigest()
