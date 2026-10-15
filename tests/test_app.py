import gzip
import json
import os
import sys
import tempfile
import shutil
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app import APP
from core.ftk_save import FTKSave

SAVE = "/home/cmayfield/.config/unity3d/IronOak Games/FTK/save/KillVexor_2025_7_18_0.run"
DB = "/home/cmayfield/.config/unity3d/IronOak Games/FTK/save/steam76561197968621086/player.db"


class FlaskSaveTests(unittest.TestCase):
    def setUp(self):
        APP.testing = True
        self.client = APP.test_client()
        # clear in-memory sessions for isolation
        from app import WORKING
        WORKING.clear()
        r = self.client.post("/open_save", data={"path": SAVE})
        self.assertEqual(r.status_code in (302, 303), True)
        self.sid = r.headers["Location"].rstrip("/").split("/")[-1]

    def test_index(self):
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"FTK1", r.data)

    def test_summary(self):
        r = self.client.get(f"/api/save/{self.sid}/summary")
        self.assertEqual(r.status_code, 200)
        d = r.get_json()
        self.assertEqual(d["player_count"], 3)
        self.assertIn("Anakrino", d["player_labels"][0])

    def test_player_get(self):
        r = self.client.get(f"/api/save/{self.sid}/player/0")
        self.assertEqual(r.status_code, 200)
        d = r.get_json()
        self.assertEqual(d["cs"]["m_Gold"]["$content"], 14)

    def test_cs_replace_and_export(self):
        obj = {"m_Gold": {"$content": 500, "$type": "System.Int32"}}
        r = self.client.post(f"/api/save/{self.sid}/player/0/cs", json={"obj": obj})
        self.assertEqual(r.status_code, 200)
        # export
        r = self.client.get(f"/api/save/{self.sid}/export")
        self.assertEqual(r.status_code, 200)
        raw = gzip.decompress(r.data)
        d = json.loads(raw.decode("utf-16-le"))
        cs = json.loads(d["m_PlayerSerialize"][0]["m_StateCSData"])
        self.assertEqual(cs["m_Gold"]["$content"], 500)

    def test_raw_roundtrip(self):
        r = self.client.get(f"/api/save/{self.sid}/raw")
        self.assertEqual(r.status_code, 200)
        text = r.get_json()["text"]
        r = self.client.post(f"/api/save/{self.sid}/raw", json={"text": text})
        self.assertEqual(r.status_code, 200)
        r = self.client.get(f"/api/save/{self.sid}/raw")
        self.assertEqual(r.get_json()["text"], text)

    def test_invalid_player_index(self):
        r = self.client.get(f"/api/save/{self.sid}/player/99")
        self.assertEqual(r.status_code, 400)

    def test_save_to_path_backup(self):
        with tempfile.TemporaryDirectory() as td:
            dst = os.path.join(td, "out.run")
            shutil.copyfile(SAVE, dst)
            # open a fresh session pointing at dst so save_to_path can default to it
            from app import WORKING
            WORKING.clear()
            r = self.client.post("/open_save", data={"path": dst})
            sid = r.headers["Location"].rstrip("/").split("/")[-1]
            r = self.client.post(f"/api/save/{sid}/save_to_path", json={})
            self.assertEqual(r.status_code, 200)
            self.assertTrue(os.path.exists(dst + ".bak"))


class FlaskDBTests(unittest.TestCase):
    def setUp(self):
        APP.testing = True
        self.client = APP.test_client()
        from app import WORKING
        WORKING.clear()
        r = self.client.post("/open_db", data={"path": DB})
        self.assertEqual(r.status_code in (302, 303), True)
        self.sid = r.headers["Location"].rstrip("/").split("/")[-1]

    def test_stats(self):
        r = self.client.get(f"/api/db/{self.sid}/stats")
        self.assertEqual(r.status_code, 200)
        d = r.get_json()
        self.assertTrue(any(s["name"] == "STAT_LU_TOTAL_LORE" for s in d["stats"]))

    def test_set_stat(self):
        r = self.client.post(f"/api/db/{self.sid}/set_stat", json={"name": "STAT_LU_TOTAL_LORE", "value": 42})
        self.assertEqual(r.status_code, 200)
        r = self.client.get(f"/api/db/{self.sid}/stats")
        stats = {s["name"]: s["value"] for s in r.get_json()["stats"]}
        self.assertEqual(stats["STAT_LU_TOTAL_LORE"], 42)

    def test_unlock_all_lore(self):
        r = self.client.post(f"/api/db/{self.sid}/unlock_all_lore", json={})
        self.assertEqual(r.status_code, 200)
        self.assertIn("unlocked", r.get_json())


if __name__ == "__main__":
    unittest.main(verbosity=2)
