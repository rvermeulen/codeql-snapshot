from hashlib import sha256


def sha256_hexdigest(content: str | bytes) -> str:
    if isinstance(content, str):
        content = content.encode("UTF-8")

    hash = sha256()
    hash.update(content)
    return hash.hexdigest()
