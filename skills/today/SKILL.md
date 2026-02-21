---
name: today
description: 生成今日计划。聚合 Calendar、Linear、GitHub、Slack、Gmail、Notion 数据源，AI 智能排序，输出到终端 + Obsidian daily note。每天早上运行一次。
---

# /today

生成今日计划。并行拉取 6 个数据源，AI 智能排序，输出到终端并写入 Obsidian daily note。

## Step 1: Collect data from 6 sources

Determine today's date and yesterday's date in `YYYY-MM-DD` format. Then collect data from all sources below. **Run independent sources in parallel** (use parallel tool calls where possible).

### Source 1 — Google Calendar

Use `mcp__google-drive__calendar_events_list` to fetch today's events.

- Parameters: set the date range to today only (start of day to end of day)
- Extract from each event: **start time**, **end time**, **title**, **attendees count**
- These go into the `📅 固定时间` section

### Source 2 — Linear

Use `mcp__plugin_linear_linear__list_issues` to fetch issues assigned to me.

- Make **two** calls to `mcp__plugin_linear_linear__list_issues`:
  1. `assignee: "me"`, `state: "started"` — captures In Progress and In Review
  2. `assignee: "me"`, `state: "unstarted"` — captures Todo, Ready for Work, Backlog
- From the combined results, keep issues where:
  - Status is `In Progress` or `In Review` (regardless of due date), OR
  - Status is `Ready for Work` or `Todo` with due date within 7 days or priority ≤ 2 (High/Urgent), OR
  - Due date is today or overdue (any status)
- Extract: **identifier** (e.g. `MLS-751`), **title**, **priority** (1=Urgent, 2=High, 3=Medium, 4=Low), **due date**, **status**

### Source 3 — GitHub

Run these two Bash commands:

```bash
gh pr list --search "review-requested:@me" --json number,title,url,reviewRequests
```

```bash
gh api notifications --jq '.[] | select(.reason=="review_requested" or .reason=="mention")'
```

- Extract: **PR number**, **title**, **comment count**, **repo name**
- Deduplicate: if a PR appears in both results, merge into one item

### Source 4 — Slack

Use `mcp__slack__conversations_history` to check for messages in channels the user is active in.

- Focus on: **@mentions** and **DMs** from the past 48 hours
- Use the `oldest` parameter set to 48 hours ago (Unix timestamp)
- Check at minimum these types of channels: DMs and channels where user was recently mentioned
- Extract: **channel name**, **sender**, **message preview** (first 80 chars), **timestamp**
- Group multiple messages in the same thread into one item

### Source 5 — Gmail

Check if Gmail MCP tools are available (e.g., tools with prefix `mcp__gmail` or similar).

- **If available**: fetch unread emails from today and yesterday
  - Extract: **sender**, **subject**, **date**
  - Group bulk/notification emails (e.g., multiple from same sender like `eng-all@`) into one summary item
- **If NOT available**: print exactly:
  ```
  ⚠️ Gmail MCP 未配置，跳过邮件。
  ```

### Source 6 — Notion

Use `mcp__notion__notion-search` to find tasks assigned to the user.

- Query for tasks or to-do items
- Extract: **title**, **status**, **due date**
- If no relevant tasks found, **skip silently** (do not show an empty section or warning)

## Step 2: Carry-forward from yesterday

Read yesterday's Obsidian daily note:

```
/Users/mia/Documents/Mia的Sunny号/{{yesterday_YYYY-MM-DD}}.md
```

- Find all lines matching the pattern `- [ ]` (unchecked checkboxes)
- Strip the leading `- [ ] ` and any existing section prefixes like `[昨日]`
- These items become the `🔄 遗留` section
- If the file does not exist, skip carry-forward silently (no error, no warning)

## Step 3: AI Smart Sort

After collecting ALL data, organize items into 5 categories and sort using these dimensions:

### Sorting dimensions

1. **时间紧迫性** (Time urgency)
   - Calendar events go to `📅 固定时间`, sorted by start time (chronological)
   - Items with due date today or overdue get higher priority within their category
   - Overdue items should be flagged

2. **阻塞性** (Blocking others)
   - Items where **others are waiting on me** go to `🔥 紧急（别人在等）`:
     - PR review requests
     - Slack @mentions requiring a response
     - Linear issues blocking others
   - Solo/independent work goes to `📋 专注工作`

3. **上下文切换成本** (Context-switching cost)
   - Group related items together (e.g., multiple comments on the same PR = one item)
   - Adjacent Linear tickets in the same epic = group together
   - Low-priority informational items go to `📬 待处理`:
     - Slack threads that are FYI-only
     - Bulk/notification emails
     - Notion tasks with no due date

### Category assignment

| Category | What goes here |
|----------|---------------|
| 📅 固定时间 | Calendar events (sorted by start time) |
| 🔥 紧急（别人在等） | PR reviews, Slack @mentions needing response, blocking issues |
| 📋 专注工作 | Linear tickets (In Progress first, then by priority), focused coding tasks |
| 📬 待处理 | Informational threads, bulk emails, low-priority Notion tasks |
| 🔄 遗留 | Unchecked items from yesterday's daily note |

### Pomodoro estimates

Assign a 🍅 pomodoro estimate to every item:

| Estimate | Duration | Use for |
|----------|----------|---------|
| 0.5 | ~12 min | Quick reply, skim email, short review |
| 1 | ~25 min | Standard PR review, respond to thread, small task |
| 2 | ~50 min | Medium coding task, design review prep |
| 3 | ~75 min | Deep focus work, complex implementation |

### Capacity calculation

Calculate:
- **Total pomodoros**: sum of all 🍅 estimates
- **Meeting hours**: sum of calendar event durations
- **Available hours**: `8h - meeting hours`
- **Available pomodoros**: `available hours * 60 / 25`
- If total pomodoros > available pomodoros, show an overload warning in the output

## Step 4: Output to terminal

Print the formatted plan to the terminal. Follow the **Terminal Output Template** in `references/output-template.md` exactly.

Key formatting rules:
- **Language**: Chinese with English proper nouns (technical terms, product names, ticket IDs like `MLS-751`, PR numbers like `#2601`)
- **Day names**: use Chinese weekday format: `周一`, `周二`, `周三`, `周四`, `周五`, `周六`, `周日`
- **Omit empty sections**: if a category has zero items, do not show its header
- **Pomodoro estimates**: right-aligned with 🍅 emoji
- **Overload warning**: only show when total pomodoros exceed available capacity
  - Format: `⚠️  超载！计划 {{total}}🍅 但只有 ~{{available}}h 可用，考虑推迟低优先级任务`

## Step 5: Write Obsidian daily note

Write the plan to the Obsidian vault daily note:

```
/Users/mia/Documents/Mia的Sunny号/{{YYYY-MM-DD}}.md
```

### Write behavior

| Condition | Action |
|-----------|--------|
| File does not exist | Create new file with `## 今日计划` as the first section |
| File exists, no `## 今日计划` section | Append `## 今日计划` section at the end of the file |
| File exists, has `## 今日计划` section | Replace the existing `## 今日计划` section (from `## 今日计划` up to the next `## ` heading or end of file) |

### Obsidian format

Follow the **Obsidian Daily Note Template** in `references/output-template.md` exactly.

Key formatting rules:
- Subsection headers use `###` (one level below `## 今日计划`)
- **Fixed-time events**: plain bullet list (`-`) — meetings don't need checking off
- **All other items**: checkbox format (`- [ ]`)
- Every item annotated with 🍅 estimate
- Carry-forward items prefixed with `[昨日]`
- Omit sections with zero items
- Summary line as blockquote: `> 合计: ~{{total}} 🍅 ({{hours}}h) | 可用时间: ~{{available}}h`

## Error Handling

- If any single data source fails (MCP timeout, API error), log the error briefly and continue with remaining sources. Never let one source failure stop the entire plan.
- If ALL sources fail, print an error message and suggest checking MCP configuration.
- Gmail is expected to be unconfigured initially — this is not an error.
