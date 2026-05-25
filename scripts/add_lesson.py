#!/usr/bin/env python3
"""Add a new lesson JSON to nova.db and rebuild nova_dashboard.html.

Usage:
    python scripts/add_lesson.py path/to/lesson_03.json
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import db

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/add_lesson.py <path/to/lesson_0N.json>")
        sys.exit(1)

    src = Path(sys.argv[1]).resolve()
    if not src.exists():
        print(f"File not found: {src}")
        sys.exit(1)

    with open(src, encoding="utf-8") as f:
        data = json.load(f)

    lesson_id = data["lesson"]
    dest = DATA_DIR / f"lesson_{lesson_id:02d}.json"

    if src != dest:
        shutil.copy2(src, dest)
        print(f"Copied → {dest.relative_to(ROOT)}")

    conn = db.connect()
    db.init_schema(conn)
    ok = db.insert_lesson(conn, data)
    conn.close()

    if ok:
        print(f"✓ L{lesson_id} ({data['date']}) inserted into nova.db")
    else:
        print(f"L{lesson_id} already existed in DB — no changes.")
        sys.exit(0)

    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "build_dashboard.py")],
        check=True,
    )


if __name__ == "__main__":
    main()
