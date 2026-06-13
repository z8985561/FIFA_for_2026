---
name: superpowers-finishing-branch
description: 当实现完成、所有测试通过，需要决定如何整合工作时使用
---

# 完成开发分支

## 概述

通过清晰的选项指导开发工作的完成，并处理选择的工作流。

**核心原则：** 验证测试 → 呈现选项 → 执行选择 → 清理。

**开始时宣布：** "我正在使用 superpowers-finishing-branch 技能完成此工作。"

## 流程

### 步骤 1：验证测试

```powershell
.venv\Scripts\python.exe -m pytest
```

**如果测试失败：** 停下来。不能继续合并/PR，直到测试通过。

### 步骤 2：呈现选项

```
实现完成。你想怎么做？

1. 合并回主分支本地
2. 推送并创建 Pull Request
3. 保持分支原样（我稍后处理）
4. 丢弃此工作

哪个选项？
```

### 步骤 3：执行选择

#### 选项 1：本地合并

```bash
git checkout main
git pull
git merge feat/xxx
.venv\Scripts\python.exe -m pytest  # 验证合并结果
git branch -d feat/xxx
```

#### 选项 2：推送并创建 PR

```bash
git push -u origin feat/xxx
# 然后用 gh pr create 或手动创建 PR
```

#### 选项 3：保持原样

报告：保持分支 `<name>`。不清理。

#### 选项 4：丢弃

**先确认：**
```
这将永久删除：
- 分支 <name>
- 所有未合并的提交

输入 'discard' 确认。
```

等待精确确认。

### 步骤 4：最终审查

如果合并/PR，先运行 `review` 工具做最终审查：

```
review({ task: "合并前最终审查" })
```

## 红旗信号

**永远不要：**
- 测试失败时继续
- 未经确认删除工作
- 未经验证合并结果就声称完成
