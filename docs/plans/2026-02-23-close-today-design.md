# /close-today Skill Design

**Date**: 2026-02-23
**Approach**: Diff-based (方案 A) — 全量拉取数据源最新状态，与 daily note 逐项对比

## Overview

`/close-today` 是 `/today` 的配套 skill，每天工作结束时运行。自动判断今日计划的完成状态，生成完整回顾（完成率、时间分析、AI 教练反馈），输出到终端并追加到 Obsidian daily note。

## Daily Workflow

```
早上 /today        → 生成今日计划
    ↓
  （工作一天）
    ↓
晚上 /close-today  → 回顾 + 自动勾选 + AI 教练反馈
```

## 数据源 (7 个)

| # | 数据源 | Tool / API | 拉取内容 | 用途 |
|---|--------|-----------|---------|------|
| 1 | Google Calendar | `mcp__google-drive__calendar_events_list` | 今天的事件 | 判断会议是否已过 |
| 2 | Linear | `mcp__plugin_linear_linear__list_issues` | issue 最新状态 | 判断 ticket 是否 Done |
| 3 | GitHub | `gh` CLI | PR merge/review 状态 | 判断 PR review 是否完成 |
| 4 | Slack | `mcp__slack__conversations_history` | 最近消息 | 判断是否已回复 @mention |
| 5 | Gmail | Gmail MCP（待配置） | 未读邮件 | 判断邮件是否已处理 |
| 6 | Notion | `mcp__notion__notion-search` | task 状态 | 判断 Notion task 是否完成 |
| 7 | Timing | Web API (`web.timingapp.com`) | 今天的时间记录 | 实际时间分析 |

## 核心逻辑: 逐项匹配 & 完成判断

### Step 1 — 读取今日计划

读取 `## 今日计划` section，解析每个 item：
- 状态: `[ ]` vs `[x]`（已手动勾选的保持不变）
- 类型标识: `MLS-xxx` (Linear), `PR #xxx` (GitHub), 时间段 (Calendar), 其他
- 所属分类: 固定时间 / 紧急 / 专注 / 待处理 / 遗留

### Step 2 — 并行拉取 7 个数据源最新状态

与 `/today` 相同的 API 调用 + Timing Web API。

### Step 3 — 完成状态判断 (两步走)

| 类型 | 高置信完成条件 → 直接勾 | 中/低置信 → 需确认 |
|------|----------------------|-------------------|
| Calendar 事件 | 当前时间 > 结束时间 | — |
| Linear issue (`MLS-xxx`) | 状态变为 Done/Cancelled | 状态仍 In Progress 但有新 commit |
| GitHub PR review | PR 已 merge 或我已提交 review | PR 仍 open 但有新 comment |
| Slack @mention | 我在该 thread 有新回复 | thread 有新消息但我未回复 |
| Gmail | — | 无法确定（Gmail 不追踪已回复） |
| Notion task | 状态变为 Done/Complete | — |
| 通用项（无标识符） | 已手动勾选 `[x]` | 未勾选，无法自动判断 |

**高置信度** → 直接在 daily note 中 `[ ]` → `[x]`
**中/低置信度** → 终端列出，等用户确认后更新

## 回顾输出

### 终端输出

```
🌙 今日回顾 — {{DATE}} ({{DAY}})
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ 已完成 ({{done}}/{{total}})
  ✓ {{item}} (→ {{reason}})
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
  {{2-4 句，关注技能成长、影响力、职业目标对齐}}

  ⚡ 效率教练
  {{2-4 句，关注时间分配、番茄完成率、工作节奏、明日优化}}

  🌱 Positive Intelligence
  {{2-4 句，关注心理状态、识别心魔模式、积极重构}}
```

### Obsidian 追加

追加 `## 今日回顾` section 到同一天的 daily note：

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

### 写入行为

| 操作 | 目标 |
|------|------|
| 自动勾选 | 修改 `## 今日计划` section: `- [ ]` → `- [x]` |
| 追加回顾 | 追加 `## 今日回顾` section（如已存在则替换） |

## AI 教练反馈规则

三个视角，每个 2-4 句话，基于当天实际数据：

| 视角 | 关注点 |
|------|--------|
| 👔 Career Coach | 技能成长、影响力、职业目标对齐、是否做了高杠杆的事 |
| ⚡ 效率教练 | 时间分配、番茄完成率、工作节奏、明日优化建议 |
| 🌱 Positive Intelligence | 心理状态、识别心魔模式（Judge, Achiever, Controller 等）、积极重构、PQ rep |

## Timing API 配置

- Endpoint: `web.timingapp.com`
- Auth: Bearer token (API key)
- Query: `GET /time-entries?start_date_min=YYYY-MM-DD&start_date_max=YYYY-MM-DD`
- 按 project 分组计算时长
- 如果 API 不可用，跳过时间分析（graceful degradation）

## Skill 结构

```
~/today-yolo/skills/close-today/
├── SKILL.md
└── references/
    └── output-template.md
```

安装: `ln -s ~/today-yolo/skills/close-today ~/.claude/skills/close-today`

## 执行步骤

| Step | 描述 | 并行？ |
|------|------|--------|
| 1 | 读取今日 daily note，解析 `## 今日计划` 中所有 items | — |
| 2 | 并行拉取 7 个数据源最新状态 | ✅ 全部并行 |
| 3 | 逐项匹配，判断完成状态（高/中/低置信度） | — |
| 4 | 高置信度项直接在 daily note 中 `[ ]` → `[x]` | — |
| 5 | 终端输出：已完成、需确认、未完成列表 | — |
| 6 | 等用户确认中置信度项 → 更新 daily note | — |
| 7 | 生成回顾统计 + AI 教练反馈 | — |
| 8 | 终端输出完整回顾 | — |
| 9 | 追加 `## 今日回顾` 到 daily note | — |

## 错误处理

- 与 `/today` 相同：单个数据源失败不阻塞整体流程
- Timing API 不可用 → 跳过时间分析，其他部分正常输出
- Gmail 未配置 → 静默跳过
- 如果 `## 今日计划` section 不存在 → 提示先运行 `/today`
