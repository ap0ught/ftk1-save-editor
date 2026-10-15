"""FTK1 .run save encoding helpers."""
import gzip
import json


def unpack_bytes(data: bytes) -> str:
    raw = gzip.decompress(data)
    # FTK1 saves are gzipped UTF-16LE JSON (no BOM).
    try:
        return raw.decode("utf-16-le")
    except UnicodeDecodeError:
        return raw.decode("utf-8")


def pack_bytes(text: str) -> bytes:
    return gzip.compress(text.encode("utf-16-le"))


def load_json_text(text: str):
    return json.loads(text)


def dump_json_text(obj, compact: bool = True) -> str:
    if compact:
        return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    return json.dumps(obj, ensure_ascii=False, indent=2)


def unpack_file(path: str) -> str:
    with open(path, "rb") as fh:
        return unpack_bytes(fh.read())


def pack_file(text: str, path: str) -> None:
    with open(path, "wb") as fh:
        fh.write(pack_bytes(text))
