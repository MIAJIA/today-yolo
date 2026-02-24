---
name: close-today
description: 今日回顾。读取今日计划，拉取 7 个数据源最新状态，自动勾选已完成项，生成回顾统计和 AI 教练反馈，输出到终端 + Obsidian daily note。每天下班前运行。
---

# /close-today

今日回顾。读取今日计划，拉取 7 个数据源最新状态，自动判断完成状态，生成回顾统计和 AI 教练反馈，输出到终端并写入 Obsidian daily note。

## Step 1: Read today's plan

Determine today's date in `YYYY-MM-DD` format.

Read the Obsidian daily note at:

```
/Users/mia/Documents/Mia的Sunny号/{{YYYY-MM-DD}}.md
```

Parse the `## 今日计划` section (from `## 今日计划` to the next `## ` heading or end of file).

Extract every item with:
- **Checkbox state**: `[ ]` (unchecked) or `[x]` (checked)
- **Full item text**
- **🍅 pomodoro estimate** (the number before 🍅)
- **Section category** (📅 固定时间 / 🔥 紧急 / 📋 专注工作 / 📬 待处理 / 🔄 遗留)

If `## 今日计划` section does not exist, print `❌ 今天没有计划。请先运行 /today` and **stop**.

Identify item types by pattern matching:

| Pattern | Item type |
|---------|-----------|
| `MLS-\d+` in text | Linear issue |
| `PR #\d+` or `#\d+` in text | GitHub PR |
| Line starts with time range `HH:MM-HH:MM` | Calendar event |
| Everything else | Generic item |

## Step 2: Fetch latest status from 7 data sources

**Run all sources in parallel** (use parallel tool calls where possible).

### Source 1 — Google Calendar

Use `mcp__google-drive__calendar_events_list` to fetch today's events.

- Parameters: set the date range to today only (start of day to end of day)
- Extract: **start time**, **end time**, **title**

### Source 2 — Linear

Use `mcp__plugin_linear_linear__list_issues` to fetch issues assigned to me.

- Make **two** calls:
  1. `assignee: "me"`, `state: "started"` — captures In Progress and In Review
  2. `assignee: "me"`, `state: "unstarted"` — captures Todo, Ready for Work, Backlog
- Extract: **identifier** (e.g. `MLS-751`), **title**, **status**, **priority**

### Source 3 — GitHub

Run two Bash commands (from `/Users/mia/today-yolo`):

```bash
gh pr list --search "review-requested:@me" --json number,title,url,state,mergedAt
```

```bash
gh api notifications --jq '.[] | select(.reason=="review_requested" or .reason=="mention")'
```

- Also check specific PRs mentioned in the plan: for any `PR #NNN` or `#NNN` found in Step 1, run:
  ```bash
  gh pr view NNN --json state,mergedAt
  ```
- Extract: **PR number**, **title**, **state** (open/merged/closed)

### Source 4 — Slack

Use `mcp__slack__conversations_history` to check channels.

- Focus on **@mentions** and **DMs** from the past 48 hours
- Use the `oldest` parameter set to 48 hours ago (Unix timestamp)
- Extract: **channel name**, **sender**, **whether user has replied in thread**

### Source 5 — Gmail

Check if Gmail MCP tools are available (tools with prefix `mcp__gmail`).

- **If NOT available**: print exactly:
  ```
  ⚠️ Gmail MCP 未配置，跳过邮件。
  ```
- **If available**: fetch unread emails

### Source 6 — Notion

Use `mcp__notion__notion-search` to find tasks assigned to the user.

- Extract: **title**, **status**
- If Notion fails or token expired, log briefly and continue

### Source 7 — Timing

Fetch today's time data from local Timing SQLite database:

```bash
python3 ~/.claude/skills/timingapp-timeline-loader/generate_timeline.py --date {{YYYY-MM-DD}} --summary --output -
```

- If the script fails (Timing not installed, DB not found), print `⚠️ Timing 数据不可用，跳过时间分析。` and continue
- Parse JSON output: `total_hours`, `by_project` (map of project→hours), `work_sessions`

## Step 3: Match items and determine completion status

For each **unchecked** `- [ ]` item in the plan, match against data source results:

| Item type | High confidence → auto-check | Medium confidence → ask user |
|-----------|------------------------------|------------------------------|
| Calendar event | Current time > event end time | — |
| Linear `MLS-xxx` | Issue status is Done or Cancelled | Status still In Progress but has activity today |
| GitHub `PR #xxx` | PR is merged, or I submitted a review | PR open with new comments |
| Slack @mention | I replied in the thread after the mention | Thread has new messages, I haven't replied |
| Gmail | — | Cannot determine (always ask) |
| Notion task | Status is Done/Complete | — |
| Generic (no identifier) | Already `[x]` in daily note | Cannot auto-determine (always ask) |

Items already checked `[x]` in the daily note → mark as `[手动]` completed, no matching needed.

Classify each item into one of three categories:
- **✅ completed** (high confidence auto-check OR already `[x]`)
- **❓ needs confirmation** (medium confidence)
- **❌ not completed** (no evidence of completion)

## Step 4: Auto-check high confidence items in daily note

For each high-confidence completed item that is currently `- [ ]` in the daily note:
- Use the Edit tool to change `- [ ] {{exact item text}}` → `- [x] {{exact item text}}`
- Track which items were auto-checked (tagged `[自动]` in the report)

Calendar events that don't have checkboxes (plain `-` bullets) — just note them as completed in the report, no edit needed.

## Step 5: Terminal output — completion status + confirmation

Print to terminal in this order:

1. **`✅ 已完成`** section — all completed items:
   - `✓ [自动] {{item}} (→ {{reason}})` for auto-checked items
   - `✓ [手动] {{item}}` for items already checked by user
   - `✓ {{item}} (已过)` for past calendar events

2. **`❓ 需要确认`** section — medium-confidence items:
   - List each item with reason for uncertainty
   - Use `AskUserQuestion` tool to let user confirm/deny each item
   - After user responds, update daily note accordingly (`[x]` if confirmed, keep `[ ]` if not)

3. **`❌ 未完成 → 明日遗留`** section — clearly not completed items

## Step 6: Generate retrospective statistics

Calculate:

- **计划完成率**: (completed items / total items) as percentage
- **番茄消耗**: sum of 🍅 estimates for completed items / sum of all 🍅 estimates
- **未完成原因分类** — for each uncompleted item, classify reason:
  - `⏰ 估时不足` — item was started but not finished (e.g., Linear status still In Progress)
  - `🚧 被阻塞` — item was blocked by external dependency
  - `📥 临时插入` — any new items that appeared during the day but weren't in original plan
- **时间分析** (from Timing data):
  - Group `by_project` into meaningful categories (e.g., merge similar project names)
  - Calculate percentage of total hours for each category
  - Display as progress bar: `█` (filled) and `░` (empty), 10 chars wide

## Step 7: Generate AI coaching feedback

Based on ALL collected data (completion stats, time analysis, what was done, what wasn't), generate feedback from 3 perspectives. Each perspective gives 2-4 sentences based on the actual data from today.

### 👔 Career Coach

- Focus on: skill growth, impact of completed work, career goal alignment
- Reference specific tickets/PRs completed and their significance
- If something was blocked, suggest escalation strategies

### ⚡ 效率教练

- Focus on: time allocation, pomodoro completion rate, work rhythm
- Compare planned vs actual
- Give specific suggestion for tomorrow's scheduling

### 🌱 Positive Intelligence

- Focus on: psychological state, identify saboteur patterns (Judge, Achiever, Controller, Hyper-Achiever, etc.)
- Acknowledge progress with empathy
- Suggest a PQ rep (mental fitness exercise)
- Use warm, supportive tone

## Step 8: Terminal output — full retrospective

Print the complete retrospective following the **Terminal Output Template** in `references/output-template.md` exactly.

## Step 9: Write retrospective to Obsidian

Append `## 今日回顾` to the daily note following the **Obsidian Daily Note Template** in `references/output-template.md`.

Write behavior:

| Condition | Action |
|-----------|--------|
| `## 今日回顾` does not exist | Append `## 今日回顾` section at end of file |
| `## 今日回顾` already exists | Replace from `## 今日回顾` to next `## ` heading or end of file |

## Error Handling

- If any single data source fails (MCP timeout, API error), log the error briefly and continue with remaining sources. Never let one source failure stop the entire review.
- If ALL sources fail, print an error message and suggest checking MCP configuration.
- Gmail is expected to be unconfigured initially — this is not an error.
- Timing not installed → skip time analysis section entirely.
- Notion token expired → log briefly, skip.
- If `## 今日计划` section not found → stop with `❌ 今天没有计划。请先运行 /today`
