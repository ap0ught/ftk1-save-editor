import gzip, json, os, sys, tempfile, unittest
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path: sys.path.insert(0,ROOT)
from core.save_codec import unpack_bytes, pack_bytes
from core.ftk_save import FTKSave
from core.playerdb import PlayerDB

SAVE='/home/cmayfield/.config/unity3d/IronOak Games/FTK/save/KillVexor_2025_7_18_0.run'
DB='/home/cmayfield/.config/unity3d/IronOak Games/FTK/save/steam76561197968621086/player.db'

class TestSave(unittest.TestCase):
    def test_roundtrip_bytes(self):
        data=open(SAVE,'rb').read()
        text=unpack_bytes(data)
        obj=json.loads(text)
        out=pack_bytes(text)
        # decompress out
        raw=gzip.decompress(out)
        self.assertEqual(raw.decode('utf-16-le'), text)

    def test_ftksave_labels(self):
        save=FTKSave.from_file(SAVE)
        self.assertGreater(save.player_count(),0)
        self.assertEqual(len(save.player_labels()), save.player_count())

    def test_cs_edit_roundtrip(self):
        save=FTKSave.from_file(SAVE)
        before=save.get_player(0)['cs']['m_Gold']['$content']
        obj=save.get_player(0)['cs']
        obj['m_Gold']['$content']=999
        save.set_player_cs(0,obj)
        # reparse from serialized text
        txt=save.to_text()
        data2=FTKSave.__new__(FTKSave)
        data2.data=json.loads(txt)
        data2.source_path=None
        data2.original_text=txt
        # emulate get via class method instead
        save2=FTKSave(txt)
        self.assertEqual(save2.get_player(0)['cs']['m_Gold']['$content'],999)
        # original file unchanged
        self.assertEqual(FTKSave.from_file(SAVE).get_player(0)['cs']['m_Gold']['$content'], before)

    def test_pack_parse(self):
        save=FTKSave.from_file(SAVE)
        b=save.to_bytes()
        save2=FTKSave.from_bytes(b)
        self.assertEqual(save.player_count(), save2.player_count())
        self.assertEqual(save.get_player(0)['cs']['m_Gold']['$content'], save2.get_player(0)['cs']['m_Gold']['$content'])

class TestDB(unittest.TestCase):
    def test_stats(self):
        db=PlayerDB(DB)
        s=db.stats_dict()
        self.assertIn('STAT_LU_TOTAL_LORE', s)
        db.close()

    def test_set_stat_persist(self):
        import shutil
        tmp=tempfile.mktemp(suffix='.db')
        shutil.copyfile(DB,tmp)
        db=PlayerDB(tmp)
        db.set_stat('STAT_LU_TOTAL_LORE', 42)
        db.close()
        db2=PlayerDB(tmp)
        self.assertEqual(db2.stats_dict()['STAT_LU_TOTAL_LORE'],42)
        db2.close()
        os.remove(tmp)

if __name__=='__main__':
    unittest.main(verbosity=2)
