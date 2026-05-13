---
name: mojiajun-auto-capability-pipeline
description: 墨家军能力自动化流水线 — 日报发现→编排器生成任务→AS1/AS2执行→墨码审核→小川部署
version: 1.0.0
tags: [mojiajun, automation, pipeline, capability]
---

# 墨家军能力自动化流水线

## 概述
从 AI 日报中发现新能力 → 自动生成开发任务 → 派发给 AS1/AS2 → 墨码审核 → 小川部署，全链路自动化，减少人工调度。

## 流水线结构

```
09:00 cron → daily_ai_briefing.py（搜索+分析）
09:30 cron → capability_orchestrator.py（提取任务→写task_queue）
手动/定时 → AS1/AS2 读 task_queue 执行
手动/定时 → 墨码审核产出
最终     → 小川部署
```

## 核心组件

### 1. 日报系统
- 位置：`/home/ubuntu/mojiajun-queue/tools/daily_ai_briefing.py`
- cron：`0 9 * * *`
- 功能：搜索5关键词 × Tavily → DeepSeek V4 分析 → 邮件推送

### 2. 编排器
- 位置：`/home/ubuntu/mojiajun-queue/tools/capability_orchestrator.py`
- cron：`30 9 * * *`
- 功能：读日报 → DeepSeek 提取可执行任务 → 写 task_queue/*.json

### 3. 任务队列
- 目录：`/home/ubuntu/mojiajun-queue/task_queue/`
- 格式：`pending_YYYY-MM-DD.json`
```json
[{
  "task_id": "T001",
  "title": "...",
  "description": "...",
  "assignee": "as1|as2",
  "priority": "high|medium|low",
  "status": "pending"
}]
```

### 4. 搜索API
- 端点：`POST /api/search` @ CORE-01:8080
- 代码：`/home/ubuntu/mojiajun-queue/tools/search_aggregator.py`

## AS1/AS2 分工

| Agent | 位置 | 引擎 | 适合任务 |
|-------|------|------|----------|
| AS1 | Mac ~/cc1-workspace | Aider+DeepSeek | 本地脚本、设计工具 |
| AS2 | CORE-01 as2-workspace | Aider+DeepSeek | 后端API、数据库 |

### AS1 启动
```bash
cd ~/cc1-workspace
export OPENAI_API_KEY="sk-xxx"
export OPENAI_API_BASE="https://api.deepseek.com"
aider <file> --message "..." --yes
```

### AS2 启动
```bash
ssh core01
cd ~/as2-workspace
export OPENAI_API_KEY="sk-xxx"
export OPENAI_API_BASE="https://api.qnaigc.com"
aider <file> --message "..." --yes
```

## 已知限制
- DeepSeek Chat 在 Aider 的 diff edit-format 下文件名输出不稳定 → 优先用 whole format
- 复杂API调用代码（需要精确格式）建议小川直接写，AS1/AS2 做部署和测试
- AS1/AS2 目前需手动启动，自动拉任务机制待建

## 环境变量
```bash
# CORE-01 .env 需包含：
TAVILY_API_KEY=tvly-xxx
DEEPSEEK_API_KEY=sk-xxx
QQ_MAIL_PASS=xxx
```
