#!/usr/bin/env python3
"""Generate a Markdown stage report from nova.db and save to reports/."""
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import db

ROOT = Path(__file__).parent.parent
REPORTS_DIR = ROOT / "reports"


def bar(pct, width=20):
    filled = round(pct / 100 * width)
    return "█" * filled + "░" * (width - filled)


def trend_arrow(vals):
    clean = [v for v in vals if v is not None]
    if len(clean) < 2:
        return "—"
    if clean[-1] > clean[-2]:
        return "↑"
    if clean[-1] < clean[-2]:
        return "↓"
    return "→"


def main():
    if not db.DB_PATH.exists():
        print("nova.db not found. Run scripts/import_lesson.py first.")
        sys.exit(1)

    conn = db.connect()
    lessons = db.load_all_lessons(conn)
    conn.close()

    if not lessons:
        print("No lessons in DB.")
        sys.exit(1)

    n = len(lessons)
    today = date.today().isoformat()
    lines = []

    def h(level, text):
        lines.append(f"\n{'#' * level} {text}\n")

    def p(text=""):
        lines.append(text)

    # ── Header ───────────────────────────────────────────────────────────────
    lines.append(f"# Nova 英语课阶段报告")
    p(f"生成时间：{today} · 已记录 {n} 课次 · 授课教师 Ashley")
    p()

    # ── Overview table ────────────────────────────────────────────────────────
    h(2, "课次总览")
    p("| 课次 | 日期 | 时长 | 跟读均值 | ≥30s停滞 | 错误次数 | 代表书写 |")
    p("|------|------|------|---------|---------|---------|---------|")
    for d in lessons:
        m = d["metrics"]
        rl = m["repeat_latency"]
        slow = next((t for t in m["writing_tasks"] if t["rating"] == "slow"), None)
        writing_cell = f"{slow['name']}={slow['seconds']}s" if slow else "—"
        flag = "★" if m.get("mouse_working") is False else ""
        p(f"| L{d['lesson']} | {d['date']} | {d['duration_min']}m"
          f" | {rl['mean']}s (n={rl['n']})"
          f" | {m['gaps_30s_count']}次{flag}"
          f" | {m['errors_count']}次"
          f" | {writing_cell} |")
    if any(not d["metrics"].get("mouse_working", True) for d in lessons):
        p()
        p("★ 含鼠标故障课次，停滞数不完全反映专注度")

    # ── Key metrics trend ─────────────────────────────────────────────────────
    h(2, "核心指标趋势")
    latencies = [d["metrics"]["repeat_latency"]["mean"] for d in lessons]
    gaps      = [d["metrics"]["gaps_30s_count"] for d in lessons]
    errors    = [d["metrics"]["errors_count"] for d in lessons]

    p(f"- **跟读延迟** {' → '.join(str(v)+'s' for v in latencies)}  {trend_arrow(latencies)}")
    p(f"- **≥30s停滞** {' → '.join(str(v)+'次' for v in gaps)}  {trend_arrow(gaps)}")
    p(f"- **朗读错误** {' → '.join(str(v)+'次' for v in errors)}  {trend_arrow(errors)}")

    # ── Skill progress ────────────────────────────────────────────────────────
    h(2, "技能掌握度")
    all_skills = {}
    for d in lessons:
        for sk in d["skills"]:
            all_skills.setdefault(sk["name"], {})[d["lesson"]] = sk["pct"]

    p("| 技能 | " + " | ".join(f"L{d['lesson']}" for d in lessons) + " | 趋势 |")
    p("|------|" + "------|" * n + "------|")
    for name, vals_by_lesson in sorted(all_skills.items()):
        vals = [vals_by_lesson.get(d["lesson"]) for d in lessons]
        cells = [(f"{v}% {bar(v, 8)}" if v is not None else "—") for v in vals]
        arrow = trend_arrow(vals)
        p(f"| {name} | " + " | ".join(cells) + f" | {arrow} |")

    # ── Per-lesson detail ─────────────────────────────────────────────────────
    h(2, "各课详细记录")
    for d in lessons:
        m = d["metrics"]
        rl = m["repeat_latency"]
        perf = d["performance"]
        h(3, f"第 {d['lesson']} 课 — {d['date']} ({d['duration_min']}min)")

        if d.get("version_note"):
            p(f"> {d['version_note']}")
            p()

        # latency samples
        h(4, "跟读反应延迟")
        p(f"平均 **{rl['mean']}s**，最长 {rl['max']}s，共 {rl['n']} 次采样")
        p()
        p("| 场景 | 时间码 | 延迟 |")
        p("|------|--------|------|")
        for s in rl["samples"]:
            p(f"| {s['scene']} | {s['ts']} | {s['latency']}s |")

        # writing tasks
        h(4, "任务耗时")
        p("| 任务 | 类型 | 时间码 | 用时 | 评级 | 备注 |")
        p("|------|------|--------|------|------|------|")
        for t in m["writing_tasks"]:
            note = t.get("note", "")
            p(f"| {t['name']} | {t['type']} | {t['ts']} | {t['seconds']}s | {t['rating']} | {note} |")

        # attention gaps
        h(4, "注意力停滞")
        p("| 时段 | 时间码 | 时长 | 类型 | 标记 |")
        p("|------|--------|------|------|------|")
        for g in m["attention_gaps"]:
            flag = g.get("flag", "")
            note = g.get("note", "")
            label = f"{flag} {note}".strip()
            p(f"| {g['scene']} | {g['ts']} | {g['seconds']}s | {g['type']} | {label} |")
        p(f"\n≥30s 停滞共 **{m['gaps_30s_count']}** 次")

        # error corrections
        h(4, "错误纠正")
        p("| 错误 | 时间码 | 纠正耗时 | 提示方式 |")
        p("|------|--------|---------|---------|")
        for e in m["error_corrections"]:
            p(f"| {e['error']} | {e['ts']} | {e['seconds']}s | {e['prompt_type']} |")

        # performance
        h(4, "课堂表现评分")
        p("| 维度 | 评分 | 说明 |")
        p("|------|------|------|")
        for dim in perf["dimensions"]:
            blocks = "■" * int(dim["score"]) + ("▪" if dim["score"] % 1 >= 0.4 else "") + \
                     "□" * (5 - int(dim["score"]) - (1 if dim["score"] % 1 >= 0.4 else 0))
            p(f"| {dim['label']} | {blocks} {dim['score']}/5 | {dim.get('note', '')} |")

        if perf["highlights_good"]:
            p()
            p("**亮点：**")
            for h_text in perf["highlights_good"]:
                p(f"- ✓ {h_text}")
        if perf["highlights_warn"]:
            p()
            p("**待改进：**")
            for h_text in perf["highlights_warn"]:
                p(f"- △ {h_text}")

        if perf.get("summary"):
            p()
            p(f"> {perf['summary']}")

    # ── Stage summary ─────────────────────────────────────────────────────────
    h(2, "阶段综合评估")
    h(3, "已稳定掌握")
    p("- 口语跟读延迟持续维持 0.8s 级别，听觉复述通道扎实")
    p("- 纠错接受速度稳定（1–3s），自我监控意识初步建立")
    p("- 新词汇即时吸收能力强")

    h(3, "持续待加强")
    p("- 长/短元音辨别（Long O vs Short O）规则感不稳固")
    p("- 近音词形-音对应（cow/car 混淆）")
    p("- 书面词形记忆（L1: has=105s）")
    p("- WH- 疑问句语序")

    # ── Footer ────────────────────────────────────────────────────────────────
    p()
    p("---")
    p(f"*数据来源：nova.db · 基于 {n} 课时间码量化数据 · 自动生成*")

    # ── Write file ────────────────────────────────────────────────────────────
    REPORTS_DIR.mkdir(exist_ok=True)
    out = REPORTS_DIR / f"report_{today}.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Report saved → {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
