# Output Template Reference

This file defines the two output formats for the `/close-today` skill:
1. **Terminal output** — displayed directly in the CLI
2. **Obsidian daily note** — written to the user's vault

---

## 1. Terminal Output Template

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

### Rendering Rules

- **Sections are omitted** if they contain zero items (don't show empty headers).
- **Day names** use Chinese weekday: 周一, 周二, 周三, 周四, 周五, 周六, 周日.
- **Language** is Chinese with English proper nouns preserved.
- **Progress bar** uses `█` (filled) and `░` (empty), always 10 characters wide.
  Example: `深度工作:  3.5h  █████░░░░░  52%`
- **Completion reasons** appear in parentheses: `(→ Done)`, `(→ Merged)`, `(已过)`.
- **`[自动]`** = auto-checked by high-confidence match against external signals (e.g., PR merged, meeting ended).
- **`[手动]`** = item was already marked `[x]` in the daily note by the user.
- **`❓ 需要确认`** items are interactive — the skill waits for user `y/n` response before proceeding to the next item.
- **未完成原因** breakdown only shows categories that have non-zero counts.

---

## 2. Obsidian Daily Note Template

### Target Path

```
/Users/mia/Documents/Mia的Sunny号/{{YYYY-MM-DD}}.md
```

### Write Behavior

| Condition | Action |
|-----------|--------|
| `## 今日回顾` does not exist | Append `## 今日回顾` section at end of file |
| `## 今日回顾` exists | Replace from `## 今日回顾` to the next `## ` heading or EOF |

### Format

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

### Formatting Rules

- **Completed items** use `- [x]` checkbox format.
- **Uncompleted items** use `- [ ]` checkbox format.
- **Each item** is annotated with a 🍅 estimate (preserved from the original plan).
- **Sections are omitted** if they contain zero items.
- **Subsection headers** use `###` (one level below `## 今日回顾`).
- **Time analysis** uses a markdown table with three columns.
- **Footer blockquote** provides a one-line summary for quick scanning.
