# task_queue 真实表结构（2026-05-13 实测确认）

⚠️ **重要：不要假设task_id是自增INT！它是VARCHAR UNIQUE，调用方需生成UUID。**

## 完整字段

| 字段 | 类型 | Null | Key | 说明 |
|------|------|:----:|:---:|------|
| id | int | NO | PRI | 自增（内部用，不对外暴露） |
| task_id | varchar(64) | NO | UNI | **UUID，非自增** |
| parent_sub_task_id | varchar(64) | YES | | 父子任务关联 |
| depends_on | varchar(64) | YES | MUL | 依赖的任务ID |
| source | varchar(32) | YES | | 来源，默认xiaochuan |
| target_agent | varchar(32) | **NO** | MUL | **必填！** |
| task_type | varchar(64) | **NO** | | 任务类型 |
| payload | json | YES | | 任务参数 |
| priority | int | YES | | 默认0 |
| status | enum('triage','pending','processing','deferred','completed','failed','blocked') | YES | MUL | 默认triage |
| timeout_seconds | int | YES | | 默认300 |
| retry_count | int | YES | | 默认0 |
| max_retries | int | YES | | 默认3 |
| created_at | timestamp | YES | MUL | |
| claimed_at | timestamp | YES | | |
| completed_at | timestamp | YES | | |
| result | json | YES | | 执行结果 |
| error_message | text | YES | | 错误信息 |
| last_error | text | YES | | |
| progress | int | YES | | 0-100 |
| checkpoint_data | json | YES | | |
| last_progress_update | timestamp | YES | | |
| current_command | text | YES | | |
| cost_cny | decimal(8,2) | YES | | |
| acceptance_criteria | json | YES | | |
| prompt_override | text | YES | | |
| attempt_log | json | YES | | |

## INSERT必备字段（最小集）

```sql
INSERT INTO task_queue 
  (task_id, task_type, status, payload, target_agent, timeout_seconds, source, created_at) 
VALUES 
  ('gen-uuid-here', 'code_exec', 'pending', '{"key":"val"}', 'moma', 300, 'api_bridge', NOW());
```

## 关键踩坑（2026-05-13）

| 坑 | 后果 | 正确做法 |
|:---|:-----|:---------|
| 假设task_id是自增INT | SQL报错，写入失败 | 调用方生成UUID |
| 漏了target_agent（NOT NULL） | SQL报错 | 总是设置默认值如'xiaochuan' |
| 以为status默认值是'pending' | 默认是'triage'，agent_worker不消费 | 显式设status='pending' |
| payload格式不对 | agent_worker解析失败 | 确保是合法JSON |
