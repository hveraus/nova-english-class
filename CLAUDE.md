# Nova English Class — 项目说明

## 项目结构
```
Nova English Class/
├── CLAUDE.md              ← 本文件，每次启动自动读取
├── nova_dashboard.html    ← 静态看板，由 build_dashboard.py 生成，勿手动编辑
├── nova.db                ← SQLite 数据库，所有课次数据的唯一来源
├── data/
│   ├── lesson_01.json     ← 原始 JSON 档案（备份用，不直接读取）
│   ├── lesson_02.json
│   └── lesson_0N.json
├── scripts/
│   ├── db.py              ← DB 公共函数（schema、insert、query）
│   ├── import_lesson.py   ← 批量导入 data/*.json → nova.db
│   ├── add_lesson.py      ← 添加单节课 + 自动重建看板
│   ├── build_dashboard.py ← 从 nova.db 重建 nova_dashboard.html
│   └── export_report.py   ← 生成 Markdown 阶段报告
└── reports/
    └── report_YYYY-MM-DD.md
```

---

## 每次新课的完整流程

```
新课转录文件 → 提取指标 → data/lesson_0N.json
             → python scripts/add_lesson.py data/lesson_0N.json
                 ├── 写入 nova.db
                 └── python scripts/build_dashboard.py
                         → nova_dashboard.html 自动更新
```

具体步骤：

1. **读取转录文件**（.md 格式，含时间码，由用户上传）
2. **提取量化指标**，生成 `data/lesson_0N.json`（N 为两位数）
   - 包含 `sentence_patterns`、`vocab`（每个 module）等字段
   - **必须包含 `stage_assessment`**（见下方说明），这是阶段综合评估的数据来源
3. **运行**：`python scripts/add_lesson.py data/lesson_0N.json`
4. 打开 `nova_dashboard.html` 确认新课数据正常显示
5. （可选）运行 `python scripts/export_report.py` 生成最新 Markdown 报告

**不再需要**：手动备份 HTML、手动追加 JSON、手动更新评估文字。

### `stage_assessment` 字段（必填，每新课更新）

整体进展页的「已稳定掌握 / 持续待加强 / 阶段综合评估」三个模块，**始终从最新课的 `stage_assessment` 字段读取**。每次新课时必须在该课 JSON 中写入最新评估，覆盖旧评估。

```json
"stage_assessment": {
  "mastered": [
    {"title": "口语跟读延迟", "detail": "三课均维持 0.8s 级别，听觉复述通道稳健"},
    ...
  ],
  "needs_work": [
    {"title": "绘本解码能力", "detail": "L3 故事朗读大量错词，篇章层解码是当前最大短板"},
    ...
  ],
  "summary": "跨课综合评估段落，100–200字，对比历史数据，指出稳定项和待改进项。"
}
```

---

## 脚本说明

### `scripts/add_lesson.py`
```
python scripts/add_lesson.py <path/to/lesson_0N.json>
```
- 把 JSON 复制到 `data/`（如果来源不在 data/）
- 插入 `nova.db`（已存在则跳过）
- 自动调用 `build_dashboard.py` 重建看板

### `scripts/import_lesson.py`
```
python scripts/import_lesson.py
```
- 批量扫描 `data/lesson_*.json`，逐一导入 `nova.db`
- 已存在的课次跳过，不重复插入

### `scripts/build_dashboard.py`
```
python scripts/build_dashboard.py
```
- 从 `nova.db` 读取所有课次，重建 `nova_dashboard.html`
- 替换 HTML 内的 `<script id="all-lessons">` 数据块

### `scripts/export_report.py`
```
python scripts/export_report.py
```
- 生成 `reports/report_YYYY-MM-DD.md`，包含课次总览、技能趋势、各课详细数据

---

## 数据库表结构

主表 `lessons`（每课一行）：

| 字段 | 类型 | 说明 |
|------|------|------|
| lesson_id | INTEGER PK | 课次编号 |
| date | TEXT | YYYY-MM-DD |
| duration_min | INTEGER | 有效分钟数 |
| time_range | TEXT | 有效时间段 |
| teacher | TEXT | 授课教师 |
| source_file | TEXT | 原始转录文件名 |
| version_note | TEXT | 说话人修正说明 |
| gaps_30s_count | INTEGER | ≥30s 停滞次数 |
| errors_count | INTEGER | 朗读错误次数 |
| oral_written_ratio | TEXT | 口语/书写比，鼠标故障时 NULL |
| mouse_working | INTEGER | 1=正常，0=故障 |
| latency_mean | REAL | 跟读延迟均值 |
| latency_max | INTEGER | 跟读延迟最大值 |
| latency_n | INTEGER | 跟读采样次数 |
| summary | TEXT | 课堂总结（100–150字） |

明细表（均含 `lesson_id` 外键）：
- `repeat_latency_samples`：scene, ts, latency
- `writing_tasks`：name, type, ts, seconds, rating, note
- `attention_gaps`：scene, ts, seconds, type, flag, note
- `error_corrections`：error, ts, seconds, prompt_type, note
- `skills`：name, pct
- `modules`：position, color, name, sub
- `performance_dimensions`：label, score, note
- `performance_highlights`：type(good/warn/note), text
- `teacher_feedback`：type(pos/neg/neutral), text

---

## 关键人物
- 学生：**Nova**，线上一对一英语课
- 老师：**Ashley** = Speaker 1
- **Nova = Speaker 2**（除非上下文明显是老师在说）
- Speaker 3 / 4：转录误分，忽略

---

## 转录文件常见问题（必读）

### 说话人标注错误
- 课程末段（老师说再见、布置作业、关屏前后）的话容易被误标为 Nova，需核查排除
- 典型误标内容："Make sure you practice"、"I will see you next time"、"Good job today"、"Give yourself a high five" 等——这些一定是 Ashley 说的
- Speaker 3 / 4 通常是背景人声或转录系统误分，不计入分析

### 课后录音残留
- 录音可能在课程结束后继续（老师关屏前后的背景声）
- 判断方式：Ashley 说"Bye-bye / See you / Thank you Nova"之后的内容全部排除
- 第2课示例：25:45 之后为非课程内容，已排除

### 其他语言干扰
- Nova 有时会说葡萄牙语或中文（自言自语、旁白）
- Ashley 常用葡萄牙语辅助讲解，属正常双语教学
- 作为**行为信号**记录（如书写困难时自语），不计入英语错误统计
- 示例：第1课 11:46 "爸爸又写不出来了，手也写不出来" → 记录为书写困难的佐证
- **转录语言误识别**：转录引擎可能把英/葡语音误配到其他语言模型，产出德语等无关语言文本（如 L8 42:50 "Wir schreiben…"）。这是转录伪影，不是教师实际用语，在 version_note 中注明即可

### 无说话人标注的转录（L7 起常见）
- 部分转录只有时间码没有 speaker 标注，说话人靠内容推断（谁下指令=Ashley，谁跟读=Nova），在 version_note 中说明推断依据
- 影响：跟读延迟只能取"明确可辨认的示范→跟读"片段，n 通常降到 5–6（标低置信）；停滞的 type 归因是推断，置信度低于有标注课次
- 大段合并 blob（一个时间段塞多轮对话，如 L8 01:00–01:38）内部的延迟/错误**不可测量**，明显影响覆盖率时在 version_note 中注明

---

## 量化指标提取规则

### ① 跟读反应延迟
- 定义：老师说完一个词/句 → Nova 开始复述的时间差（秒）
- 时间码精度为 1s，所以延迟只会是 0s 或 1s 或 2s 等整数
- 0s = 同一秒内开口（最快），1s = 正常，≥3s = 偏慢，需单独标注
- 每课采样 ≥5 次，尽量 10+ 次
- **只计跟读**：老师示范 → Nova 复述。排除 Nova 独立朗读段
- **报告口径（2026-07 修订）**：
  - 主报告**分布**（如 `0s×3 · 1s×7 · 2s×1`），均值仅作参考——1s 精度下，均值小数位差异（0.7 vs 1.0）属噪声，**不得用于跨课趋势结论**
  - n < 8 的课次标注 `low_confidence`，评估文字中不引用其均值
  - 跨课只看粗信号：是否出现 ≥3s 异常样本、分布是否整体后移
  - 分布和低置信标记由 `db.py` 加载时自动从 samples 计算，无需手工写入 JSON

### ② 书写/任务耗时
- 定义：老师下达书写指令结束 → 老师确认完成（"Good job" / "There you go" / 移入下一题）
- 任务类型：`fill-blank` / `whole-word` / `spelling-repeat` / `oral-identification` / `read-page`
- 鼠标故障时：在 metrics 层级记录 `"mouse_working": false`，任务类型加 `oral-` 前缀

### ③ 注意力中断 / 长时沉默
- 扫描相邻 turn 之间的时间间隔（turn_B.start - turn_A.end）
- ≥10s 记录进 attention_gaps
- ≥30s 标注 `"flag": "alert"`
- 原因类型：`writing` / `mouse-task` / `mouse-failure` / `comprehension` / `page-turn` / `teacher-explanation` / `concept-confusion` / `reading` / `technical`
- 鼠标故障导致的停滞在 note 中注明"★鼠标故障"，区别于专注度问题
- **任务内 / 任务外拆分（2026-07 修订）**：
  - **任务内**（`writing` / `mouse-task` / `mouse-failure` / `page-turn` / `reading` / `read-page` / `technical`）：老师布置了任务，停滞是预期的任务耗时，与 writing_tasks 本质重复，**不是专注度信号**
  - **任务外**（`comprehension` / `concept-confusion` / `teacher-explanation` 及其他）：无任务却沉默，才是真正的注意力/理解信号
  - 跨课比较**只用任务外次数**；总 gaps_30s_count 主要反映课程形式（书写任务多少），不反映专注度
  - 拆分由 `db.py` 按 type 自动计算（`gaps_task_count` / `gaps_offtask_count`），提取时只需把 type 标注准确

### ④ 纠错耗时
- 定义：Nova 出错的时间戳 → Nova 成功复述正确形式完毕
- 提示类型：`modeled`（老师示范）/ `direct`（直接给词）/ `hint`（暗示）/ `two-choice`（二选一）/ `explanation`（解释概念）/ `modeled-repeat`（示范后再次出错重示范）

### ⑤ 错误率归一化（2026-07 修订）
- errors_count 与课长强相关，跨课比较必须用归一化口径：**errors_per_10min = errors_count / duration_min × 10**（保留 1 位小数）
- 由 `db.py` 加载时自动计算，评估文字引用错误趋势时用归一化值，不用原始次数

---

## 技能列表（固定，跨课追踪）

每课的 `skills` 数组尽量从以下列表中选取，名称保持一致，没有练到的课次**不填该项**（不要填 null，直接省略）：

| 技能名称 | 说明 |
|---------|------|
| 长元音 Long I | nine kite five dime bike |
| 长元音 Long O | nose rope bone home rose |
| 长/短元音辨别 | 长O vs 短O 等对比辨别 |
| 绘本朗读 | 独立完成句子朗读 |
| 视觉词拼写 | sight words 书写 |
| 形容词辨别 | 近义词/语义区分 |
| WH- 问句句型 | Where/What 等问句语序 |
| 词汇量（农场/自然） | 农场动物、植物等主题 |
| food source 词汇 | wheat/fruit/cow 等食物来源 |
| can/cannot 句型 | 情态动词句型 |

如果本课出现以上列表没有的新技能，可以新增，但名称要简洁、可复用。

**pct 打分口径**：pct 是主观粗估，不是精确测量。以 5 为步长（60/65/70…），依据"首次尝试正确率 + 需要提示的程度"两个锚点估计；评估文字中不要引用个位数差异（如 65% vs 68%）做趋势结论，只在 ≥10 个百分点变化时才视为有意义。

---

## 基准数据（历史记录，2026-07 新口径重算）

| 课次 | 日期 | 时长 | 跟读延迟分布 | 停滞(任务内/外) | 错误率 (/10min) |
|------|------|------|-------------|----------------|-----------------|
| L1 | 2026-05-17 | 45min | 0s×2 1s×9 (n=11) | 1 / 1 | 1.1 |
| L2 | 2026-05-19 | 25min | 0s×3 1s×8 2s×1 (n=12) | 1 / 4 | 1.6 |
| L3 | 2026-05-24 | 49min | 0s×5 1s×5 4s×1 (n=11) | 3 / 1 | 0.8 |
| L4 | 2026-06-07 | 47min | 0s×6 1s×6 (n=12) | 3 / 0 | 1.1 |
| L5 | 2026-06-09 | 28min | 0s×2 1s×7 2s×2 4s×1 (n=12) | 8 / 1 | 1.8 |
| L6 | 2026-06-14 | 49min | 0s×1 1s×3 2s×1 (n=5★) | 15 / 2 | 1.8 |
| L7 | 2026-07-07 | 26min | 0s×3 1s×8 (n=11) | 4 / 0 | 3.1 |
| L8 | 2026-07-12 | 44min | 0s×1 1s×4 2s×1 (n=6★) | 10 / 0 | 1.1 |
| L9 | 2026-07-14 | 25min | 0s×2 1s×7 2s×1 3s×1 5s×1 (n=12) | 8 / 0 | 3.2 |

★ n<8 低置信（书写为主的课次，可辨认跟读片段少）

新口径下的跨课结论：任务外停滞八课合计仅 9 次（L2 占 4 次），专注度整体良好；
任务内停滞随书写任务量波动，属课程形式差异。L7 错误率 3.1 为八课最高（短课+高强度朗读）。

---

## JSON Schema 说明
参照 `data/lesson_01.json`，关键字段：

```
lesson            课次编号（整数）
date              YYYY-MM-DD
duration_min      有效课程分钟数（排除课后残留）
time_range        有效时间段字符串
source_file       原始转录文件名
version_note      说话人修正说明（如有）

metrics
  repeat_latency.mean/max/n/samples
  writing_tasks[].rating    fast / mid / slow
  attention_gaps[].flag     "alert" 表示≥30s
  error_corrections[].prompt_type
  gaps_30s_count            整数
  errors_count              整数
  oral_written_ratio        字符串如"1:6"，鼠标故障时填 null
  mouse_working             布尔，默认省略（true），故障时填 false

派生字段（勿写入 JSON，db.py 加载时自动计算）：
  repeat_latency.dist / low_confidence
  gaps_task_count / gaps_offtask_count
  errors_per_10min

skills[].name     从固定技能列表选取
skills[].pct      0–100 整数

performance
  dimensions[].score        0–5，支持0.5步长
  highlights_good/warn      具体行为+时间码，不要泛泛而谈
  summary                   100–150字，对比上节课
```

**注意**：JSON 字符串中如有直引号 `"` 需转义为 `\"`，否则 JSON 解析失败。

---

## 文件命名规范
- 转录文件：用户上传的文件名不固定，以实际为准
- JSON 数据文件：`lesson_01.json` / `lesson_02.json` ... 两位数补零
- 看板：`nova_dashboard.html`，唯一入口，不要创建多个版本
- 报告：`reports/report_YYYY-MM-DD.md`

---

## 注意事项
- `nova_dashboard.html` 由 `build_dashboard.py` 生成，**不要手动编辑 `<script id="all-lessons">` 块**
- `nova.db` 是数据唯一来源，`data/*.json` 仅作备份档案
- 所有脚本用 Python 3 标准库，无需安装额外依赖
