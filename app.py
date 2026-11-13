# Built by Manaswin Tripathi (@manaswintripathi)
"""
Smart Attendance Predictor
---------------------------
A small Flask + SQLite app that tracks attendance per subject, shows the
current percentage against the 75% rule, and predicts how many classes you
must attend in a row to reach your target — or how many you can still skip
while staying at or above it.

Run:
    pip install -r requirements.txt
    python app.py
Then open http://127.0.0.1:5000
"""
import math
import os
import sqlite3

from flask import Flask, g, jsonify, render_template, request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "attendance.db")
DEFAULT_TARGET = 75.0

# Realistic sample data. Overall: 134 attended / 181 total = 74.03%.
SEED_SUBJECTS = [
    ("Cryptography & Network Security", 20, 26),
    ("Wireless Network Security", 24, 30),
    ("Hands-on DSA for Industry Prep-III", 18, 28),
    ("Technical Training for Placement-III", 30, 38),
    ("PDP Soft Skill", 22, 29),
    ("Major Project-I", 20, 30),
]

app = Flask(__name__)


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            attended INTEGER NOT NULL DEFAULT 0,
            total INTEGER NOT NULL DEFAULT 0,
            CHECK (attended >= 0),
            CHECK (total >= 0),
            CHECK (attended <= total)
        )
        """
    )
    count = conn.execute("SELECT COUNT(*) FROM subjects").fetchone()[0]
    if count == 0:
        conn.executemany(
            "INSERT INTO subjects (name, attended, total) VALUES (?, ?, ?)",
            SEED_SUBJECTS,
        )
    conn.commit()
    conn.close()


def calc_stats(attended, total, target=DEFAULT_TARGET):
    """Return percentage, classes needed to reach target, skippable classes."""
    attended = int(attended)
    total = int(total)
    target = float(target)
    pct = (attended / total * 100.0) if total > 0 else 100.0
    if total == 0:
        needed = 0
        skippable = 0
    elif pct >= target:
        needed = 0
        # a / (t + s) >= target/100  ->  s <= a*100/target - t
        skippable = max(0, math.floor(attended * 100.0 / target - total))
    else:
        # (a + x) / (t + x) >= target/100
        if target >= 100:
            needed = 0 if attended == total else -1
        else:
            needed = math.ceil((target * total / 100.0 - attended) / (1 - target / 100.0))
            needed = max(0, needed)
        skippable = 0
    return {
        "attended": attended,
        "total": total,
        "percentage": round(pct, 2),
        "target": target,
        "needed_to_reach_target": needed,
        "can_skip": skippable,
        "is_safe": pct >= target,
    }


def subject_to_dict(row):
    stats = calc_stats(row["attended"], row["total"])
    return {"id": row["id"], "name": row["name"], **stats}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/subjects", methods=["GET"])
def list_subjects():
    db = get_db()
    rows = db.execute("SELECT * FROM subjects ORDER BY id").fetchall()
    return jsonify([subject_to_dict(r) for r in rows])


@app.route("/api/subjects", methods=["POST"])
def add_subject():
    data = request.get_json(force=True, silent=True) or {}
    name = (data.get("name") or "").strip()
    try:
        attended = int(data.get("attended", 0))
        total = int(data.get("total", 0))
    except (TypeError, ValueError):
        return jsonify({"error": "attended and total must be integers"}), 400
    if not name:
        return jsonify({"error": "name is required"}), 400
    if attended < 0 or total < 0 or attended > total:
        return jsonify({"error": "require 0 <= attended <= total"}), 400
    db = get_db()
    cur = db.execute(
        "INSERT INTO subjects (name, attended, total) VALUES (?, ?, ?)",
        (name, attended, total),
    )
    db.commit()
    row = db.execute("SELECT * FROM subjects WHERE id = ?", (cur.lastrowid,)).fetchone()
    return jsonify(subject_to_dict(row)), 201


@app.route("/api/subjects/<int:subject_id>", methods=["PUT"])
def update_subject(subject_id):
    data = request.get_json(force=True, silent=True) or {}
    db = get_db()
    row = db.execute("SELECT * FROM subjects WHERE id = ?", (subject_id,)).fetchone()
    if row is None:
        return jsonify({"error": "subject not found"}), 404
    name = (data.get("name") or row["name"]).strip()
    try:
        attended = int(data.get("attended", row["attended"]))
        total = int(data.get("total", row["total"]))
    except (TypeError, ValueError):
        return jsonify({"error": "attended and total must be integers"}), 400
    if not name or attended < 0 or total < 0 or attended > total:
        return jsonify({"error": "require a name and 0 <= attended <= total"}), 400
    db.execute(
        "UPDATE subjects SET name = ?, attended = ?, total = ? WHERE id = ?",
        (name, attended, total, subject_id),
    )
    db.commit()
    row = db.execute("SELECT * FROM subjects WHERE id = ?", (subject_id,)).fetchone()
    return jsonify(subject_to_dict(row))


@app.route("/api/subjects/<int:subject_id>", methods=["DELETE"])
def delete_subject(subject_id):
    db = get_db()
    cur = db.execute("DELETE FROM subjects WHERE id = ?", (subject_id,))
    db.commit()
    if cur.rowcount == 0:
        return jsonify({"error": "subject not found"}), 404
    return jsonify({"ok": True})


@app.route("/api/subjects/<int:subject_id>/attend", methods=["POST"])
def mark_attended(subject_id):
    db = get_db()
    cur = db.execute(
        "UPDATE subjects SET attended = attended + 1, total = total + 1 WHERE id = ?",
        (subject_id,),
    )
    db.commit()
    if cur.rowcount == 0:
        return jsonify({"error": "subject not found"}), 404
    row = db.execute("SELECT * FROM subjects WHERE id = ?", (subject_id,)).fetchone()
    return jsonify(subject_to_dict(row))


@app.route("/api/subjects/<int:subject_id>/miss", methods=["POST"])
def mark_missed(subject_id):
    db = get_db()
    cur = db.execute(
        "UPDATE subjects SET total = total + 1 WHERE id = ?", (subject_id,)
    )
    db.commit()
    if cur.rowcount == 0:
        return jsonify({"error": "subject not found"}), 404
    row = db.execute("SELECT * FROM subjects WHERE id = ?", (subject_id,)).fetchone()
    return jsonify(subject_to_dict(row))


@app.route("/api/overall", methods=["GET"])
def overall():
    db = get_db()
    row = db.execute(
        "SELECT COALESCE(SUM(attended), 0) AS a, COALESCE(SUM(total), 0) AS t "
        "FROM subjects"
    ).fetchone()
    return jsonify(calc_stats(row["a"], row["t"]))


@app.route("/api/predict", methods=["GET"])
def predict():
    try:
        attended = int(request.args.get("attended", 0))
        total = int(request.args.get("total", 0))
        target = float(request.args.get("target", DEFAULT_TARGET))
    except (TypeError, ValueError):
        return jsonify({"error": "attended/total/target must be numbers"}), 400
    if attended < 0 or total < 0 or attended > total or not (0 < target <= 100):
        return jsonify({"error": "require 0 <= attended <= total and 0 < target <= 100"}), 400
    return jsonify(calc_stats(attended, total, target))


@app.route("/api/seed", methods=["POST"])
def reseed():
    db = get_db()
    db.execute("DELETE FROM subjects")
    db.executemany(
        "INSERT INTO subjects (name, attended, total) VALUES (?, ?, ?)", SEED_SUBJECTS
    )
    db.commit()
    rows = db.execute("SELECT * FROM subjects ORDER BY id").fetchall()
    return jsonify([subject_to_dict(r) for r in rows])


@app.route("/api/clear", methods=["POST"])
def clear_all():
    db = get_db()
    db.execute("DELETE FROM subjects")
    db.commit()
    return jsonify({"ok": True})


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


init_db()

if __name__ == "__main__":
    init_db()
    app.run(host="127.0.0.1", port=5000, debug=True)
