#!/usr/bin/env python3
"""Rebuild nova_dashboard.html by replacing its embedded JSON from nova.db."""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import db

ROOT = Path(__file__).parent.parent
DASHBOARD = ROOT / "nova_dashboard.html"


def build():
    if not db.DB_PATH.exists():
        print("nova.db not found. Run scripts/import_lesson.py first.")
        sys.exit(1)

    conn = db.connect()
    lessons = db.load_all_lessons(conn)
    conn.close()

    if not lessons:
        print("No lessons in DB.")
        sys.exit(1)

    json_str = json.dumps(lessons, ensure_ascii=False, indent=2)

    html = DASHBOARD.read_text(encoding="utf-8")
    new_html, n = re.subn(
        r'(<script\s+id="all-lessons"[^>]*>)[\s\S]*?(</script>)',
        f'\\1\n{json_str}\n\\2',
        html,
    )
    if n == 0:
        print("ERROR: could not find <script id=\"all-lessons\"> block in HTML.")
        sys.exit(1)

    DASHBOARD.write_text(new_html, encoding="utf-8")
    print(f"Dashboard rebuilt with {len(lessons)} lesson(s): "
          + ", ".join(f"L{d['lesson']} ({d['date']})" for d in lessons))


if __name__ == "__main__":
    build()
