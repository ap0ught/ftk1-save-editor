"""In-memory model for a For The King I save."""
import json
from . import save_codec as codec


class FTKSave:
    def __init__(self, text, source_path=None):
        self.source_path = source_path
        self.original_text = text
        self.data = json.loads(text)

    @classmethod
    def from_bytes(cls, data, source_path=None):
        return cls(codec.unpack_bytes(data), source_path)

    @classmethod
    def from_file(cls, path):
        with open(path, "rb") as fh:
            return cls.from_bytes(fh.read(), path)

    @property
    def game_info(self):
        return self.data.setdefault("m_GameInfo", {})

    @property
    def players_raw(self):
        return self.data.setdefault("m_PlayerSerialize", [])

    def player_count(self):
        return len(self.players_raw)

    def player_labels(self):
        gi = self.game_info
        names = gi.get("m_PlayedWith") or []
        classes = gi.get("m_PlayedWithClass") or []
        levels = gi.get("m_PlayedWithLevel") or []
        out = []
        for i in range(len(names)):
            name = names[i] if i < len(names) else f"Player {i}"
            cls = classes[i] if i < len(classes) else "?"
            lvl = levels[i] if i < len(levels) else "?"
            # Prefer in-inventory or inst data name if present
            try:
                inst = self.players_raw[i].get("m_InstData", [])
                if len(inst) > 3 and isinstance(inst[3], dict):
                    v = inst[3].get("$content")
                    if v:
                        name = v
            except Exception:
                pass
            out.append(f"{name} ({cls} - level {lvl})")
        if not out:
            for i in range(len(self.players_raw)):
                out.append(f"Player {i}")
        return out

    def get_player(self, idx):
        idx = int(idx)
        if idx < 0 or idx >= len(self.players_raw):
            raise IndexError("player index out of range")
        p = self.players_raw[idx]
        cs_text = p.get("m_StateCSData")
        cow_text = p.get("m_StateCOWData")
        cs = json.loads(cs_text) if isinstance(cs_text, str) else cs_text
        cow = json.loads(cow_text) if isinstance(cow_text, str) else cow_text
        return {
            "index": idx,
            "label": self.player_labels()[idx] if self.player_count() else f"Player {idx}",
            "raw": p,
            "cs": cs,
            "cow": cow,
        }

    def set_player_cs(self, idx, obj):
        idx = int(idx)
        txt = codec.dump_json_text(obj, compact=True)
        json.loads(txt)  # validate
        self.players_raw[idx]["m_StateCSData"] = txt

    def set_player_cow(self, idx, obj):
        idx = int(idx)
        txt = codec.dump_json_text(obj, compact=True)
        json.loads(txt)
        self.players_raw[idx]["m_StateCOWData"] = txt

    def set_player_inst(self, idx, inst):
        idx = int(idx)
        if not isinstance(inst, list):
            raise ValueError("inst data must be a list")
        self.players_raw[idx]["m_InstData"] = inst

    def set_player_raw(self, idx, obj):
        idx = int(idx)
        if not isinstance(obj, dict):
            raise ValueError("player raw must be an object")
        self.players_raw[idx] = obj

    def to_text(self, compact=True):
        return codec.dump_json_text(self.data, compact=compact)

    def to_bytes(self, compact=True):
        return codec.pack_bytes(self.to_text(compact=compact))

    def save_to(self, path, compact=True):
        with open(path, "wb") as fh:
            fh.write(self.to_bytes(compact=compact))


def common_save_dirs():
    home = __import__("pathlib").Path.home()
    dirs = [
        home / ".config" / "unity3d" / "IronOak Games" / "FTK" / "save",
        home / ".local" / "share" / "Steam" / "steamapps" / "compatdata",
    ]
    return [d for d in dirs if d.exists()]


def find_run_saves():
    out = []
    for base in [__import__("pathlib").Path.home() / ".config" / "unity3d" / "IronOak Games" / "FTK" / "save"]:
        if base.exists():
            for p in base.rglob("*.run"):
                out.append(str(p))
    # Proton prefixes
    steam = __import__("pathlib").Path.home() / ".local" / "share" / "Steam" / "steamapps" / "compatdata"
    if steam.exists():
        for p in steam.rglob("*IronOak Games/FTK/save/*.run"):
            out.append(str(p))
    return sorted(set(out))
