#!/usr/bin/env python3
"""Verify a FTK1 .run save: unpack, parse, and print a concise sanity report."""
import gzip
import json
import sys
from pathlib import Path


def main():
    if len(sys.argv) < 2:
        print("usage: python3 verify_save.py <save.run>")
        raise SystemExit(2)
    path = Path(sys.argv[1])
    raw = gzip.decompress(path.read_bytes())
    text = raw.decode("utf-16-le")
    d = json.loads(text)
    gi = d.get("m_GameInfo", {})
    print("File:", path)
    print("Game:", gi.get("m_GameDefinition"), "| room:", gi.get("m_GameRoomName"), "| day:", gi.get("m_GameDay"), "| diff:", gi.get("m_DiffType"))
    names = gi.get("m_PlayedWith", [])
    classes = gi.get("m_PlayedWithClass", [])
    levels = gi.get("m_PlayedWithLevel", [])
    for i, p in enumerate(d.get("m_PlayerSerialize", [])):
        cs = json.loads(p.get("m_StateCSData", "{}"))
        cow = json.loads(p.get("m_StateCOWData", "{}"))
        inv = (cow.get("m_PlayerInventory") or {})
        bp = (inv.get("m_ContainerBackpack") or {}).get("m_ItemCounts", {})
        name = p.get("m_InstData", [None, None, None, {}])[3].get("$content") if len(p.get("m_InstData", [])) > 3 else names[i] if i < len(names) else f"Player {i}"
        print(f"\nPlayer {i}: {name} ({classes[i] if i < len(classes) else '?'} level {levels[i] if i < len(levels) else '?'})")
        print("  HP:", gc(cs, "m_HealthCurrent"), "XP:", gc(cs, "m_PlayerXP"), "Gold:", gc(cs, "m_Gold"), "Focus:", gc(cs, "m_FocusPoints"))
        print("  Backpack:", bp)
    print("\nJSON parse: OK")
    print("Decompressed size:", len(raw), "bytes")


def gc(obj, key):
    v = obj.get(key)
    if isinstance(v, dict) and "$content" in v:
        return v["$content"]
    return v


if __name__ == "__main__":
    main()
