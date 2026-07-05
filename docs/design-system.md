# 设计系统 · Design System

整个 demo 的视觉语言都集中在这里。改一个 token，所有图表 + PDF + Word 同步更新。

---

## 🎨 配色

### 主色（深墨）

| Token | HEX | 用途 |
|-------|-----|------|
| `INK` | `#0F172A` | 标题、正文、主文案 |
| `GOLD` | `#B8860B` | eyebrow、强调、数字、key insight |
| `SLATE` | `#64748B` | 副文、caption、metadata |
| `PAPER` | `#FAF8F5` | 主背景（暖白纸） |
| `BORDER` | `#E8E2D5` | 卡片边线、表格线 |
| `SOFT` | `#F4F0E8` | pull-quote / info block 底色 |
| `LAVENDER` | `#EFE7FC` | 装饰英文（极淡） |

### 分类色（时段三色）

| 时段 | 主色 | 浅底色 |
|------|------|--------|
| 🟣 上午 · 输入 | `#7C3AED` | `#F3E8FF` |
| 🟢 下午 · 练习 | `#059669` | `#D1FAE5` |
| 🟡 晚上 · 输出 | `#D97706` | `#FEF3C7` |
| ⚫ 休息 · 切换 | `#64748B` | `#F8FAFC` |

---

## ✏️ 字体

中文：

| 角色 | 字体 | 字重 | 示例 |
|------|------|------|------|
| 大标题 | Noto Serif SC | Black (900) | "雅思自学" 60-72pt |
| 副标题 | Noto Serif SC | Regular | "从裸考一次开始" 24pt italic |
| 段落标题 | Noto Serif SC | Bold | "能不报班就别报" 18pt |
| 正文 | Noto Sans SC | Regular | 10pt 行距 16 |
| 强调正文 | Noto Sans SC | Bold | 10pt |
| caption | Noto Sans SC | Regular | 9pt italic slate |

英文 / 数字：

- 系统无衬线（Arial / Calibri）
- 装饰英文：Noto Serif SC Italic + LAVENDER 极淡色

可变字体：`NotoSerifSC-VF.ttf` / `NotoSansSC-VF.ttf`，通过 `set_variation_by_name('Black' | 'Bold' | 'Regular')` 切换权重。

---

## 📐 排版规则

### 网格

- A4 纸 / 4800×2700 图像基准
- PDF 边距 2.0 / 1.8 / 2.0 / 1.8 cm（左右上下）
- 图像边距 0.15 cm

### 节奏

- 节标题 = 数字（22pt Gold）+ 标题（22pt Ink）+ 金线（15% 宽）
- 子标题 = 13pt Ink Bold
- 段落间距 = 6pt
- 列表间距 = 2pt

### 引用（pull-quote）

```
▍ "真正的捷径只有一条：单句精听。"
  — 雅思信息透明 · AI 已能覆盖...
```

- 左侧 2pt 金色竖条
- 文字 11pt Italic，缩进左右各 0.8cm

### 表格

| 类型 | 表头 | 边线 |
|------|------|------|
| 数据表 | 黑色底白字 + 底部金色 1.2pt | Border 0.3pt |
| 元数据表 | 浅 SOFT 底 + Gold key + Ink value | Border 0.3pt |

---

## 🖼️ 视觉资产规范

| 资产 | 尺寸 (px) | 用途 |
|------|-----------|------|
| 封面 | 6000×3375 (16:9) | PDF/Word 首页全幅 |
| 信息图 | 4800×3600 (4:3) | TL;DR 全页 |
| 每日作息 | 4800×2900 (16:10) | 表格形式，PDF 单页 |
| 精听流程 | 4800×2500 (16:8.3) | 流程图 |

输出统一 PNG（DPI 200），便于嵌入。

---

## 🎯 字体粗细陷阱（已踩过）

- **Noto Serif SC 是 variable font**，`matplotlib.fontproperties.set_weight('bold')` 不生效
- **必须直接调用**：```python f.set_variation_by_name('Black') ```
- 或者用 PIL 的 `ImageFont.truetype(...).font_variant()` 强制轴

参考实现：`src/make_cover.py` 和 `src/make_infographic.py`。

---

## 🛠️ 编辑风格（Editorial）

受 **ui-ux-pro-max** 推荐：*Exaggerated Minimalism* 风格：

1. **大量留白** — 让元素呼吸
2. **单一强调色** — 金色 Gold 用作 eyebrow / 数字 / 边线，其它一律 Ink
3. **大字号 + 小副文** — 标题主导，metadata 弱化
4. **hairline 边线** — 不粗框，用 0.3-0.4pt 细线
5. **eyebrow + 金线** — 每个章节顶部：金色小标签 + 短金线
6. **左对齐为主** — 中文编辑风的灵魂

---

## 🚫 避免

- ❌ Emoji 作为图标（CJK 字体不渲染 → 豆腐块）
- ❌ 花哨渐变背景
- ❌ 蓝紫等冷色科技感配色（与「学习方法论」主题不符）
- ❌ 全角破折号混排 — 用半角 — 加空格更易读