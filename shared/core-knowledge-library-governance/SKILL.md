---
name: core-knowledge-library-governance
description: 墨家军核心知识库治理体系——数据分级、审核流程、Agent读写权限矩阵、每日审核清单规范
category: mojiajun
---

# 核心知识库治理体系

## 核心原则

1. **数据库是发展壮大的关键基石**——只有大威审核通过的数据才能入核心库
2. **核心库只读不写**——所有Agent只能读核心库，写入/修改/删除只有大威/小川有权限
3. **数据分三区存储**——原始数据区（自动写入）→ 审核区（待确认）→ 核心库（审核通过）
4. **素材库另存**——旅游攻略/时事/低粉爆款等时效性短或质量不够核心库的数据，另存material_library表，Agent创作时参考但不自动调用

## 数据分区

### 原始数据区（不入核心库，自动写入）
| 数据来源 | 存放位置 | 谁写 | 特点 |
|:--------|:--------|:----|:----|
| 小墨采集爆款 | mojiajun.xhs_sample_library | 小墨 | 带互动数据（赞/藏/评），但可能有重复 |
| Tavily自采集 | ceramic_db.xhs_sample_library | 墨橙/采集器 | 通用搜索数据，不带小红书互动数据 |
| Agent学习反馈 | ceramic_db.xhs_sample_library | 墨渊/墨蓝/墨红 | 标记source为对应Agent名 |

### 核心知识库（只读，仅大威审核后写入）
| 表 | 存储内容 | 读取权限 |
|:---|:--------|:--------|
| core_knowledge_items | 200多本书精华 + 墨渊双轨洞察 + 陶瓷工艺知识 | 所有Agent只读 |
| core_samples | 高质量爆款样本（陶瓷/卖货，大威审核后） | 所有Agent只读 |
| core_library_log | 入库操作日志 | 小川/大威 |

### 素材库（创作参考，Agent不自动调用）
| 表 | 存储内容 |
|:---|:--------|
| material_library | 旅游攻略/景德镇时事/低粉爆款/Tavily通用卖货 |

## 审核流程

### 每日审核清单
每天小川整理原始数据，产出审核清单发给大威确认。

**审核清单结构：**
1. 墨渊双轨洞察（标题公式/风格指南/心理开关/内容原则）
2. 新采集爆款样本（按分类列，每条带互动数据）
3. Agent学习反馈（墨蓝笔记/墨红质检等）
4. 其他待审核内容

**审核清单格式示例：**

```
📋 今日需审核内容（日期）

1. 墨渊 | 双轨洞察更新
   - 新增标题公式：情绪反转型（共5条）
   - 新增心理开关：锚定效应
   ⏳ 等你确认

2. 墨蓝 | 新笔记《xxx》
   - 标题：...
   - 正文：300字
   ⏳ 等你确认
```

### 审核规则
- **双轨学习洞察**（标题公式/风格指南/心理开关/内容原则）→ 大威确认后入 `core_knowledge_items`
- **墨蓝/墨青产出** → 先过墨红质检，再发给大威确认，通过后入 `core_samples`
- **墨红质检结果** → 直接入原始区（本身就是训练数据），入核心库需大威确认
- **墨渊分析结果** → 直接入原始区，入核心库需大威确认
- **小墨/Tavily原始数据** → 自动入原始区，筛选后经大威确认入核心库
- **热点数据**（hot_list） → 不入核心库，保留7天后自动清理

## Agent读写权限矩阵

| Agent | 原始数据区 | 核心知识库 |
|:------|:---------|:---------|
| 小墨 | ✅ 写 | ❌ 只读 |
| Tavily采集器 | ✅ 写 | ❌ 只读 |
| 墨渊 | ✅ 读 | ✅ 只读 |
| 墨蓝 | ❌ | ✅ 只读 |
| 墨青 | ❌ | ✅ 只读 |
| 墨红 | ❌ | ✅ 只读 |
| 墨子 | ❌ | ✅ 只读 |
| 墨创 | ❌ | ✅ 只读 |
| 墨金 | ❌ | ✅ 只读 |
| **大威/小川** | ✅ 读写 | ✅ 读写 |

## 入库执行

```python
# 双轨洞察入核心库
INSERT INTO core_knowledge_items (category, title, content, source, status, reviewed_by)
VALUES ('title_formula', '情绪反转型', '说明...', '墨渊', 'active', '大威')

# 样本入核心库
INSERT INTO core_samples (title, likes, collects, comments, source, sample_type)
VALUES ('标题', 10000, 5000, 300, '小墨', '陶瓷')
```

## 去重规则

小墨采集的数据常有重复（同一条数据多次入库），入核心库前必须去重：
- 按标题前20字去重
- 互动数据（赞/藏/评）相近的视为重复
- 去重后产出的才是真实不重复的样本数量

## 核心库建表SQL

```sql
CREATE TABLE core_knowledge_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    category VARCHAR(50) NOT NULL COMMENT '分类：title_formula/psych_switch/style_guide/content_principle/topic/knowledge',
    title VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,
    source VARCHAR(50) DEFAULT NULL,
    evidence TEXT DEFAULT NULL,
    status VARCHAR(20) DEFAULT 'active',
    reviewed_by VARCHAR(50) DEFAULT NULL,
    reviewed_at DATETIME DEFAULT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_category (category),
    INDEX idx_status (status)
);

CREATE TABLE core_samples (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    content TEXT DEFAULT NULL,
    source VARCHAR(50) DEFAULT NULL,
    likes INT DEFAULT 0,
    collects INT DEFAULT 0,
    comments INT DEFAULT 0,
    sample_type VARCHAR(50) DEFAULT NULL,
    tags VARCHAR(500) DEFAULT NULL,
    reviewed_by VARCHAR(50) DEFAULT NULL,
    reviewed_at DATETIME DEFAULT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_type (sample_type)
);
```

## 注意事项
- 小墨之前的数据正文只有几十字摘要，没有完整笔记正文。后续采集需加上全文。
- 分类越细Agent查询越快。200多本书精华导入时按书名关键词匹配分类。
- 不要一上来就跑全自动化——先人工审核保证核心库质量，以后数据质量高了再考虑自动化。
