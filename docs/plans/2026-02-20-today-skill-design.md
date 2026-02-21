# /today Skill Design

**Date**: 2026-02-20
**Approach**: Pure Skill (方案 A) — 复用已有 MCP 生态，Claude 做智能排序

## Overview

`/today` 是一个 Claude Code skill，每天早上运行一次，自动聚合 6 个数据源的信息，通过 AI 智能排序生成今日计划。输出到终端 + Obsidian daily note。

## Daily Workflow

```
早上 /today      → 生成今日计划（本 skill）
    ↓
  （工作一天）
    ↓
晚上 /today-close → 回顾 + 自动勾选已完成项（future skill）
```

## 数据源

| # | 数据源 | MCP/Tool | 拉取内容 | 时间范围 |
|---|--------|----------|---------|---------|
| 1 | Google Calendar | `mcp__google-drive__calendar_events_list` | 今天的所有事件（时间、标题、参会者） | 今天 |
| 2 | Linear | `mcp__plugin_linear_linear__list_issues` | 分配给我的 active issues（状态、优先级、due date） | Active |
| 3 | GitHub | `gh` CLI | Open PR reviews requested + unresolved comments on my PRs | Open |
| 4 | Slack | `mcp__slack__conversations_history` | 未读消息 / @mentions | 过去 48h |
| 5 | Gmail | Gmail MCP（待配置） | 未读邮件（发件人、主题） | 今天 + 昨天未处理 |
| 6 | Notion | `mcp__notion__notion-search` | 分配给我的 tasks | Active |

### Carry-forward 机制

- 读取昨天的 Obsidian daily note，提取未勾选的 checkbox 项
- Slack/Linear 拉取 48h 范围作为补充
- 遗留项在输出中标记 `[carry-forward]`

### Gmail MCP 配置（TODO）

`/opt/homebrew/bin/google-mcp-server` 已安装，需添加 Gmail scope 到 `~/.claude/mcp.json`。

## AI 智能排序

Claude 综合以下维度判断优先级：

1. **时间紧迫性** — 有固定时间的会议最优先；有 due date 的 ticket 次之
2. **阻塞性** — 别人在等我的（PR review、Slack @mention）优先于我自己的任务
3. **上下文切换成本** — 相关事项尽量放在一起（同一个 PR 的 comment 合并处理）

复杂度用番茄钟表示（🍅 = 25min）。

## 输出格式

### 终端（中文 + 专有名词英文）

```
☀️ 今日计划 — 2026-02-20 (Thu)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📅 固定时间
  09:00-09:30  Sprint standup                          🍅 1
  14:00-15:00  Design review: auth flow                🍅 2

🔥 紧急（别人在等）
  ☐ Review PR #2601 — nose BFF endpoint (3 comments)  🍅 1
  ☐ 回复 @eric #pod-notegen — eval 问题               🍅 0.5

📋 专注工作
  ☐ MLS-751: 实现 nose feature flag                    🍅 3
  ☐ MLS-748: 更新 section postprocessing               🍅 2

📬 待处理
  ☐ 5 封未读邮件 (2 from eng-all, 1 from HR)          🍅 1
  ☐ 3 个 Slack threads in #general                     🍅 0.5

🔄 遗留 (carry-forward)
  ☐ [昨日] MLS-745: 修复 nose parsing bug              🍅 2

─────────────────────────────
合计: ~12 🍅 (5h)  |  可用时间: ~6h (减去会议)
⚠️ 超载 — 建议推迟「待处理」类事项
```

### Obsidian Daily Note

写入 `{vault}/Daily Notes/YYYY-MM-DD.md`：
- 如果 daily note 已存在，append `## 今日计划` section
- 如果不存在，创建新文件
- 使用 Obsidian checkbox 格式 `- [ ]`，可手动勾选

## Skill 结构

```
~/.claude/skills/today/
├── SKILL.md
└── references/
    └── output-template.md
```

安装方式：`ln -s ~/today-yolo/skills/today ~/.claude/skills/today`

## Future: /today-close

独立 skill，用于一天结束时：
- 检查 Linear issues 状态变化（已关闭的自动勾）
- 检查 PR 是否已 merge
- 检查 Calendar 事件是否已过
- 标记剩余未完成项为 carry-forward
