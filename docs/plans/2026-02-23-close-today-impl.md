# /close-today Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the `/close-today` Claude Code skill — end-of-day review that auto-checks completed items, generates retrospective stats, and provides AI coaching feedback from 3 perspectives.

**Architecture:** Pure Claude Code skill (markdown instructions + output templates). No code — Claude follows SKILL.md instructions at runtime. Reuses the same MCP tools as `/today` plus Timing Web API via `curl`.

**Tech Stack:** Claude Code skills (SKILL.md), MCP tools (Google Calendar, Linear, Slack, Notion), GitHub CLI (`gh`), Timing Web API, Obsidian vault.

---

### Task 1: Create output template reference

**Files:**
- Create: `skills/close-today/references/output-template.md`

**Step 1: Create directory structure**

```bash
mkdir -p ~/today-yolo/skills/close-today/references
```

**Step 2: Write the output template file**

Write `skills/close-today/references/output-template.md` with these two sections:

**Section 1 — Terminal Output Template:**

```
🌙 今日回顾 — {{DATE}} ({{DAY}})
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ 已完成 ({{done}}/{{total}})
  ✓ {{item}} (→ {{completion reason}})
  ✓ [自动] {{item}} (→ {{reason}})
  ✓ [手动] {{item}}

❓ 需要确认 ({{count}})
  ? {{item}} — {{reason}}
    → 标记完成？ [y/n]

❌ 未完成 → 明日遗留 ({{count}})
  ☐ {{item}} — {{reason}}

⏱️ 时间分析 (Timing)
  {{category}}:  {{hours}}h  {{bar}}  {{percent}}%

📊 统计
  计划完成率: {{percent}}% ({{done}}/{{total}})
  番茄消耗: ~{{actual}}🍅 / 计划 {{planned}}🍅
  未完成原因:
    ⏰ 估时不足: {{count}} 项
    🚧 被阻塞:  {{count}} 项
    📥 临时插入: {{count}} 项

🧠 AI 教练反馈

  👔 Career Coach
  {{2-4 sentences}}

  ⚡ 效率教练
  {{2-4 sentences}}

  🌱 Positive Intelligence
  {{2-4 sentences}}
```

Rendering rules:
- Omit sections with zero items
- Day names: Chinese weekday (周一–周日)
- Language: Chinese + English proper nouns
- Progress bar uses `█` (filled) and `░` (empty), 10 chars wide
- Completion reasons in parentheses: `(→ Done)`, `(→ Merged)`, `(已过)`
- `[自动]` = auto-checked by high-confidence match; `[手动]` = was already `[x]` in daily note
- `❓ 需要确认` items are interactive — wait for user response before proceeding

**Section 2 — Obsidian Daily Note Template:**

Target path: `/Users/mia/Documents/Mia的Sunny号/{{YYYY-MM-DD}}.md`

Write behavior:
- If `## 今日回顾` does not exist → append at end of file
- If `## 今日回顾` exists → replace from `## 今日回顾` to next `## ` or EOF

Format:
```markdown
## 今日回顾

### ✅ 已完成 ({{done}}/{{total}})
- [x] {{item}} (→ {{reason}}) 🍅 {{estimate}}

### ❌ 未完成 → 明日遗留
- [ ] {{item}} — {{reason}} 🍅 {{estimate}}

### ⏱️ 时间分析
| 类别 | 时长 | 占比 |
|------|------|------|
| {{category}} | {{hours}}h | {{percent}}% |

### 📊 统计
- 计划完成率: {{percent}}% ({{done}}/{{total}})
- 番茄消耗: ~{{actual}}🍅 / 计划 {{planned}}🍅

### 🧠 AI 教练反馈

**👔 Career Coach**
{{feedback}}

**⚡ 效率教练**
{{feedback}}

**🌱 Positive Intelligence**
{{feedback}}

> 完成率: {{percent}}% | 实际: ~{{actual}}🍅 / 计划 {{planned}}🍅
```

Formatting rules:
- Subsection headers use `###`
- Completed items use `- [x]`, uncompleted use `- [ ]`
- Each item annotated with 🍅 estimate (preserved from original plan)
- Omit sections with zero items

**Step 3: Commit**

```bash
cd ~/today-yolo
git add skills/close-today/references/output-template.md
git commit -m "feat: add close-today output template"
```

---

### Task 2: Create SKILL.md (core skill definition)

**Files:**
- Create: `skills/close-today/SKILL.md`

**Step 1: Write SKILL.md**

Write `skills/close-today/SKILL.md` with YAML frontmatter and 7 steps. The full content:

**YAML frontmatter:**
```yaml
---
name: close-today
description: 今日回顾。读取今日计划，拉取 7 个数据源最新状态，自动勾选已完成项，生成回顾统计和 AI 教练反馈，输出到终端 + Obsidian daily note。每天下班前运行。
---
```

**Body — 7 steps:**

**Step 1: Read today's plan**
- Determine today's date in `YYYY-MM-DD`
- Read `/Users/mia/Documents/Mia的Sunny号/{{YYYY-MM-DD}}.md`
- Parse the `## 今日计划` section
- Extract every item: checkbox state (`[ ]` or `[x]`), text, 🍅 estimate, section category
- If `## 今日计划` does not exist, print `❌ 今天没有计划。请先运行 /today` and stop
- Identify item types by pattern matching:
  - `MLS-\d+` → Linear issue
  - `PR #\d+` or `#\d+` → GitHub PR
  - `HH:MM-HH:MM` at start → Calendar event
  - Other → generic item

**Step 2: Fetch latest status from 7 data sources (parallel)**

Run all sources in parallel:

Source 1 — Google Calendar: same as `/today` (`mcp__google-drive__calendar_events_list`)
Source 2 — Linear: same as `/today` (two calls: `state: "started"` + `state: "unstarted"`)
Source 3 — GitHub: same as `/today` (`gh pr list` + `gh api notifications`)
Source 4 — Slack: same as `/today` (`mcp__slack__conversations_history`, 48h window)
Source 5 — Gmail: same as `/today` (check if MCP available, skip if not)
Source 6 — Notion: same as `/today` (`mcp__notion__notion-search`)
Source 7 — Timing: Use the `timingapp-timeline-loader` skill to fetch today's time data from local SQLite:
```bash
python3 ~/.claude/skills/timingapp-timeline-loader/generate_timeline.py --date {{YYYY-MM-DD}} --summary --output -
```
- If the script fails (Timing not installed, DB not found), print `⚠️ Timing 数据不可用，跳过时间分析。` and continue
- The JSON output includes `total_hours`, `by_project` (hours per project), `work_sessions` (time ranges with project/app breakdown)
- Use `by_project` for the time analysis section, `work_sessions` for detailed session breakdown

**Step 3: Match items and determine completion status**

For each unchecked `- [ ]` item in the plan, match against data source results:

| Item type | High confidence → auto-check | Medium confidence → ask user |
|-----------|------------------------------|------------------------------|
| Calendar event | Current time > event end time | — |
| Linear `MLS-xxx` | Issue status is Done or Cancelled | Status still In Progress but has activity today |
| GitHub `PR #xxx` | PR is merged, or I submitted a review | PR open with new comments |
| Slack @mention | I replied in the thread after the mention | Thread has new messages, I haven't replied |
| Gmail | — | Cannot determine (always ask) |
| Notion task | Status is Done/Complete | — |
| Generic (no identifier) | Already `[x]` in daily note | Cannot auto-determine (always ask) |

Items already checked `[x]` → mark as `[手动]` completed, skip matching.

**Step 4: Auto-check high confidence items in daily note**

For each high-confidence completed item:
- Use the Edit tool to change `- [ ] {{item text}}` → `- [x] {{item text}}` in the daily note file
- Track which items were auto-checked for the report

**Step 5: Terminal output — completion status + confirmation**

Print to terminal:
1. `✅ 已完成` section — all completed items (auto + manual)
2. `❓ 需要确认` section — medium-confidence items
3. `❌ 未完成 → 明日遗留` section — clearly uncompleted items

For `❓ 需要确认` items, use `AskUserQuestion` tool to let user confirm each item. After confirmation, update the daily note accordingly.

**Step 6: Generate retrospective statistics**

Calculate:
- **完成率**: completed / total items (percentage)
- **番茄消耗**: sum of 🍅 estimates for completed items vs total planned
- **未完成原因分类**: for each uncompleted item, classify as:
  - `⏰ 估时不足` — item was started but not finished (e.g., Linear still In Progress)
  - `🚧 被阻塞` — item was blocked by external dependency
  - `📥 临时插入` — item was not in original plan (if any unplanned items appeared)
- **时间分析** (from Timing): actual hours per category with progress bars

**Step 7: Generate AI coaching feedback**

Based on ALL collected data (completion stats, time analysis, what was done, what wasn't), generate feedback from 3 perspectives:

**👔 Career Coach** (2-4 sentences):
- Focus on: skill growth, impact of completed work, career goal alignment
- Reference specific tickets/PRs completed and their significance
- If something was blocked, suggest escalation strategies

**⚡ 效率教练** (2-4 sentences):
- Focus on: time allocation, pomodoro completion rate, work rhythm
- Compare planned vs actual
- Give specific suggestion for tomorrow's scheduling

**🌱 Positive Intelligence** (2-4 sentences):
- Focus on: psychological state, identify saboteur patterns (Judge, Achiever, Controller, etc.)
- Acknowledge progress with empathy
- Suggest a PQ rep (mental fitness exercise)
- Use warm, supportive tone

**Step 8: Terminal output — full retrospective**

Print the complete retrospective following the **Terminal Output Template** in `references/output-template.md`.

**Step 9: Write retrospective to Obsidian**

Append `## 今日回顾` to the daily note following the **Obsidian Daily Note Template** in `references/output-template.md`.

Write behavior:
- If `## 今日回顾` does not exist → append at end of file
- If `## 今日回顾` exists → replace from `## 今日回顾` to next `## ` heading or EOF

**Error handling section:**
- Same as `/today`: single source failure → log briefly, continue with rest
- Timing API not configured → skip time analysis, everything else works
- Gmail not configured → skip silently
- If `## 今日计划` missing → stop with helpful message
- If ALL sources fail → print error, suggest checking MCP config

**Step 2: Commit**

```bash
cd ~/today-yolo
git add skills/close-today/SKILL.md
git commit -m "feat: add close-today SKILL.md"
```

---

### Task 3: Install skill via symlink and test

**Step 1: Create symlink**

```bash
ln -s ~/today-yolo/skills/close-today ~/.claude/skills/close-today
```

Verify:
```bash
ls -la ~/.claude/skills/close-today
```
Expected: symlink pointing to `~/today-yolo/skills/close-today`

**Step 2: Test run**

Run `/close-today` in Claude Code. Verify:
- It reads today's daily note
- It fetches data sources in parallel
- Calendar events past their end time are auto-checked
- Linear issues that are Done are auto-checked
- Medium-confidence items prompt for confirmation
- Timing data shows (or gracefully skips if no API key)
- Full retrospective is printed
- `## 今日回顾` is appended to daily note

**Step 3: Fix any issues found during test**

If any source fails or output format is wrong, edit SKILL.md accordingly.

**Step 4: Commit any fixes**

```bash
cd ~/today-yolo
git add -A
git commit -m "fix: close-today adjustments from test run"
```

---

### Task 4: Verify Timing skill works

**Step 1: Test the timing skill**

```bash
python3 ~/.claude/skills/timingapp-timeline-loader/generate_timeline.py --date 2026-02-23 --summary --output -
```

Expected: JSON with `total_hours`, `by_project`, `work_sessions`.

No API key needed — reads directly from Timing's local SQLite database.

---

### Task 5: Push to GitHub

**Step 1: Push**

```bash
cd ~/today-yolo
git push origin main
```

Verify at: https://github.com/MIAJIA/today-yolo
