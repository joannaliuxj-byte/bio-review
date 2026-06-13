import json
import re
from pathlib import Path

with open("biology_data.txt", encoding="utf-8") as f:
    raw = f.read()

# ── 1. 分割题目区 / 解析区 ──────────────────────────────────────────────────
# 文本结构：
#   标题行
#   一.选择题(共60小题)   ← 第一次出现
#   60道题目
#   一.选择题(共60小题)   ← 第二次出现（答案表 + 解析）
#     1.【答案】C ...
#
# 用第二次出现的 "一.选择题" 作为分割点

parts = re.split(r'一\.选择题[（(]共60\s*小题[）)]', raw, maxsplit=2)
# parts[0] = 标题前文字 (可忽略)
# parts[1] = 60道题目区
# parts[2] = 答案表 + 解析区
question_block = parts[1] if len(parts) >= 2 else ""
analysis_block  = parts[2] if len(parts) >= 3 else ""

# ── 2. 解析 解析区 → {id: {answer, analysis}} ───────────────────────────────
# 每块以 "N.【答案】X" 开头
analysis_map = {}
for m in re.finditer(
    r'(\d{1,2})\.【答案】([A-D])\s*\n([\s\S]*?)(?=\n\d{1,2}\.【答案】|$)',
    analysis_block
):
    qid     = int(m.group(1))
    answer  = m.group(2)
    content = m.group(3).strip().replace('\n', ' ')
    analysis_map[qid] = {"answer": answer, "analysis": content}

# ── 3. 解析 题目区 → 题目列表 ─────────────────────────────────────────────
# 每道题以行首的 "N." 开头（N 为1-60）
chunks = re.split(r'\n(?=\d{1,2}\.(?!\d))', question_block)

IMAGE_KEYWORDS = re.compile(
    r'如图|图一|图二|图甲|图乙|图丙|示意图|下图|上图|右图|左图|图\d|如表'
)

questions = []
for chunk in chunks:
    chunk = chunk.strip()
    header = re.match(r'^(\d{1,2})\.', chunk)
    if not header:
        continue
    qid = int(header.group(1))
    if not 1 <= qid <= 60:
        continue

    lines = [l.strip() for l in chunk.splitlines() if l.strip()]

    # 找第一个选项行的位置
    opt_start = next(
        (i for i, l in enumerate(lines) if re.match(r'^[A-D][\.．]', l)),
        None
    )

    # 题干（选项行之前的所有行拼接）
    q_lines = lines[:opt_start] if opt_start is not None else lines
    question_text = ' '.join(q_lines)
    question_text = re.sub(r'^\d{1,2}\.', '', question_text).strip()

    # 选项
    options = {}
    if opt_start is not None:
        cur_key = None
        for line in lines[opt_start:]:
            m = re.match(r'^([A-D])[\.．](.*)', line)
            if m:
                cur_key = m.group(1)
                options[cur_key] = m.group(2).strip()
            elif cur_key:
                options[cur_key] += ' ' + line

    info = analysis_map.get(qid, {})
    answer   = info.get("answer", "")
    analysis = info.get("analysis", "")

    # 图片判断：本地文件存在时填写路径
    img_path = Path(f"images/q{qid}.png")
    image = f"images/q{qid}.png" if img_path.exists() else ""

    questions.append({
        "id": qid,
        "question": question_text,
        "options": [
            {"key": k, "text": options.get(k, "")} for k in "ABCD"
        ],
        "answer": answer,
        "analysis": analysis,
        "image": image,
    })

questions.sort(key=lambda x: x["id"])

with open("questions.json", "w", encoding="utf-8") as f:
    json.dump(questions, f, ensure_ascii=False, indent=2)

print(f"Done: {len(questions)} questions → questions.json")

no_answer   = [q["id"] for q in questions if not q["answer"]]
no_analysis = [q["id"] for q in questions if not q["analysis"]]
no_opts     = [q["id"] for q in questions if any(o["text"] == "" for o in q["options"])]
if no_answer:   print(f"  ⚠ Missing answer:   {no_answer}")
if no_analysis: print(f"  ⚠ Missing analysis: {no_analysis}")
if no_opts:     print(f"  ⚠ Empty options:    {no_opts}")
