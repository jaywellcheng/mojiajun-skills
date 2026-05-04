---
name: mojiajun-memdir
description: 墨家军memdir记忆目录系统——将臃肿的单一MEMORY.md拆分为独立文件+INDEX.md索引，按content/user/system分类，支持智能截断
version: 1.0.0
author: 小川 (林青川)
---

# 墨家军 memdir 记忆目录系统

借鉴 Claude Code 的 memdir 设计，将墨家军知识从单一 MEMORY.md 拆分为规范的文件目录结构。

## 目录结构

```
/home/ubuntu/mojiajun-queue/knowledge/
├── INDEX.md              ← 知识索引（200行/25KB上限）
├── content/              ← 内容策略记忆
│   ├── title_formulas.md
│   ├── hot_patterns.md
│   ├── failure_cases.md
│   ├── content_calendar.md
│   └── platform_rules.md
├── user/                 ← 大威偏好+品牌记忆
│   ├── brand_identity.md
│   ├── style_prefs.md
│   ├── review_feedback.md
│   └── persona.md
├── system/               ← 系统运维记忆
│   ├── architecture.md
│   ├── agent_configs.md
│   ├── bug_fixes.md
│   └── deploy_log.md
└── market/               ← 市场数据记忆
    ├── competitors.md
    ├── trends.md
    └── pricing.md
```

## 文件规范

### 每个记忆文件格式
```markdown
---
type: content|user|system|market
created: 2026-04-28
updated: 2026-04-28
---

# 标题

具体内容...
```

### INDEX.md 格式
每行一个索引条目：`- [标题](分类/文件名.md) — 一句话描述`

## 智能截断规则
- INDEX.md: 200行上限 + 25KB上限
- 先按行截断→再按字节截断→在最后一个完整换行处截断
- 超限时追加警告信息

## 工具脚本
- scripts/memdir_init.py — 初始化/迁移现有MEMORY→memdir
- scripts/memdir_add.py — 添加新记忆
- scripts/memdir_search.py — 搜索记忆

## 与autoDream配合
memdir就位后，autoDream可以自动回顾和更新这些文件，实现自主学习。
