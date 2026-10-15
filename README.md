# FTK1 Save Editor (web)

A local Flask web app for editing *For The King* (FTK1) save files.

## Supports
- `.run` saves: unpack (gzip UTF-16 JSON), edit, repack.
- Game info, per-player vitals/stats, State CS/COW JSON, InstData, raw player JSON, full raw save JSON.
- `player.db`: statistics, achievements, one-click lore unlock, export.

## Run
```bash
cd /path/to/ftk1-save-editor
python -m pip install -r requirements.txt
python app.py
```
Then open http://127.0.0.1:5000

## Save locations (Linux / Proton)
- Native Unity: `~/.config/unity3d/IronOak Games/FTK/save/`
- Steam Play: `~/.local/share/Steam/steamapps/compatdata/*/pfx/drive_c/users/steamuser/AppData/LocalLow/IronOak Games/FTK/save/`

## Safety
- Always back up saves. The app writes `.bak` beside the destination when saving to a path.
- Editing raw JSON can corrupt saves if invalid types are used. The app validates JSON but not game semantics.
- The game must be closed (or save not in use) before overwriting `.run`/`player.db`.

## Tests
```bash
python -m unittest tests.test_core -v
```
