# Output Template Reference

This file defines the two output formats for the `/today` skill:
1. **Terminal output** — displayed directly in the CLI
2. **Obsidian daily note** — written to the user's vault

---

## 1. Terminal Output Template

```
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
```

### Rendering Rules

- **Sections are omitted** if they contain zero items (don't show empty headers).
- **Pomodoro estimates** are right-aligned with 🍅 emoji.
- **Overload warning** appears only when total pomodoros exceed available time.
  Example: `⚠️  超载！计划 12🍅 但只有 ~4h 可用，考虑推迟低优先级任务`
- **Day names** use Chinese: 一/二/三/四/五/六/日 (e.g., `周三`).

---

## 2. Obsidian Daily Note Template

### Target Path

```
/Users/mia/Documents/Mia的Sunny号/{{YYYY-MM-DD}}.md
```

### Write Behavior

| Condition | Action |
|-----------|--------|
| File does not exist | Create new file with `## 今日计划` as first section |
| File exists, no `## 今日计划` | Append `## 今日计划` section at the end |
| File exists, has `## 今日计划` | Replace the existing `## 今日计划` section |

### Format

```markdown
## 今日计划

### 📅 固定时间
- {{HH:MM}}-{{HH:MM}} {{event title}} 🍅 {{estimate}}

### 🔥 紧急（别人在等）
- [ ] {{item description}} 🍅 {{estimate}}

### 📋 专注工作
- [ ] {{item description}} 🍅 {{estimate}}

### 📬 待处理
- [ ] {{item description}} 🍅 {{estimate}}

### 🔄 遗留
- [ ] [昨日] {{item description}} 🍅 {{estimate}}

> 合计: ~{{total}} 🍅 ({{hours}}h) | 可用时间: ~{{available}}h
```

### Formatting Rules

- **Fixed-time events** use plain bullet list (`-`) — meetings don't need checking off.
- **All other items** use checkbox format (`- [ ]`).
- **Each item** is annotated with a 🍅 estimate.
- **Carry-forward items** are prefixed with `[昨日]`.
- **Sections are omitted** if they contain zero items.
- **Subsection headers** use `###` (one level below `## 今日计划`).
