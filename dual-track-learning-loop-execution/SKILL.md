---
name: dual-track-learning-loop-execution
description: 墨家军双轨学习闭环实际执行流程——从多库数据查询、墨渊分析提炼术轨道轨洞察、分发到各Agent、内容创作、质检、到核心知识库审核入库的完整可重复流程
---

# 双轨学习闭环执行流程（2026-04-27实战验证）

## 一、数据来源

两个数据库：
- **mojiajun库**（小墨采集）：含真实互动数据（likes/collects/comments）的爆款样本
  - 表: `xhs_sample_library`（167条可用）
  - 表: `xhs_explosive_notes`（94条）
- **ceramic_db库**（Tavily自采+墨典知识库）：通用搜索数据+书摘
  - 表: `xhs_sample_library`（148条）
  - 表: `knowledge_items`（313条书籍精华）
  - 表: `core_knowledge_items`（核心知识库，已审核）

## 二、查询关键——中文编码问题

在docker mysql中使用中文查询时必须加 `--default-character-set=utf8mb4`：
```bash
docker exec -i ceramic-mysql mysql -u root -pceramic_2026 --default-character-set=utf8mb4 ceramic_db -e "SELECT ..."
```

Python通过pymysql连接时也要设 `charset="utf8mb4"`。

## 三、墨渊分析

从两个库拉数据，提炼术轨（爆款标题公式/风格指南）和道轨（心理开关/内容原则）：

```python
# 术轨：从mojiajun库拉带互动数据的爆款
query(DB_MOJIAJUN, "SELECT title, likes, collects, comments FROM xhs_sample_library WHERE sample_type IN ('陶瓷','景德镇') AND likes > 1000 ORDER BY likes DESC")

# 道轨：从ceramic_db库拉理论
query(DB_CERAMIC, "SELECT content FROM knowledge_items WHERE content LIKE '%用户心理%' OR content LIKE '%内容营销%'")
```

## 四、洞察分发到Agent

分析结果存两份：
1. JSON文件入库 (`moyuan/dual_insight.json`)
2. 文本文件注入每个Agent目录（`dual_insight_inject.txt`）

**Agent模块路径**（2026-04-27确认）：
- 根目录: `/home/ubuntu/mojiajun-queue/agent_outputs/`
- Agent子目录: `molan`, `moqing`, `mochuang`, `mojin`, `mozi`, `mohong`, `moyuan`, `molang_v2`, `moqing_v2`
- 注入文件: `dual_insight_inject.txt`

**分发脚本部署**（gzip+base64法，避免中文路径和转义问题）：
```python
import gzip, base64
compressed = base64.b64encode(gzip.compress(script.encode())).decode()
terminal(f"ssh user@host 'echo {compressed} | base64 -d | gunzip > /path/script.py && python3 /path/script.py'")
```

数据源: `ceramic_db.core_knowledge_items` 表，用户心理215条、title_formula/psych_switch/style_guide等是关键分发类别。

## 五、核心知识库结构

三张表在ceramic_db库：
- `core_knowledge_items` — 双轨学习洞察（可读知识）
- `core_samples` — 高质量爆款样本（可读样本）
- `core_library_log` — 审核操作日志

权限设计：所有Agent**只能读**，只有小川/大威能写。
审核流程：小川每日发审核清单 → 大威确认 → 小川执行写入。

## 七、Agent全链路跑通状态（2026-04-27）

| Agent | 角色 | 状态 | 说明 |
|:------|:-----|:----|:-----|
| 墨渊 | 数据科学家 | ✅ | 双轨分析、洞察产出、分发所有Agent |
| 墨蓝 | 内容创作者 | ✅ | 接入DeepSeek，注入双轨洞察后完整产出笔记 |
| 墨青 | 视觉设计师 | ✅ | 爆款封面方案生成，风格匹配 |
| 墨红 | 质检员 | ✅ | 审计Agent产出质量，评分+建议 |
| 墨子 | 仪表盘 | ✅ | HTML看板，展示核心库状态 |
| 墨创 | 策略参谋 | ⚠️ | 可产出计划，但数据源需切换 |
| 墨金 | 创新引擎 | ❌ | topic_miner未调用 |

## 八、陷阱笔记

1. **双库问题**：mojiajun库和ceramic_db库都存了xhs_sample_library，字段结构不同，查询时必须注意哪个库。
2. **Json序列化**：Python脚本ssh到服务器执行时，避免在`-c`参数里嵌套f-string，否则引号转义会报错。用写文件→scp→远程执行 三步法。
3. **.env文件**：配API Key时不要用echo展开变量（`echo "KEY=$KEY"`），要直接用明文值写入，否则可能被截断。
4. **墨蓝v2模块**：`generate_story_note()` 原版只输出创作上下文（占位），不改代码不会调用AI生成。需要在engine.py里接入DeepSeek API调用。
5. **墨红审核**：`audit_style()` 的参数是 `target_agent` 和 `days`，不是传笔记内容对象。它是审计Agent产出的，不是审核单篇笔记。
