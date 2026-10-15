"""Flask web app: For The King I save editor."""
import gzip
import json
import os
import uuid
from datetime import datetime
from pathlib import Path

from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for

from core.ftk_save import FTKSave, find_run_saves
from core.playerdb import PlayerDB

APP = Flask(__name__)
APP.secret_key = "ftk1-se-local"
WORKING = {}


def _sid():
    return uuid.uuid4().hex



def _fmt_time(p):
    try:
        return datetime.fromtimestamp(Path(p).stat().st_mtime).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return ""

def find_db_files():
    out=set()
    bases=[Path.home()/".config"/"unity3d"/"IronOak Games"/"FTK"/"save"]
    steam=Path.home()/".local"/"share"/"Steam"/"steamapps"/"compatdata"
    if steam.exists():
        for p in steam.rglob("IronOak Games/FTK/save"):
            if p.exists(): bases.append(p)
    for b in bases:
        if b.exists():
            for p in b.rglob("player.db"):
                out.add(str(p))
    return sorted(out)

@APP.route("/")
def index():
    run_saves = [{"path": p, "mtime": _fmt_time(p)} for p in find_run_saves()]
    db_saves = [{"path": p, "mtime": _fmt_time(p)} for p in find_db_files()]
    working_list = [{"sid": sid, "w": w, "created": w.get("created", "")} for sid, w in WORKING.items()]
    return render_template("index.html", run_saves=run_saves, db_saves=db_saves, working=working_list)


@APP.route("/open_save", methods=["POST"])
def open_save():
    path = request.form.get("path", "").strip()
    uploaded = request.files.get("file")
    if uploaded and uploaded.filename:
        data = uploaded.read()
        save = FTKSave.from_bytes(data, None)
        sid = _sid()
        WORKING[sid] = {"type": "save", "save": save, "filename": uploaded.filename, "created": datetime.now().strftime("%H:%M:%S")}
        return redirect(url_for("editor", sid=sid))
    if path:
        save = FTKSave.from_file(path)
        sid = _sid()
        WORKING[sid] = {"type": "save", "save": save, "source_path": path, "filename": Path(path).name, "created": datetime.now().strftime("%H:%M:%S")}
        return redirect(url_for("editor", sid=sid))
    return redirect(url_for("index"))


@APP.route("/open_db", methods=["POST"])
def open_db():
    path = request.form.get("path", "").strip()
    uploaded = request.files.get("file")
    if uploaded and uploaded.filename:
        db = PlayerDB.from_bytes(uploaded.read())
        sid = _sid()
        WORKING[sid] = {"type": "db", "db": db, "filename": uploaded.filename, "created": datetime.now().strftime("%H:%M:%S")}
        return redirect(url_for("db_editor", sid=sid))
    if path:
        db = PlayerDB(path)
        sid = _sid()
        WORKING[sid] = {"type": "db", "db": db, "source_path": path, "filename": Path(path).name, "created": datetime.now().strftime("%H:%M:%S")}
        return redirect(url_for("db_editor", sid=sid))
    return redirect(url_for("index"))


@APP.route("/save/<sid>")
def editor(sid):
    w = WORKING.get(sid)
    if not w or w["type"] != "save":
        return redirect(url_for("index"))
    return render_template("editor.html", sid=sid, filename=w.get("filename"))


@APP.route("/db/<sid>")
def db_editor(sid):
    w = WORKING.get(sid)
    if not w or w["type"] != "db":
        return redirect(url_for("index"))
    return render_template("db.html", sid=sid, filename=w.get("filename"))


# ---------- Save APIs ----------

@APP.route("/api/save/<sid>/summary")
def api_save_summary(sid):
    w = WORKING.get(sid)
    if not w:
        return jsonify({"error": "not found"}), 404
    save = w["save"]
    return jsonify({
        "filename": w.get("filename"),
        "source_path": w.get("source_path"),
        "player_count": save.player_count(),
        "player_labels": save.player_labels(),
        "game_info": save.game_info,
    })


@APP.route("/api/save/<sid>/player/<int:idx>")
def api_get_player(sid, idx):
    w = WORKING.get(sid)
    if not w:
        return jsonify({"error": "not found"}), 404
    try:
        p = w["save"].get_player(idx)
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    return jsonify({
        "index": p["index"],
        "label": p["label"],
        "raw": p["raw"],
        "cs": p["cs"],
        "cow": p["cow"],
        "inst": p["raw"].get("m_InstData"),
    })


@APP.route("/api/save/<sid>/player/<int:idx>/cs", methods=["POST"])
def api_set_cs(sid, idx):
    w = WORKING.get(sid)
    if not w:
        return jsonify({"error": "not found"}), 404
    body = request.get_json(force=True)
    text = body.get("text")
    obj = body.get("obj")
    try:
        if obj is not None:
            pass
        else:
            obj = json.loads(text)
        w["save"].set_player_cs(idx, obj)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@APP.route("/api/save/<sid>/player/<int:idx>/cow", methods=["POST"])
def api_set_cow(sid, idx):
    w = WORKING.get(sid)
    if not w:
        return jsonify({"error": "not found"}), 404
    body = request.get_json(force=True)
    text = body.get("text")
    obj = body.get("obj")
    try:
        if obj is None:
            obj = json.loads(text)
        w["save"].set_player_cow(idx, obj)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@APP.route("/api/save/<sid>/player/<int:idx>/inst", methods=["POST"])
def api_set_inst(sid, idx):
    w = WORKING.get(sid)
    if not w:
        return jsonify({"error": "not found"}), 404
    body = request.get_json(force=True)
    try:
        inst = body.get("inst", body.get("obj"))
        w["save"].set_player_inst(idx, inst)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@APP.route("/api/save/<sid>/player/<int:idx>/raw", methods=["POST"])
def api_set_player_raw(sid, idx):
    w = WORKING.get(sid)
    if not w:
        return jsonify({"error": "not found"}), 404
    body = request.get_json(force=True)
    try:
        obj = body.get("obj")
        if obj is None:
            obj = json.loads(body.get("text", "{}"))
        w["save"].set_player_raw(idx, obj)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@APP.route("/api/save/<sid>/raw")
def api_raw_get(sid):
    w = WORKING.get(sid)
    if not w:
        return jsonify({"error": "not found"}), 404
    return jsonify({"text": json.dumps(w["save"].data, ensure_ascii=False, indent=2)})


@APP.route("/api/save/<sid>/raw", methods=["POST"])
def api_raw_set(sid):
    w = WORKING.get(sid)
    if not w:
        return jsonify({"error": "not found"}), 404
    body = request.get_json(force=True)
    text = body.get("text", "")
    try:
        obj = json.loads(text)
        w["save"].data = obj
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@APP.route("/api/save/<sid>/gameinfo", methods=["POST"])
def api_gameinfo(sid):
    w = WORKING.get(sid)
    if not w:
        return jsonify({"error": "not found"}), 404
    body = request.get_json(force=True)
    try:
        obj = body.get("obj")
        if obj is None:
            obj = json.loads(body.get("text", "{}"))
        w["save"].data["m_GameInfo"] = obj
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@APP.route("/api/save/<sid>/export")
def api_export(sid):
    w = WORKING.get(sid)
    if not w:
        return jsonify({"error": "not found"}), 404
    save = w["save"]
    data = save.to_bytes(compact=True)
    out_name = w.get("filename") or "edited.run"
    from io import BytesIO
    return send_file(BytesIO(data), download_name=out_name, as_attachment=True)


@APP.route("/api/save/<sid>/save_to_path", methods=["POST"])
def api_save_to_path(sid):
    w = WORKING.get(sid)
    if not w:
        return jsonify({"error": "not found"}), 404
    body = request.get_json(force=True)
    path = body.get("path")
    if not path:
        path = w.get("source_path")
    if not path:
        return jsonify({"error": "no path"}), 400
    # backup
    try:
        src = Path(path)
        if src.exists():
            backup = src.with_suffix(src.suffix + ".bak")
            src.replace(backup) if False else None
    except Exception:
        pass
    pth = Path(path)
    if pth.exists():
        try:
            pth.replace(pth.with_name(pth.name + ".bak")) if False else None
        except Exception:
            pass
        backup = pth.with_name(pth.name + ".bak")
        try:
            import shutil
            shutil.copy2(pth, backup)
        except Exception:
            pass
    w["save"].save_to(path, compact=True)
    w["source_path"] = path
    return jsonify({"ok": True, "path": path, "backup": str(pth.with_name(pth.name + ".bak")) if pth.exists() else None})


# ---------- Player DB APIs ----------

@APP.route("/api/db/<sid>/stats")
def api_db_stats(sid):
    w = WORKING.get(sid)
    if not w:
        return jsonify({"error": "not found"}), 404
    db = w["db"]
    return jsonify({"stats": db.stats(), "achievements": db.achievements()})


@APP.route("/api/db/<sid>/set_stat", methods=["POST"])
def api_db_set_stat(sid):
    w = WORKING.get(sid)
    if not w:
        return jsonify({"error": "not found"}), 404
    body = request.get_json(force=True)
    try:
        w["db"].set_stat(body["name"], body["value"])
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@APP.route("/api/db/<sid>/set_achievement", methods=["POST"])
def api_db_set_achievement(sid):
    w = WORKING.get(sid)
    if not w:
        return jsonify({"error": "not found"}), 404
    body = request.get_json(force=True)
    try:
        w["db"].set_achievement(body["name"], bool(body["achieved"]))
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@APP.route("/api/db/<sid>/unlock_all_lore", methods=["POST"])
def api_db_unlock_lore(sid):
    w = WORKING.get(sid)
    if not w:
        return jsonify({"error": "not found"}), 404
    try:
        n = w["db"].unlock_all_lore()
        return jsonify({"ok": True, "unlocked": n})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@APP.route("/api/db/<sid>/export")
def api_db_export(sid):
    w = WORKING.get(sid)
    if not w:
        return jsonify({"error": "not found"}), 404
    data = w["db"].to_bytes()
    from io import BytesIO
    return send_file(BytesIO(data), download_name=w.get("filename") or "player.db", as_attachment=True)


@APP.route("/api/db/<sid>/save_to_path", methods=["POST"])
def api_db_save_to_path(sid):
    w = WORKING.get(sid)
    if not w:
        return jsonify({"error": "not found"}), 404
    body = request.get_json(force=True)
    path = body.get("path") or w.get("source_path")
    if not path:
        return jsonify({"error": "no path"}), 400
    w["db"].conn.commit()
    import shutil
    pth = Path(path)
    if pth.exists():
        try:
            shutil.copy2(pth, pth.with_name(pth.name + ".bak"))
        except Exception:
            pass
    src = w["db"].path
    shutil.copyfile(src, path)
    w["source_path"] = path
    return jsonify({"ok": True, "path": path})


if __name__ == "__main__":
    APP.run(host="127.0.0.1", port=5000, debug=True)
