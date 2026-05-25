#!/usr/bin/env python3
"""Bulk-import all data/lesson_*.json files into nova.db."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import db

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"


def main():
    conn = db.connect()
    db.init_schema(conn)

    json_files = sorted(DATA_DIR.glob("lesson_*.json"))
    if not json_files:
        print("No lesson JSON files found in data/")
        conn.close()
        return

    imported = 0
    for f in json_files:
        print(f"Importing {f.name} …")
        with open(f, encoding="utf-8") as fp:
            data = json.load(fp)
        if db.insert_lesson(conn, data):
            print(f"  ✓ L{data['lesson']} ({data['date']}) imported.")
            imported += 1

    conn.close()
    print(f"\nDone. {imported} new lesson(s) imported.")


if __name__ == "__main__":
    main()
