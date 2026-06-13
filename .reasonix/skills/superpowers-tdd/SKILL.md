---
name: superpowers-tdd
description: 在实现任何功能或修复 bug 时使用，在编写实现代码之前
---

# 测试驱动开发（TDD）

## 概述

先写测试。看着它失败。写最小代码使其通过。

**核心原则：** 如果你没看到测试失败，你就不知道它是否测试了正确的东西。

**违反规则的字母就是违反规则的精神。**

## 何时使用

**总是：**
- 新功能
- Bug 修复
- 重构
- 行为变更

**例外（询问用户）：**
- 一次性原型
- 生成的代码
- 配置文件

## 铁律

```
没有失败的测试，不写生产代码
```

在测试之前写了代码？删除它。重新开始。

**没有例外：**
- 不要保留作为"参考"
- 不要在写测试时"改编"它
- 不要看它
- 删除意味着删除

从测试开始全新实现。句号。

## 红-绿-重构

### RED — 写失败的测试

写一个最小的测试来展示应该发生什么。

```python
def test_retries_failed_operations_3_times():
    """重试失败操作 3 次"""
    attempts = 0
    def operation():
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise RuntimeError("fail")
        return "success"

    result = retry_operation(operation)

    assert result == "success"
    assert attempts == 3
```

**要求：**
- 一个行为
- 清晰的名称
- 真实代码（除非不可避免不用 mock）

### 验证 RED — 看着它失败

**强制。永远不要跳过。**

```powershell
.venv\Scripts\python.exe -m pytest tests/path/test.py::test_name -v
```

确认：
- 测试失败（不是报错）
- 失败消息符合预期
- 因为功能缺失而失败（不是拼写错误）

**测试通过了？** 你在测试已有行为。修复测试。

### GREEN — 最小代码

写最简单的代码使测试通过。

```python
def retry_operation(fn, max_retries=3):
    for i in range(max_retries):
        try:
            return fn()
        except Exception:
            if i == max_retries - 1:
                raise
```

刚好够通过。不要添加功能、重构其他代码或"改进"超出测试范围。

### 验证 GREEN — 看着它通过

**强制。**

```powershell
.venv\Scripts\python.exe -m pytest tests/path/test.py::test_name -v
```

确认：
- 测试通过
- 其他测试仍然通过
- 输出干净（无错误、警告）

### REFACTOR — 清理

只在绿色之后：
- 移除重复
- 改善命名
- 提取辅助函数

保持测试绿色。不要添加行为。

## 好测试

| 质量 | 好 | 坏 |
|------|-----|-----|
| **最小** | 一件事。名称中有 "and"？拆分。 | `test_validates_email_and_domain_and_whitespace` |
| **清晰** | 名称描述行为 | `test_test1` |
| **展示意图** | 展示期望的 API | 隐藏代码应该做什么 |

## 常见合理化借口

| 借口 | 现实 |
|------|------|
| "太简单了不需要测试" | 简单代码也会坏。测试只需 30 秒。 |
| "我之后再测试" | 之后写的测试一写就通过。通过什么也证明不了。 |
| "已经手动测试过了" | 临时 ≠ 系统化。没有记录，不能重跑。 |
| "删除 X 小时的工作是浪费" | 沉没成本谬误。保留无法信任的代码才是技术债。 |
| "需要先探索" | 可以。扔掉探索代码，从 TDD 开始。 |

## 验证检查清单

在标记工作完成之前：

- [ ] 每个新函数/方法都有测试
- [ ] 每个测试在实现前都看着它失败了
- [ ] 每个测试因预期原因失败（功能缺失，不是拼写错误）
- [ ] 写了最小代码使每个测试通过
- [ ] 所有测试通过
- [ ] 输出干净（无错误、警告）

不能检查所有框？你跳过了 TDD。重新开始。

## 最终规则

```
生产代码 → 测试存在且先失败过
否则 → 不是 TDD
```

没有用户明确许可，不得例外。
