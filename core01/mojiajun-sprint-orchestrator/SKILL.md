---
name: mojiajun-sprint-orchestrator
description: 墨家军Sprint编排器——5阶段流水线(分析→策划→创作→质检→通知) + 4道硬门控 + 双重检查机制，cron驱动状态机，JSON文件传递数据。
version: 1.1.0
tags:
  - mojiajun
  - sprint
  - pipeline
  - content-production
  - gate
---

# 墨家军 Sprint 编排器 — 5阶段流水线

## 架构

5阶段状态机，cron每30秒推进一次：
```
idle → ①分析(moyuan) → ②策划(mochuang) → ③创作(molan) → ④质检(mohong) → ⑤通知 → done
```

所有阶段通过 JSON 文件传递数据，不依赖 task_queue 的 payload 跨阶段传参。

## 数据流

| 阶段 | task_type | 输入 | 输出 |
|------|-----------|------|------|
| ① 分析 | python_code | MySQL task_queue + INDEX.md | `agent_outputs/moyuan/latest_analysis.json` |
| ② 策划 | python_code | `latest_analysis.json` | `agent_outputs/mochuang/latest_plan.json` |
| ③ 创作 | python_code | `latest_plan.json` | `agent_outputs/molan/latest_note.json` |
| ④ 质检 | python_code | `latest_note.json` | `agent_outputs/mohong/latest_audit.json` |
| ⑤ 通知 | python_code | 所有产出 | 打印 summary JSON |

## 关键设计决策

### ③④ 为什么不用 module_dispatcher 的 task_type？

最初设计 phase ③用 `xiaohongshu_note`、④用 `quality_audit`，通过 module_dispatcher 路由到 molan/mohong 模块。但 module_dispatcher 只传 payload 的 `args` 字段给模块函数，无法传递上一阶段的产出数据。

**解决方案**：改为 `python_code` task_type，嵌入桥接代码：
- ③ 先读 `latest_plan.json` → 提取 topic/tone/outline 等参数 → 调 `molan.create(**params)` → 保存结果
- ④ 先读 `latest_note.json` → 调 `mohong.audit_style(target_agent="molan")` → 保存结果

### Python 内嵌代码的引号规则（重要踩坑）

编排器把每个阶段的 Python 代码作为字符串常量嵌入。关键规则：

**外层的 triple-quote 类型必须避开内嵌代码中出现的 triple-quote。**

- 如果内嵌代码包含 `f"""..."""` 或 `"""docstring"""` → 外层用 `r'''...'''`
- 如果内嵌代码只用单引号 → 外层可用 `r"""..."""`
- 绝不混用：`r'''` 开头不能 `"""` 收尾，反之亦然

```python
# ✅ 正确：内嵌有 f""" → 外层用 r'''
STAGE_CODE = r'''
prompt = f"""hello {name}"""
print(output)
'''

# ❌ 错误：外层 r""" 被内嵌 f""" 提前关闭
STAGE_CODE = r"""          # ← 这里开始
prompt = f"""hello {name}"""  # ← 这个 """ 提前关闭了外层！
"""                        # ← 这个变成独立字符串，语法错误
```

## 门控机制（4道硬门控）

每个阶段完成后，`check_gate()` 检查产出质量，不通过则回退/重试：

| 阶段 | 门控条件 | 扣分项 | 不通过动作 |
|------|---------|--------|-----------|
| analysis | ≥3条洞察 | <3条→分=条数×33 | auto_retry |
| planning | ≥2标题+大纲>20字 | 缺一项→分减半 | auto_retry |
| creation | 300-1000字+有标题 | 字数/标题缺→分=0 | rework_retry |
| audit | 质检分≥70 | <70→不通过 | reject_rewrite |
| notify | 无门控 | 始终通过 | ignore |

代码位置：sprint_orchestrator.py `check_gate()` 函数 (line ~836-920)

## ⚠️ 双重检查 Bug (2026-05-01 修复)

**问题**：worker 执行完脚本就设 `task_queue.status="completed"`，即使内部墨蓝报错 (exit_code=1)。编排器只看 `task_queue.status` → 错误推进到下一阶段，绕过门控。

**修复**：`advance_stage()` 第513行加"剥洋葱"检查：
```python
if task_status == "completed":
    # 双重检查：worker completed ≠ 内容成功
    result = task.get("result", {})
    if isinstance(result, dict):
        inner_status = result.get("status", "")
        inner_exit = result.get("exit_code", 0)
        if inner_status == "error" or (isinstance(inner_exit, int) and inner_exit != 0):
            handle_stage_failure(state, stage_name, task)
            return
    handle_stage_success(state, stage_name, task)
```

## 部署位置

- 文件：`/home/ubuntu/mojiajun-queue/sprint_orchestrator.py` (CORE-01, ~920行)
- 本地同步：`墨家军资料库/05_模块代码/sprint_orchestrator.py`
- 状态文件：`/home/ubuntu/mojiajun-queue/sprint_state.json`（自动创建）
- 备份：`sprint_orchestrator.py.bak.gate_20260501_013501`（门控上线的旧备份）

## 运行

```bash
# 强制启动（忽略采集就绪检测）
python3 sprint_orchestrator.py --force

# cron 自动模式（每30秒）
* * * * * cd /home/ubuntu/mojiajun-queue && python3 sprint_orchestrator.py
* * * * * sleep 30 && cd /home/ubuntu/mojiajun-queue && python3 sprint_orchestrator.py
```

## ③创作阶段 use_ai 踩坑 (2026-04-29 修复)

**症状**：创作产出只有 209 字，是提纲复读而非正文展开。
**原因**：STAGE_CREATION_CODE 调 `molan.create()` 时：
1. 没传 `use_ai=True` → 走模板路径，不会调 DeepSeek 展开
2. 参数名不匹配：传了 `style_guide`/`target_user`，但 `ai_create_note` 收的是 `style`/`target`
3. 把 `content_outline` 塞进 `article_structure.opening`，模板直接当正文输出

**修复**：
```python
# ✅ 正确：把提纲拼入 description，让 AI 看到完整创作指令
description = f"主题：{topic}\n\n内容大纲（请据此展开为完整笔记）：\n{outline}"
result = create(
    use_ai=True,
    description=description,
    topic=topic,
    style=tone,       # ← 不是 style_guide
    target=audience,  # ← 不是 target_user
    note_type="story",
    ...
)
```

## 失败策略

| 阶段 | on_failure | max_retries | 行为 |
|------|-----------|-------------|------|
| ① 分析 | auto_retry | 3 | 自动重试 |
| ② 策划 | fallback_restart | 2 | 退回①重来 |
| ③ 创作 | rework_retry | 3 | 带 feedback 重试 |
| ④ 质检 | reject_rewrite | 2 | 驳回③重写 |
| ⑤ 通知 | ignore | 1 | 失败不影响流程 |

## 依赖模块（阶段③④桥接调用）

- `agent_outputs/molan/xiaohongshu_note.py` → `create(**kwargs)` — 生成小红书笔记
- `agent_outputs/mohong/style_auditor.py` → `audit_style(target_agent, days)` — 质量审计

## 同步命令

```bash
scp /tmp/sprint_orchestrator.py ubuntu@159.75.12.11:/home/ubuntu/mojiajun-queue/
```
