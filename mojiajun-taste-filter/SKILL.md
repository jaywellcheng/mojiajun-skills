---
name: mojiajun-taste-filter
description: 墨家军信息入口5维评分过滤器 — 采集入库后自动用DeepSeek对每条信息做相关性/价值/深度/可转化性/新鲜度评分，决定distill/save/title_only/discard
category: mojiajun
---

# 墨家军 Taste Filter

基于大威「自我进化」方法论第1步：信息入口过滤。不是所有信息都值得进系统。

## 5维评分标准

| 维度 | 说明 | 1-5分 |
|:---|:---|:---|
| 相关性 | 和品牌方向（陶瓷/手作/AI/内容创作）相关程度 | 5=直接相关 |
| 当前价值 | 是否服务当前项目（小红书/漫画/AI系统） | 5=立刻能用 |
| 深度 | 是否有方法论/案例/实践细节 | 5=系统方法论+案例 |
| 可转化性 | 能否变成Memory/Skill/素材 | 5=多维可转化 |
| 新鲜度 | 是否提供新视角 | 5=全新视角 |

## 判定规则

| 总分 | verdict | 动作 |
|:---|:---|:---|
| 20-25 | distill | 精读并蒸馏 |
| 15-19 | save | 快速阅读并记录 |
| 10-14 | title_only | 暂存标题 |
| <10 | discard | 丢弃 |

## 部署文件

- **模块**: `/home/ubuntu/mojiajun-queue/taste_filter.py`
- **集成点**: `agent_outputs/collector.py` 的 `run_collect()` 末尾，采集完成后自动调用 `run_filter(batch_size=30)`
- **数据库**: `ceramic_db.xhs_sample_library` 新增8个字段

## 数据库字段

```sql
ALTER TABLE xhs_sample_library 
  ADD COLUMN taste_score INT DEFAULT NULL,
  ADD COLUMN taste_relevance INT DEFAULT NULL,
  ADD COLUMN taste_value INT DEFAULT NULL,
  ADD COLUMN taste_depth INT DEFAULT NULL,
  ADD COLUMN taste_transform INT DEFAULT NULL,
  ADD COLUMN taste_freshness INT DEFAULT NULL,
  ADD COLUMN taste_verdict VARCHAR(20) DEFAULT NULL,
  ADD COLUMN taste_scored_at DATETIME DEFAULT NULL;
```

## 使用方式

```bash
# 手动评分（未评分条目）
cd /home/ubuntu/mojiajun-queue && python3 taste_filter.py --batch 20

# 查看评分分布
python3 taste_filter.py --show-verdicts

# 集成：collector.py采集完成后自动触发
# 已在 run_collect() 末尾注入 try/except 调用 run_filter(batch_size=30)
```

## 验证方法

```bash
# 跑3条测试
ssh core01 'cd /home/ubuntu/mojiajun-queue && python3 taste_filter.py --batch 3'

# 查看分布
ssh core01 'cd /home/ubuntu/mojiajun-queue && python3 taste_filter.py --show-verdicts'

# 查看具体评分
ssh core01 "docker exec -i ceramic-mysql mysql -u root -pceramic_2026 \
  --default-character-set=utf8mb4 ceramic_db \
  -e \"SELECT id, title, taste_score, taste_verdict FROM xhs_sample_library \
  WHERE taste_score IS NOT NULL ORDER BY taste_score DESC LIMIT 10;\""
```

## 实测数据（首批23条）

| verdict | count | avg_score |
|:---|:---|:---|
| save | 2 | 17.5 |
| title_only | 4 | 11.8 |
| discard | 17 | 5.2 |

说明：Tavily采集的大部分是好物分享/食品测评等无关内容（正确过滤），陶瓷相关条目被保留。

## 已知问题

- DeepSeek评分有随机性，同一标题两次评分可能差1-2分
- 品牌上下文写死在prompt里，如果品牌方向变了需更新 `BRAND_CONTEXT`
- 未集成到 mojiajun.xhs_sample_library（小墨采集的数据），只覆盖 ceramic_db
