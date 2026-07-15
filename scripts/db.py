"""Shared DB helpers: schema init, insert, and query-to-dict."""
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).parent.parent
DB_PATH = ROOT / "nova.db"


def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_schema(conn):
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS lessons (
        lesson_id          INTEGER PRIMARY KEY,
        date               TEXT NOT NULL,
        duration_min       INTEGER,
        time_range         TEXT,
        teacher            TEXT,
        source_file        TEXT,
        version_note       TEXT,
        gaps_30s_count     INTEGER,
        errors_count       INTEGER,
        oral_written_ratio TEXT,
        mouse_working      INTEGER DEFAULT 1,
        latency_mean       REAL,
        latency_max        INTEGER,
        latency_n          INTEGER,
        summary            TEXT,
        sentence_patterns  TEXT DEFAULT '[]',
        stage_assessment   TEXT DEFAULT '{}'
    );

    CREATE TABLE IF NOT EXISTS repeat_latency_samples (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        lesson_id INTEGER REFERENCES lessons(lesson_id) ON DELETE CASCADE,
        scene     TEXT,
        ts        TEXT,
        latency   INTEGER
    );

    CREATE TABLE IF NOT EXISTS writing_tasks (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        lesson_id INTEGER REFERENCES lessons(lesson_id) ON DELETE CASCADE,
        name      TEXT,
        type      TEXT,
        ts        TEXT,
        seconds   INTEGER,
        rating    TEXT,
        note      TEXT
    );

    CREATE TABLE IF NOT EXISTS attention_gaps (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        lesson_id INTEGER REFERENCES lessons(lesson_id) ON DELETE CASCADE,
        scene     TEXT,
        ts        TEXT,
        seconds   INTEGER,
        type      TEXT,
        flag      TEXT,
        note      TEXT
    );

    CREATE TABLE IF NOT EXISTS error_corrections (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        lesson_id   INTEGER REFERENCES lessons(lesson_id) ON DELETE CASCADE,
        error       TEXT,
        ts          TEXT,
        seconds     INTEGER,
        prompt_type TEXT,
        note        TEXT
    );

    CREATE TABLE IF NOT EXISTS skills (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        lesson_id INTEGER REFERENCES lessons(lesson_id) ON DELETE CASCADE,
        name      TEXT,
        pct       INTEGER
    );

    CREATE TABLE IF NOT EXISTS modules (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        lesson_id INTEGER REFERENCES lessons(lesson_id) ON DELETE CASCADE,
        position  INTEGER,
        color     TEXT,
        name      TEXT,
        sub       TEXT,
        vocab     TEXT DEFAULT '[]'
    );

    CREATE TABLE IF NOT EXISTS performance_dimensions (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        lesson_id INTEGER REFERENCES lessons(lesson_id) ON DELETE CASCADE,
        label     TEXT,
        score     REAL,
        note      TEXT
    );

    CREATE TABLE IF NOT EXISTS performance_highlights (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        lesson_id INTEGER REFERENCES lessons(lesson_id) ON DELETE CASCADE,
        type      TEXT,
        text      TEXT
    );

    CREATE TABLE IF NOT EXISTS teacher_feedback (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        lesson_id INTEGER REFERENCES lessons(lesson_id) ON DELETE CASCADE,
        type      TEXT,
        text      TEXT
    );
    """)
    conn.commit()


def insert_lesson(conn, data):
    """Insert one lesson dict into all tables. Skips if lesson_id already exists."""
    lesson_id = data["lesson"]
    if conn.execute("SELECT 1 FROM lessons WHERE lesson_id=?", (lesson_id,)).fetchone():
        print(f"  L{lesson_id} already in DB, skipping.")
        return False

    m = data["metrics"]
    rl = m["repeat_latency"]
    perf = data["performance"]

    conn.execute("""
        INSERT INTO lessons
            (lesson_id, date, duration_min, time_range, teacher, source_file, version_note,
             gaps_30s_count, errors_count, oral_written_ratio, mouse_working,
             latency_mean, latency_max, latency_n, summary, sentence_patterns, stage_assessment)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        lesson_id, data["date"], data.get("duration_min"), data.get("time_range"),
        data.get("teacher"), data.get("source_file"), data.get("version_note"),
        m.get("gaps_30s_count"), m.get("errors_count"), m.get("oral_written_ratio"),
        0 if m.get("mouse_working") is False else 1,
        rl["mean"], rl["max"], rl["n"],
        perf.get("summary"),
        json.dumps(data.get("sentence_patterns", []), ensure_ascii=False),
        json.dumps(data.get("stage_assessment", {}), ensure_ascii=False),
    ))

    for s in rl.get("samples", []):
        conn.execute(
            "INSERT INTO repeat_latency_samples (lesson_id,scene,ts,latency) VALUES (?,?,?,?)",
            (lesson_id, s["scene"], s["ts"], s["latency"]))

    for t in m.get("writing_tasks", []):
        conn.execute(
            "INSERT INTO writing_tasks (lesson_id,name,type,ts,seconds,rating,note) VALUES (?,?,?,?,?,?,?)",
            (lesson_id, t["name"], t["type"], t["ts"], t["seconds"], t["rating"], t.get("note")))

    for g in m.get("attention_gaps", []):
        conn.execute(
            "INSERT INTO attention_gaps (lesson_id,scene,ts,seconds,type,flag,note) VALUES (?,?,?,?,?,?,?)",
            (lesson_id, g["scene"], g["ts"], g["seconds"], g["type"], g.get("flag"), g.get("note")))

    for e in m.get("error_corrections", []):
        conn.execute(
            "INSERT INTO error_corrections (lesson_id,error,ts,seconds,prompt_type,note) VALUES (?,?,?,?,?,?)",
            (lesson_id, e["error"], e["ts"], e["seconds"], e["prompt_type"], e.get("note")))

    for sk in data.get("skills", []):
        conn.execute(
            "INSERT INTO skills (lesson_id,name,pct) VALUES (?,?,?)",
            (lesson_id, sk["name"], sk["pct"]))

    for i, mod in enumerate(data.get("modules", [])):
        conn.execute(
            "INSERT INTO modules (lesson_id,position,color,name,sub,vocab) VALUES (?,?,?,?,?,?)",
            (lesson_id, i, mod["color"], mod["name"], mod["sub"],
             json.dumps(mod.get("vocab", []), ensure_ascii=False)))

    for dim in perf.get("dimensions", []):
        conn.execute(
            "INSERT INTO performance_dimensions (lesson_id,label,score,note) VALUES (?,?,?,?)",
            (lesson_id, dim["label"], dim["score"], dim.get("note")))

    for h in perf.get("highlights_good", []):
        conn.execute("INSERT INTO performance_highlights (lesson_id,type,text) VALUES (?,?,?)",
                     (lesson_id, "good", h))
    for h in perf.get("highlights_warn", []):
        conn.execute("INSERT INTO performance_highlights (lesson_id,type,text) VALUES (?,?,?)",
                     (lesson_id, "warn", h))
    for h in perf.get("notes", []):
        conn.execute("INSERT INTO performance_highlights (lesson_id,type,text) VALUES (?,?,?)",
                     (lesson_id, "note", h))

    for t in perf.get("teacher_feedback_pos", []):
        conn.execute("INSERT INTO teacher_feedback (lesson_id,type,text) VALUES (?,?,?)",
                     (lesson_id, "pos", t))
    for t in perf.get("teacher_feedback_neg", []):
        conn.execute("INSERT INTO teacher_feedback (lesson_id,type,text) VALUES (?,?,?)",
                     (lesson_id, "neg", t))
    for t in perf.get("teacher_feedback_neutral", []):
        conn.execute("INSERT INTO teacher_feedback (lesson_id,type,text) VALUES (?,?,?)",
                     (lesson_id, "neutral", t))

    conn.commit()
    return True


# Gap types that are expected task time (already covered by writing_tasks),
# vs. off-task gaps that are genuine attention signals.
TASK_GAP_TYPES = {"writing", "mouse-task", "mouse-failure", "page-turn",
                  "reading", "read-page", "technical"}

# Latency samples below this count are too small for a reliable mean.
LATENCY_MIN_N = 8


def load_lesson(conn, lesson_id):
    """Reconstruct a full lesson dict from all DB tables."""
    row = dict(conn.execute("SELECT * FROM lessons WHERE lesson_id=?", (lesson_id,)).fetchone())

    def rows(sql, *args):
        return [dict(r) for r in conn.execute(sql, args)]

    def texts(sql, *args):
        return [r[0] for r in conn.execute(sql, args)]

    def strip_none(lst, keys):
        for d in lst:
            for k in keys:
                if d.get(k) is None:
                    d.pop(k, None)
        return lst

    samples = rows(
        "SELECT scene,ts,latency FROM repeat_latency_samples WHERE lesson_id=? ORDER BY id", lesson_id)
    writing = strip_none(
        rows("SELECT name,type,ts,seconds,rating,note FROM writing_tasks WHERE lesson_id=? ORDER BY id", lesson_id),
        ["note"])
    gaps = strip_none(
        rows("SELECT scene,ts,seconds,type,flag,note FROM attention_gaps WHERE lesson_id=? ORDER BY id", lesson_id),
        ["flag", "note"])
    errors = strip_none(
        rows("SELECT error,ts,seconds,prompt_type,note FROM error_corrections WHERE lesson_id=? ORDER BY id", lesson_id),
        ["note"])
    skills = rows("SELECT name,pct FROM skills WHERE lesson_id=? ORDER BY id", lesson_id)
    raw_mods = rows("SELECT color,name,sub,vocab FROM modules WHERE lesson_id=? ORDER BY position", lesson_id)
    modules = []
    for m in raw_mods:
        mod = {"color": m["color"], "name": m["name"], "sub": m["sub"]}
        v = json.loads(m.get("vocab", "[]") or "[]")
        if v:
            mod["vocab"] = v
        modules.append(mod)
    dims = rows(
        "SELECT label,score,note FROM performance_dimensions WHERE lesson_id=? ORDER BY id", lesson_id)

    good    = texts("SELECT text FROM performance_highlights WHERE lesson_id=? AND type='good' ORDER BY id", lesson_id)
    warn    = texts("SELECT text FROM performance_highlights WHERE lesson_id=? AND type='warn' ORDER BY id", lesson_id)
    notes   = texts("SELECT text FROM performance_highlights WHERE lesson_id=? AND type='note' ORDER BY id", lesson_id)
    fb_pos  = texts("SELECT text FROM teacher_feedback WHERE lesson_id=? AND type='pos' ORDER BY id", lesson_id)
    fb_neg  = texts("SELECT text FROM teacher_feedback WHERE lesson_id=? AND type='neg' ORDER BY id", lesson_id)
    fb_neu  = texts("SELECT text FROM teacher_feedback WHERE lesson_id=? AND type='neutral' ORDER BY id", lesson_id)

    # Derived metrics, recomputed from detail rows on every load.
    dist = {}
    for s in samples:
        key = str(s["latency"])
        dist[key] = dist.get(key, 0) + 1
    alert_gaps = [g for g in gaps if g.get("flag") == "alert"]
    gaps_task = sum(1 for g in alert_gaps if g["type"] in TASK_GAP_TYPES)
    gaps_offtask = len(alert_gaps) - gaps_task
    errors_per_10min = (
        round(row["errors_count"] / row["duration_min"] * 10, 1)
        if row["duration_min"] else None)

    result = {
        "lesson": row["lesson_id"],
        "date": row["date"],
        "duration_min": row["duration_min"],
        "time_range": row["time_range"],
        "teacher": row["teacher"],
        "source_file": row["source_file"],
        "metrics": {
            "repeat_latency": {
                "mean": row["latency_mean"],
                "max": row["latency_max"],
                "n": row["latency_n"],
                "dist": dist,
                "low_confidence": row["latency_n"] < LATENCY_MIN_N,
                "samples": samples,
            },
            "writing_tasks": writing,
            "attention_gaps": gaps,
            "error_corrections": errors,
            "gaps_30s_count": row["gaps_30s_count"],
            "gaps_task_count": gaps_task,
            "gaps_offtask_count": gaps_offtask,
            "errors_count": row["errors_count"],
            "errors_per_10min": errors_per_10min,
            "oral_written_ratio": row["oral_written_ratio"],
        },
        "sentence_patterns": json.loads(row.get("sentence_patterns") or "[]"),
        "stage_assessment": json.loads(row.get("stage_assessment") or "{}"),
        "skills": skills,
        "modules": modules,
        "performance": {
            "dimensions": dims,
            "highlights_good": good,
            "highlights_warn": warn,
            "notes": notes,
            "teacher_feedback_pos": fb_pos,
            "teacher_feedback_neg": fb_neg,
            "teacher_feedback_neutral": fb_neu,
            "summary": row["summary"],
        },
    }

    if row["version_note"]:
        result["version_note"] = row["version_note"]
    if row["mouse_working"] == 0:
        result["metrics"]["mouse_working"] = False

    return result


def load_all_lessons(conn):
    ids = [r[0] for r in conn.execute("SELECT lesson_id FROM lessons ORDER BY lesson_id")]
    return [load_lesson(conn, lid) for lid in ids]
