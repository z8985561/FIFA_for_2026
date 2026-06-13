---
name: superpowers-using
description: 在任何对话开始时使用 — 建立如何发现和使用 Superpowers 技能，要求在做出任何响应之前先检查技能
---

# Superpowers 使用指南

## 指令优先级

Superpowers 技能覆盖默认系统行为，但 **用户指令永远优先**：

1. **用户的明确指令**（CLAUDE.md、直接请求）—— 最高优先级
2. **Superpowers 技能** —— 在冲突时覆盖默认系统行为
3. **默认系统提示** —— 最低优先级

## 如何使用技能

在 Reasonix Code 中，使用 `run_skill` 工具调用技能。技能名以 `superpowers-` 开头。

```
run_skill({ name: "superpowers-brainstorming", arguments: "用户想做什么" })
```

## 核心规则

**在任何响应或行动之前，先检查是否有相关技能。** 即使只有 1% 的可能性适用，也应该调用技能检查。

### 红旗信号

以下想法意味着 STOP——你在合理化：

| 想法 | 现实 |
|------|------|
| "这只是个简单问题" | 问题就是任务。检查技能。 |
| "我需要先了解更多上下文" | 技能检查在澄清问题之前。 |
| "让我先探索代码库" | 技能告诉你如何探索。先检查。 |
| "这不需要正式技能" | 如果有技能存在，就用它。 |
| "我记得这个技能" | 技能会演化。读取当前版本。 |
| "技能太重了" | 简单的事情会变复杂。用它。 |

## 技能优先级

多个技能可能适用时：

1. **流程技能优先**（brainstorming、debugging）—— 决定如何接近任务
2. **实现技能其次**（writing-plans、executing-plans、tdd）—— 指导执行

## Reasoning Code 工具映射

| Superpowers (Claude Code) | Reasonix Code |
|---------------------------|---------------|
| `Skill` | `run_skill` |
| `TodoWrite` | `todo_write` |
| `Read` | `read_file` |
| `Write` | `write_file` |
| `Edit` | `edit_file` |
| `Bash` | `run_command` |
| `Glob` | `glob` |
| `Grep` | `search_content` |
| `Task` (通用子代理) | `explore` / `review` / `research`（专用子代理） |

**注意：** Reasonix Code 没有通用子代理派发（Task 工具），因此 `subagent-driven-development` 不适用。使用 `executing-plans` 代替。
