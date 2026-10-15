"""FTK1 player.db (SQLite) helpers."""
import sqlite3
from pathlib import Path


class PlayerDB:
    def __init__(self, path=None, raw_bytes=None):
        self.path = path
        if raw_bytes is not None:
            import tempfile, os
            fd, tmp = tempfile.mkstemp(suffix=".db")
            os.close(fd)
            with open(tmp, "wb") as fh:
                fh.write(raw_bytes)
            self.path = tmp
            self._tmp = tmp
        else:
            self._tmp = None
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row

    @classmethod
    def from_bytes(cls, data):
        return cls(raw_bytes=data)

    def close(self):
        try:
            self.conn.close()
        except Exception:
            pass
        if getattr(self, "_tmp", None):
            try:
                Path(self._tmp).unlink()
            except FileNotFoundError:
                pass

    def stats(self):
        rows = self.conn.execute("SELECT Name, Value FROM sPlayerStatistic ORDER BY Name").fetchall()
        return [{"name": r["Name"], "value": r["Value"]} for r in rows]

    def set_stat(self, name, value):
        cur = self.conn.execute("UPDATE sPlayerStatistic SET Value=? WHERE Name=?", (int(value), name))
        if cur.rowcount == 0:
            now = "2025-01-01 00:00:00"
            self.conn.execute(
                "INSERT INTO sPlayerStatistic (CreatedDateTime, LastModifiedDateTime, Name, Value) VALUES (?,?,?,?)",
                (now, now, name, int(value)),
            )
        self.conn.commit()

    def achievements(self):
        rows = self.conn.execute("SELECT Name, IsAchieved FROM sPlayerAchievement ORDER BY Name").fetchall()
        return [{"name": r["Name"], "achieved": bool(r["IsAchieved"])} for r in rows]

    def set_achievement(self, name, achieved):
        self.conn.execute("UPDATE sPlayerAchievement SET IsAchieved=? WHERE Name=?", (1 if achieved else 0, name))
        self.conn.commit()

    def unlock_all_lore(self):
        # Unlock every lore entry reveal and set total lore to count of unlocked.
        unlocked = 0
        for row in self.conn.execute("SELECT Name FROM sPlayerStatistic WHERE Name LIKE 'STAT_LU_%_REVEAL'").fetchall():
            self.set_stat(row["Name"], 1)
            unlocked += 1
        for row in self.conn.execute("SELECT Name FROM sPlayerStatistic WHERE Name LIKE 'STAT_LU_%' AND Name NOT LIKE '%_REVEAL'").fetchall():
            # only set base entries (non-zero content items) to 1; leave totals? We'll set all lore unlocks
            if row["Name"] not in ("STAT_LU_TOTAL_LORE",):
                try:
                    self.set_stat(row["Name"], 1)
                except Exception:
                    pass
        # Set total lore to number of base lore unlocks (excluding reveal/progress helpers). Heuristic: count STAT_LU_ base set.
        base = self.conn.execute("SELECT COUNT(*) c FROM sPlayerStatistic WHERE Name LIKE 'STAT_LU_%' AND Name NOT LIKE '%_REVEAL' AND Value=1").fetchone()["c"]
        self.set_stat("STAT_LU_TOTAL_LORE", base)
        self.conn.commit()
        return base

    def to_bytes(self):
        import sqlite3, tempfile, os
        # Copy db file to bytes safely
        # Ensure committed
        self.conn.commit()
        if self.path:
            return Path(self.path).read_bytes() if isinstance(self.path, str) else self.path.read_bytes()
        raise RuntimeError("no path")

    def stats_dict(self):
        return {r["name"]: r["value"] for r in self.stats()}
