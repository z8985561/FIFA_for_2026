---
name: superpowers-writing-plans
description: 当你有规格或需求用于多步骤任务时使用，在触碰代码之前
---

# 编写实现计划

## 概述

编写全面的实现计划，假设执行者对我们的代码库零上下文且品味存疑。记录他们需要知道的一切：每个任务涉及哪些文件、代码、测试、可能需要查阅的文档、如何测试。将整个计划拆成 bite-sized 任务。DRY。YAGNI。TDD。频繁提交。

假设他们是熟练的开发者，但对我们的工具集和问题领域几乎一无所知。假设他们不太懂好的测试设计。

**开始时宣布：** "我正在使用 superpowers-writing-plans 技能创建实现计划。"

**计划保存到：** `docs/superpowers/plans/YYYY-MM-DD-<功能名>.md`

## 范围检查

如果规格涉及多个独立子系统，建议拆分为单独的计划——每个子系统一个。每个计划应该产出独立可工作的、可测试的软件。

## Bite-Sized 任务粒度

**每个步骤一个动作（2-5 分钟）：**
- "编写失败的测试" — 一步
- "运行以确保失败" — 一步
- "实现最小代码使测试通过" — 一步
- "运行测试确保通过" — 一步
- "提交" — 一步

## 计划文档头部

```markdown
# [功能名] 实现计划

> **给执行者：** 使用 superpowers-executing-plans 来逐任务实现此计划。步骤使用 checkbox (`- [ ]`) 语法跟踪。

**目标：** [一句话描述构建什么]

**架构：** [2-3 句话关于方法]

**技术栈：** [关键技术/库]

---
```

## 任务结构

```markdown
### 任务 N: [组件名]

**文件：**
- 创建: `exact/path/to/file.py`
- 修改: `exact/path/to/existing.py:123-145`
- 测试: `tests/exact/path/to/test.py`

- [ ] **步骤 1: 编写失败的测试**

  ```python
  def test_specific_behavior():
      result = function(input)
      assert result == expected
  ```

- [ ] **步骤 2: 运行测试验证失败**

  运行: `.venv\Scripts\python.exe -m pytest tests/path/test.py::test_name -v`
  预期: FAIL

- [ ] **步骤 3: 编写最小实现**

  ```python
  def function(input):
      return expected
  ```

- [ ] **步骤 4: 运行测试验证通过**

  运行: `.venv\Scripts\python.exe -m pytest tests/path/test.py::test_name -v`
  预期: PASS

- [ ] **步骤 5: 提交**

  ```bash
  git add tests/path/test.py src/path/file.py
  git commit -m "feat: add specific feature"
  ```
```

## 禁止占位符

每一步必须包含执行者需要的实际内容。这些是**计划失败**——永远不要写：
- "TBD"、"TODO"、"稍后实现"、"补充细节"
- "添加适当的错误处理" / "添加验证" / "处理边界情况"
- "为上述编写测试"（没有实际测试代码）
- "与任务 N 类似"（重复代码——执行者可能乱序阅读任务）
- 描述做什么但不展示如何做的步骤（代码步骤需要代码块）
- 引用未在任何任务中定义的类型、函数或方法

## 记住
- 始终使用精确文件路径
- 每一步都有完整代码——如果步骤修改代码，展示代码
- 精确命令及预期输出
- DRY、YAGNI、TDD、频繁提交

## 自审

写完完整计划后，检查：
1. **规格覆盖：** 浏览规格的每个部分/需求。能指出实现它的任务吗？
2. **占位符扫描：** 搜索计划中的红旗——上述 "禁止占位符" 中的任何模式
3. **类型一致性：** 后续任务中使用的类型、方法签名、属性名是否与前面任务定义的一致？

## 执行交接

保存计划后，告诉用户：

> "计划完成，已保存到 `docs/superpowers/plans/<filename>.md`。请审查，批准后我将使用 superpowers-executing-plans 执行。"

**不要**在用户批准计划前开始执行。
