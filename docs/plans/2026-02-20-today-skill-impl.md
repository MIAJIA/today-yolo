# /today Skill Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create a `/today` Claude Code skill that aggregates 6 data sources into a prioritized daily plan, output to terminal + Obsidian daily note.

**Architecture:** Pure skill (SKILL.md + reference files). Claude calls existing MCP tools and `gh` CLI at runtime, then applies AI sorting. No scripts, no custom MCP server.

**Tech Stack:** Claude Code skill (Markdown), MCP tools (Google Drive, Linear, Slack, Notion), `gh` CLI, Obsidian vault file I/O.

---

### Task 1: Create output template reference file

**Files:**
- Create: `skills/today/references/output-template.md`

**Step 1: Write the output template**

```markdown
## Terminal Output Template

☀️ 今日计划 — {{DATE}} ({{DAY}})
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📅 固定时间
  {{HH:MM}}-{{HH:MM}}  {{event title}}                 🍅 {{estimate}}

🔥 紧急（别人在等）
  ☐ {{item description}}                                🍅 {{estimate}}

📋 专注工作
  ☐ {{item description}}                                🍅 {{estimate}}

📬 待处理
  ☐ {{item description}}                                🍅 {{estimate}}

🔄 遗留 (carry-forward)
  ☐ [昨日] {{item description}}                         🍅 {{estimate}}

─────────────────────────────
合计: ~{{total}} 🍅 ({{hours}}h)  |  可用时间: ~{{available}}h (减去会议)
{{overload warning if total > available}}

## Obsidian Daily Note Template

写入: `/Users/mia/Documents/Mia的Sunny号/{{YYYY-MM-DD}}.md`

如果文件已存在，append `## 今日计划` section。
如果文件不存在，创建新文件。

格式:
- 固定时间用 bullet list（不用 checkbox，会议不需要勾选）
- 其他用 `- [ ]` checkbox
- 每项标注 🍅 估算
- carry-forward 项标注 `[昨日]`
```

**Step 2: Commit**

```bash
git -C ~/today-yolo add skills/today/references/output-template.md
git -C ~/today-yolo commit -m "feat: add output template reference"
```

---

### Task 2: Create the SKILL.md (core skill definition)

This is the main file. It tells Claude exactly what to do when `/today` is invoked.

**Files:**
- Create: `skills/today/SKILL.md`

**Step 1: Write SKILL.md**

The SKILL.md must contain:

1. **Frontmatter** — `name: today`, `description: ...`
2. **Data collection instructions** — 6 data sources, exact MCP tool names, what to query
3. **Carry-forward instructions** — read yesterday's Obsidian daily note, extract unchecked items
4. **AI sorting prompt** — the 3 dimensions (时间紧迫性, 阻塞性, 上下文切换成本)
5. **Output instructions** — terminal format + Obsidian daily note write

Key details for each data source:

**Google Calendar:**
- Tool: `mcp__google-drive__calendar_events_list`
- Filter: today's date only
- Extract: start time, end time, title, attendees count

**Linear:**
- Tool: `mcp__plugin_linear_linear__list_issues`
- Filter: assigned to me, status in [In Progress, Todo, Backlog with due date today]
- Extract: identifier, title, priority, due date, status

**GitHub:**
- Tool: `gh pr list --search "review-requested:@me" --json number,title,url`
- Tool: `gh api notifications --jq '.[] | select(.reason=="review_requested" or .reason=="mention")'`
- Extract: PR number, title, comment count

**Slack:**
- Tool: `mcp__slack__conversations_history` on key channels
- Key channels to check: channels where user has unread @mentions
- Time range: past 48 hours
- Extract: channel, sender, message preview, timestamp

**Gmail:**
- Tool: Gmail MCP (needs configuration first — see Task 4)
- If Gmail MCP not yet configured, skip gracefully with message: "⚠️ Gmail MCP 未配置，跳过邮件检查。运行 Task 4 的步骤来配置。"
- Extract: sender, subject, date

**Notion:**
- Tool: `mcp__notion__notion-search`
- Query: tasks assigned to me
- Extract: title, status, due date
- If no tasks found, skip section silently

**Carry-forward:**
- Read file: `/Users/mia/Documents/Mia的Sunny号/{{yesterday_date}}.md`
- Parse: find all lines matching `- [ ]` (unchecked checkboxes)
- These become the 🔄 遗留 section

**Sorting prompt (embedded in SKILL.md):**
After collecting all data, sort by:
1. 时间紧迫性 — fixed-time events first (chronological), then items with due dates
2. 阻塞性 — items where others are waiting (PR reviews, @mentions) before solo work
3. 上下文切换成本 — group related items together

Assign 🍅 estimates (0.5 = 12min, 1 = 25min, 2 = 50min, 3 = 75min, etc.)

**Output:**
1. Print formatted terminal output (see `references/output-template.md`)
2. Write/append Obsidian daily note to `/Users/mia/Documents/Mia的Sunny号/{{YYYY-MM-DD}}.md`

**Step 2: Commit**

```bash
git -C ~/today-yolo add skills/today/SKILL.md
git -C ~/today-yolo commit -m "feat: add /today skill definition"
```

---

### Task 3: Install skill via symlink and test

**Step 1: Create symlink**

```bash
ln -s ~/today-yolo/skills/today ~/.claude/skills/today
```

**Step 2: Verify symlink**

```bash
ls -la ~/.claude/skills/today
# Should point to ~/today-yolo/skills/today
```

**Step 3: Test the skill**

In a new Claude Code session, run `/today` and verify:
- It attempts to fetch from all 6 data sources
- Gmail gracefully skips if MCP not configured
- Terminal output matches the template format
- Obsidian daily note is created/appended correctly
- Carry-forward reads yesterday's note (if exists)

**Step 4: Commit any fixes**

```bash
git -C ~/today-yolo add -A
git -C ~/today-yolo commit -m "fix: adjustments from first test run"
```

---

### Task 4: Configure Gmail MCP (optional — can defer)

**Step 1: Research google-mcp-server Gmail support**

```bash
/opt/homebrew/bin/google-mcp-server --help
```

Check if it supports Gmail scope. If yes, proceed. If not, search for alternative Gmail MCP servers.

**Step 2: Add Gmail MCP to config**

Edit `~/.claude/mcp.json` to add a gmail server entry alongside the existing slack config. The exact config depends on Step 1 findings.

**Step 3: Test Gmail MCP**

Verify the Gmail MCP can list recent unread emails.

**Step 4: Update SKILL.md**

Remove the "Gmail MCP 未配置" fallback message now that it's working.

**Step 5: Commit**

```bash
git -C ~/today-yolo add skills/today/SKILL.md
git -C ~/today-yolo commit -m "feat: enable Gmail data source"
```

---

### Task 5: Push to GitHub

**Step 1: Push**

```bash
git -C ~/today-yolo push origin main
```

---

## Execution Notes

- Tasks 1-3 are the MVP — get the skill working with 5 data sources (no Gmail)
- Task 4 is optional and can be deferred
- Task 5 is the final push
- The SKILL.md in Task 2 is the most critical piece — it's essentially the entire "code" of this project
