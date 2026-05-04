---
name: mojiajun-content-audit-system
description: 墨家军内容审核完整系统——109词红线词库(6大类别)+pre_publish_check函数+dispatch参数修复+端到端验证方法。用于审核驳回→自动重写回路。
version: 1.0.0
tags:
  - mojiajun
  - audit
  - redline
  - content-review
  - pre-publish
---

# 墨家军内容审核系统

## 概述

完整的内容审核系统，包含：
1. CORE-01审核回路hook（agent_worker.py L216-L217之间）
2. 109词红线词库（6大类别，基于小红书社区规范+广告法）
3. pre_publish_check函数（单篇笔记发布前审核）
4. dispatch参数修复

## 架构

```
Agent → 创作 → module dispatcher → pre_publish_check()
                                     ├─ passed=true → 通过
                                     └─ passed=false → hook生成重写任务
```

## ⚠️ 关键陷阱：dispatch 参数提取

`module_dispatcher.py` L195：
```python
# ❌ 错误（只取payload.args，其他模块兼容但审核任务不工作）
func_args = payload.get("args", {})
# ✅ 正确（无args时fallback到整个payload）
func_args = payload.get("args", payload) if isinstance(payload, dict) else {}
```

此bug导致pre_publish_check收到空参数，红线词永远不命中。2026-04-27已修复。

## 红线词库（109词，6大类）

| 类别 | 数量 | 示例 |
|------|------|------|
| 引流诱导 | 25词 | 加微信、私信我、主页有惊喜、扫码 |
| 夸大虚假 | 28词 | 最好、第一、100%有效、包治百病 |
| 医疗功效 | 23词 | 治疗、祛斑、消炎、抗衰老 |
| 虚假激励 | 14词 | 月入过万、躺赚、兼职、刷单 |
| 营销硬广 | 14词 | 限时特惠、错过等一年、赶紧入手 |
| 煽情腔 | 7词 | 泪目了、破防了、美哭了 |

## 部署位置

| 文件 | 路径 |
|------|------|
| 审核回路hook | CORE-01:/home/ubuntu/mojiajun-queue/agent_worker.py L216-L217 |
| 词库+审核函数 | CORE-01:/home/ubuntu/mojiajun-queue/agent_outputs/mohong/style_auditor.py |
| dispatch修复 | CORE-01:/home/ubuntu/mojiajun-queue/module_dispatcher.py L195 |

## 验证方法

```bash
# 直接测试审核函数
ssh ubuntu@159.75.12.11 "cd /home/ubuntu/mojiajun-queue && python3 -c '
from module_dispatcher import dispatch
r = dispatch(\"pre_publish_check\", {\"title\":\"测试\",\"body\":\"含加微信\",\"tags\":[]}, \"mohong\")
print(r[\"result\"][\"passed\"], r[\"result\"][\"redline_hits\"])
'"
```

## 恢复步骤

Mac重建后：
1. 确认3个文件包含最新代码
2. 清理pyc缓存
3. 重启workers
4. 插入测试任务验证
