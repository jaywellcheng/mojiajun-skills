---
name: design-taste-extraction-for-ai
description: 从Refero等设计参考库提取顶级品牌设计系统，提炼为AI Agent可直接注入Prompt的色板/字体/质感/空间规则。适用于品牌视觉体系建设、MJ/GPT Image 2封面Prompt优化。天青浅品牌实战验证。
source: https://styles.refero.design
verified: 2026-05-04 天青浅品牌 — 13风格 → 5级色板 + 6条铁律
---

# 设计审美提取——为 AI Agent 注入设计品味

## 方法论（5步）

### Step 1: 筛选匹配风格
在 `styles.refero.design` 搜索品牌调性关键词（warm/earthy/botanical/craft/artisan/luxury/editorial）。精选标准：tagline 读起来像品牌的视觉 slogan。

### Step 2: 批量提取 DESIGN.md
风格页 URL 格式：`styles.refero.design/style/{uuid}`。用 web_extract 取完整数据：色彩 Hex+角色、字体家族+字阶、间距刻度、圆角、组件参数。

### Step 3: 提炼 5 级色彩体系
```
底色(暖白/米白) → 次底色(暖灰/砂岩) → 主文字(深棕/墨绿) → 强调色(陶土/鼠尾绿) → 点缀色(极少)
```
铁律：禁用纯黑#000/纯白#fff，禁用投影，禁用超过5种颜色。

### Step 4: 提炼质感铁律
跨风格找共性。天青浅实测：15/15 个顶级品牌全部回避 drop-shadow，层次用背景微调。

### Step 5: 注入 Prompt 生成器
色板 Hex → MJ/GPT Image 2 英文关键词映射表，写入 cover-prompt-crafter。

## 天青浅实战（2026-05-04）

- 扫描：2000+ 风格 → 精选 13 个
- 产出：5 级色板 + 6 条铁律 + MJ 关键词映射表
- 交付物：`tianqing-design-references.md`（已部署双端）
- cover-prompt-crafter 已接入品牌色板

## 踩坑

1. Refero 是 SPA，详情页需要直接请求 style/{uuid} URL
2. 纯黑纯白 = 廉价感，15 个顶级品牌 0 个用
3. "with soft shadows" = AI 味，真实品牌不用投影
4. 色板每个颜色必须标注角色（底色/次底色/文字/强调/点缀）
