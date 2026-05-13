---
name: backlog
description: 跨会话任务追踪系统。管理待办/等待/就绪任务，三系统闭环(retro→backlog→dispatch→retro)。大威提到"还有什么没做""有什么待办""看看进度"时加载。
version: 1.0.0
author: 小川
license: MIT
metadata:
  hermes:
    tags: [backlog, tasks, tracking, planning]
    related_skills: [total-commander-mode, mojiajun-memory-system]
---

# backlog 任务追踪

## 概述

跨会话任务追踪系统。解决"关了窗口就忘记还有什么没做"的问题。
三系统时间轴：retro（过去）→ backlog（未来）→ dispatch（现在）→ retro（归档闭环）。

每次对话开始前：先检查 backlog 状态，汇报待处理事项，再响应新请求。

## 当使用

- 对话刚开始时——先加载此 skill 检查 backlog
- 大威说"还有什么没做""有什么待办""看看进度""还有哪些事"——立即加载并运行检查
- 大威说"记一下这个以后做""这个先放着"——用 backlog-manager add 添加任务
- 大威说"那个做完了""这个搞定了"——用 backlog-manager status 更新状态
- 提到"等X到"、"等X通过"——用 backlog-manager 加 waiting 条件

## 核心命令

所有操作通过 SSH 到 CORE-01 执行（本地Mac用wrapper）：

```
~/.hermes/backlog/backlog.sh <命令>
```

底层执行：`ssh ubuntu@159.75.12.11 "cd ~/.hermes/backlog && python3 backlog-manager.py <命令>"`

backlog 主副本在 CORE-01（24小时在线），本地 Mac 通过 SSH 操作。CORE-01 系统 crontab 每天9:00自动检查，发现问题发邮件到 76835298@qq.com。

### 常用命令速查

| 场景 | 命令 |
|------|------|
| 查看所有未完成 | `backlog-manager list` |
| 查看特定状态 | `backlog-manager list --status waiting` |
| 按标签筛选 | `backlog-manager list --tags plur` |
| 新增想法 | `backlog-manager add "标题" --status idea` |
| 新增待办 | `backlog-manager add "标题" --status pending --tags "a,b"` |
| 新增等待 | `backlog-manager add "标题" --status waiting --until 2026-05-20` |
| 改状态 | `backlog-manager status <id> active "开始干了"` |
| 标记完成 | `backlog-manager status <id> completed` |
| 取消（必须写原因） | `backlog-manager status <id> cancelled "不做了因为..."` |
| 更新字段 | `backlog-manager update <id> --next "下一步动作"` |
| 全面检查 | `backlog-manager check` |
| 备份 | `backlog-manager backup` |

### 每日检查（cron 自动跑，也可手动）

每天早上 backlog-manager check 检查四件事：

1. **就绪任务** — waiting 条件满足 → ready 状态，汇总展示
2. **卡住任务** — active >7天未更新 → 标黄提醒
3. **搁置想法** — idea >30天未动 → 提醒清理
4. **等待超时** — waiting >60天无 next_action → 提醒是否放弃

## 状态机

```
idea → pending → active ↔ waiting → ready → active → completed
         ↘ 任意 → cancelled
```

| 状态 | 含义 | 什么时候用 |
|------|------|-----------|
| idea | 灵感/想法，未正式立项 | 先记下来，别占大脑 |
| pending | 已立项，等待开始 | 确定要做，还没动手 |
| active | 正在执行 | 正在干的活 |
| waiting | 等外部条件 | 等日期到/等别人/等数据 |
| ready | 条件满足，待确认 | cron 自动标记，等大威说"干" |
| completed | 已完成 | 搞定了 |
| cancelled | 已取消（必须填原因） | 决定不做了 |

## 三系统闭环（必读）

backlog 不是孤立的。它与另外两个系统形成时间轴闭环：

```
                  ┌─────────┐
                  │  retro   │ ← 过去：已完成的经验归档
                  └────┬────┘
                       │ report完成后自动检查→追加新待办
                       ↓
                  ┌─────────┐
                  │ backlog  │ ← 未来：待办和规划
                  └────┬────┘
                       │ active任务→通过dispatch执行
                       ↓
                  ┌─────────┐
                  │ dispatch│ ← 现在：正在执行的任务
                  └────┬────┘
                       │ 执行完毕→retro归档
                       ↓
                  ┌─────────┐
                  │  retro   │ ← 闭环完成
                  └─────────┘
```

### 写入入口（只有三个）

1. **retro.py report 后自动检查** → 追加到 CORE-01 backlog-agent.yaml
2. **cron 定时检查** → 条件满足/卡住/超时提醒（cron只读不写）
3. **口头说"这个以后做"** → 小川手动加

## 安全机制

- **原子写入**：先写.tmp再rename，写到一半crash不会丢数据
- **YAML校验**：写入前语法检查，格式错了拒绝写入
- **冲突检测**：写入前读最新版本比对，被改过就提示
- **自动备份**：每天保留最近7份备份
- **cancelled必须写原因**：防止忘记为什么取消

## 常见陷阱

1. **改状态跳过reason** → cancelled 强制填 reason，其他状态可选
2. **非法状态转换** → 不能从 idea 直接到 completed，必须走 pending → active
3. **多窗口同时改** → 写入前检测冲突，不要覆盖别人的变更
4. **next_action 执行完忘了更新状态** → 养成习惯：做完下一步就更新
5. **notes 字段更新不会重置 stuck_days** → 只有 status 变化才重置

## 验证清单

- [ ] `backlog-manager check` 能看到所有待处理事项
- [ ] 每次对话开始前加载此 skill
- [ ] 三系统闭环关系已理解（retro→backlog→dispatch→retro）
- [ ] 知道三个写入入口（retro/cron/口头）
- [ ] 知道 atomic write 保护文件不损坏
