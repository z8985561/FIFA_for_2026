---
name: taste-minimalist
description: 编辑型产品 UI 设计风格 — 暖色单色板、排版层级对比、扁平 bento 网格、极简组件架构，适合数据仪表盘和工具型界面
---

# 极简产品 UI 设计协议

## 概述

生成高度精炼、极简、"文档风格"的 Web 界面，类似 Notion / Linear 等顶级工作台平台。强制高对比暖色单色板、定制排版层级、宏观留白、bento-grid 布局、超扁平组件架构。拒绝通用 SaaS 设计趋势。

**适配说明：** 本项目使用 Vue 3 + Element Plus + ECharts。以下规则在 Element Plus 框架内尽量遵循，但不对抗组件库的既有设计 token。

## 绝对禁止

- 不使用 Inter、Roboto、Open Sans 作为默认字体
- 不使用 Tailwind 默认重度阴影（`shadow-md`、`shadow-lg`、`shadow-xl`）
- 不使用大面积主色背景
- 不使用渐变、霓虹色、3D 玻璃效果
- 卡片/容器不使用 `rounded-full`
- 不使用 emoji 替代图标
- 不使用 AI 陈词滥调："Elevate"、"Seamless"、"Unleash"、"Next-Gen"

## 排版架构

- **主 Sans（正文、UI、按钮）：** `'Geist Sans', 'SF Pro Display', 'Helvetica Neue', sans-serif`
- **衬线（标题、引用）：** `'Newsreader', 'Playfair Display', serif`，紧字距（`-0.02em`）、紧凑行高（`1.1`）
- **等宽（代码、键位、元数据）：** `'Geist Mono', 'SF Mono', 'JetBrains Mono', monospace`
- **正文颜色：** 非纯黑，用 charcoal `#2F3437`，行高 `1.6`
- **次要文本：** `#787774`

## 调色板（暖单色 + 点缀色）

- **画布/背景：** `#FFFFFF` 或 `#F7F6F3` / `#FBFBFA`
- **卡片表面：** `#FFFFFF` 或 `#F9F9F8`
- **边框/分割线：** `#EAEAEA` 或 `rgba(0,0,0,0.06)`
- **点缀色（仅用于标签、代码背景）：**
  - 淡红：背景 `#FDEBEC`，文字 `#9F2F2D`
  - 淡蓝：背景 `#E1F3FE`，文字 `#1F6C9F`
  - 淡绿：背景 `#EDF3EC`，文字 `#346538`
  - 淡黄：背景 `#FBF3DB`，文字 `#956400`

## 组件规范

- **卡片：** `border: 1px solid #EAEAEA`，圆角最大化 `8px`，内边距慷慨（`18px`-`24px`）
- **主 CTA 按钮：** 背景 `#111111`，文字 `#FFFFFF`，圆角 `4px`-`6px`，无阴影。hover → `#333333` 或微缩放
- **标签/徽章：** 胶囊形（`border-radius: 9999px`），小字号，大写 + 宽字距
- **分割线：** 用 `border-bottom: 1px solid #EAEAEA` 替代卡片容器
- **图标：** Phosphor Icons Bold 或 Element Plus 自带图标，统一描边宽度

## 数据仪表盘特殊考虑

对于本项目（Vue 3 + Element Plus + ECharts 仪表盘）：
- 数据卡片优先用 `border` 而非阴影区分层级
- 图表区域保持充足留白，不用密集网格挤压
- 表格行高慷慨，交替行背景极淡（`#FBFBFA`）
- 数字指标使用 Tabular Nums（等宽数字）以保证对齐
- 统计卡片用微妙的 hover 提升效果：`translateY(-2px)` + 极淡阴影

## 微动效

- **滚动入场：** 淡入 `translateY(12px)` → `0`，600ms，`cubic-bezier(0.16, 1, 0.3, 1)`
- **hover 状态：** 卡片 `box-shadow` 从 `0 0 0` 到 `0 2px 8px rgba(0,0,0,0.04)`，200ms
- **仅在 `transform` 和 `opacity` 上做动画** — 不触发布局重排
- 不使用 `window.addEventListener('scroll')` — 用 `IntersectionObserver`

## 执行协议

修改前端代码时：
1. 先建立宏观留白 — section 之间使用慷慨的垂直间距
2. 限制正文排版宽度到合适的 measure
3. 遵循单色板 + 点缀色体系
4. 每个卡片、分割线、边框保持 `1px solid #EAEAEA` 规范
5. 确保没有空白的扁平背景 — 通过内容密度或微妙纹理增加深度
