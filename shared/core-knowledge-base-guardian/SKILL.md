---
name: core-knowledge-base-guardian
description: 墨家军核心知识库设计、审核流程、Agent读写权限管理。所有入核心库的数据必须经大威审核，Agent只能读不能写，保证数据质量。
---

# 墨家军核心知识库管理

## 核心原则

**数据库是墨家军发展壮大的基石，所有数据必须经过大威审核才能进入核心库。** Agent只能从核心库读取数据，不能修改、增加、删除。修改核心库的唯一权限在大威手中。

## 数据流转架构

```
原始数据区（无审核自动入库，Agent可写）
  ├── 小墨采集 → mojiajun.xhs_sample_library
  ├── Tavily采集 → ceramic_db.xhs_sample_library (source='tavily')
  ├── 每天自动采集 → ceramic_db 多表 (通过collector.py)
  ├── 每日热点 → ceramic_db.hot_list (7天自动清理)
  ├── 工具数据 → ceramic_db.knowledge_items (墨典知识库313条书摘)
  └── Agent学习反馈 → 各Agent本地JSON文件（待审核回写）

Agent产出区（不入原始库，审核后直接入核心库）
  ├── 墨蓝笔记 → molang_v2/molan_v2_note_*.json
  ├── 墨青封面方案 → moqing_v2/ 本地文件
  ├── 墨红质检结果 → mohong/ 本地文件
  └── 墨渊洞察 → moyuan/dual_insight.json（待审核）
        │
        ▼ 大威每日审核
        │
核心知识库（只读，所有Agent最终数据源）
  ├── core_knowledge_items — 双轨洞察（标题公式/心理开关/风格指南）
  ├── core_samples — 高质量样本（审核通过的爆款）
  └── core_library_log — 审核变更日志
        │
        ▼ 只读
所有Agent（墨渊/墨蓝/墨青/墨红/墨子/墨创/墨金）
```

## 审核流程

1. **原始数据自动入库**（无审核）
2. **小川每日整理审核清单** → 存到 `墨家军资料库/审核清单/YYYY-MM-DD_核心库审核清单.md`
3. **大威逐项确认**（同意/修改/否决）
4. **小川执行写入核心库**
5. **核心库更新后**，所有Agent下次调用时自动读到最新数据

## 审核清单格式

审核清单必须包含以下分类：

### 一、墨渊双轨学习洞察 → core_knowledge_items
- **术轨：爆款标题公式**（公式名、示例标题、数据支撑：点赞/收藏/评论）
- **术轨：风格指南**（语气、标题长度、正文格式、封面类型、禁忌）
- **道轨：心理开关**（名称、说明）
- **道轨：内容原则**（原则描述）

### 二、Agent产出的笔记/封面/方案 → core_samples
- 标题、内容摘要、风格评价

### 三、原始数据概况（参考信息，不入库）
- 各数据源条数统计

每项后面标注「□ 同意 □ 修改/否」，大威确认后执行。

## Agent读写权限矩阵

| Agent | 原始数据区 | 核心知识库 |
|:------|:---------|:---------|
| 小墨 | ✅ 写 | ❌ 只读 |
| Tavily采集器 | ✅ 写 | ❌ 只读 |
| 墨渊 | ✅ 读(分析用) | ✅ 只读 |
| 墨蓝(内容创作) | ❌ | ✅ 只读 |
| 墨青(封面) | ❌ | ✅ 只读 |
| 墨红(质检) | ❌ | ✅ 只读 |
| 墨子(报告) | ❌ | ✅ 只读 |
| 墨创(策划) | ❌ | ✅ 只读 |
| 墨金(创新) | ❌ | ✅ 只读 |
| 大威/小川 | ✅ 读写 | ✅ 读写 |

## 核心知识库表结构

### core_knowledge_items
```sql
CREATE TABLE IF NOT EXISTS core_knowledge_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    category VARCHAR(50) NOT NULL COMMENT '分类：title_formula/psych_switch/style_guide/content_principle/topic',
    title VARCHAR(200) NOT NULL COMMENT '知识标题',
    content TEXT NOT NULL COMMENT '知识内容',
    source VARCHAR(50) DEFAULT NULL COMMENT '来源：墨渊/墨蓝/墨红/小墨/Tavily',
    evidence TEXT DEFAULT NULL COMMENT '证据/数据支撑（点赞量、收藏量等）',
    status VARCHAR(20) DEFAULT 'pending' COMMENT '状态：pending/active/archived/deprecated',
    reviewed_by VARCHAR(50) DEFAULT '大威',
    reviewed_at DATETIME DEFAULT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_category (category),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

### core_samples
```sql
CREATE TABLE IF NOT EXISTS core_samples (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
    content TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
    source VARCHAR(50) DEFAULT NULL,
    likes INT DEFAULT 0,
    collects INT DEFAULT 0,
    comments INT DEFAULT 0,
    sample_type VARCHAR(50) DEFAULT NULL,
    tags VARCHAR(500) DEFAULT NULL,
    review_note TEXT DEFAULT NULL,
    reviewed_by VARCHAR(50) DEFAULT NULL,
    reviewed_at DATETIME DEFAULT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_type (sample_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

## 审核清单存放路径

```
/Users/jaywell/Desktop/墨家军资料库/墨家军产出文件/审核清单/
```

文件名格式：`YYYY-MM-DD_核心库审核清单.md`

## 双轨洞察分发机制（墨渊产出 → 各Agent）

墨渊分析完数据后，将双轨洞察**同时分发到以下位置**，供各Agent调用：

| Agent | 接收文件路径 | 内容 |
|:------|:-----------|:-----|
| 墨蓝 | `agent_outputs/molang_v2/dual_insight_inject.txt` | 标题公式+风格指南+心理开关（直接注入创作prompt） |
| 墨青 | `agent_outputs/moqing_v2/dual_insight.txt` | 风格指南+色彩方案 |
| 墨红 | `agent_outputs/mohong/dual_insight.txt` | 质检标准（哪些是禁区） |

分发脚本：`dual_insight_and_inject.py`（同时写3份 + 保存master到moyuan/dual_insight.json）

**重要**：这些本地文件只是临时缓存。永久存储必须走审核流程写入核心库的core_knowledge_items表。

## 素材库（不入核心库，创作参考用）

对于时效性短或内容类型不适合核心库的数据（如旅游攻略、时事新闻、通用网页爬取内容），建单独的 `material_library` 表存放。区分：核心库 Agent 自动调用，素材库手动参考。

## 核心库建表语句（已验证可执行）

```sql
-- 1. 双轨洞察核心库
CREATE TABLE IF NOT EXISTS core_knowledge_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    category VARCHAR(50) NOT NULL COMMENT '分类',
    title VARCHAR(200) NOT NULL COMMENT '知识标题',
    content TEXT NOT NULL COMMENT '知识内容',
    source VARCHAR(50) DEFAULT NULL COMMENT '来源',
    evidence TEXT DEFAULT NULL COMMENT '数据支撑',
    status VARCHAR(20) DEFAULT 'pending' COMMENT '状态: pending/active/archived',
    reviewed_by VARCHAR(50) DEFAULT NULL COMMENT '审核人',
    reviewed_at DATETIME DEFAULT NULL COMMENT '审核时间',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_category (category),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. 高质量样本库
CREATE TABLE IF NOT EXISTS core_samples (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
    content TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
    source VARCHAR(50) DEFAULT NULL,
    likes INT DEFAULT 0,
    collects INT DEFAULT 0,
    comments INT DEFAULT 0,
    sample_type VARCHAR(50) DEFAULT NULL,
    tags VARCHAR(500) DEFAULT NULL,
    review_note TEXT DEFAULT NULL,
    reviewed_by VARCHAR(50) DEFAULT NULL,
    reviewed_at DATETIME DEFAULT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_type (sample_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3. 审核变更日志
CREATE TABLE IF NOT EXISTS core_library_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    action_type VARCHAR(50) NOT NULL,
    source_table VARCHAR(100) DEFAULT NULL,
    source_id INT DEFAULT NULL,
    target_table VARCHAR(100) DEFAULT NULL,
    target_id INT DEFAULT NULL,
    summary TEXT DEFAULT NULL,
    reviewed_by VARCHAR(50) DEFAULT NULL,
    reviewed_at DATETIME DEFAULT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

## 要避免的坑

1. **不要直接写库** — 任何Agent产出都必须先经过大威审核才能写入核心库
2. **不要给Agent写权限** — Agent只能读核心库，不能写
3. **不要删除原始数据** — 原始区数据保留用于追溯
4. **不要跳过审核环节** — 即使是墨渊的分析结果也要审核
5. **审核清单要写清楚数据来源和证据** — 大威需要知道"为什么这个数据值得入库"
