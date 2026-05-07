---
name: mojiajun-agent-module-deployment
description: 为墨家军Agent部署新能力模块到CORE-01的完整模式——编写→传输(base64)→注册module_dispatcher→worker重启→验证。覆盖shell heredoc引号陷阱、.env加载、sed注册三大坑。
category: mojiajun
tags: [deployment, agent-module, module-dispatcher, comic-planner, capability-gap]
---

# 墨家军 Agent 新模块部署模式

## 适用场景
- 墨家军某个Agent缺少某种能力（如墨创缺漫画脚本策划）
- 需要新建Python模块并注册到module_dispatcher
- 产出物从本地Mac部署到CORE-01

## 全流程（5步）

### 1. 本地编写模块

模块规范：
- 放在 `agent_outputs/{agent}/` 目录下
- 入口函数接收 `payload: dict`，返回 `dict`
- 需要调用外部API的模块**必须自己加载.env**

.env自加载模板（放在模块顶部import之后）：
```python
from pathlib import Path
import os
_env = Path("/home/ubuntu/mojiajun-queue/.env")
if _env.exists():
    for line in _env.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
```

### 2. 传输到CORE-01（scp优先，base64备选）

**首选：scp文件**（比base64更可靠，保留所有字符）：
```bash
scp /tmp/module.py ubuntu@159.75.12.11:/path/to/module.py
```

**备选：base64**（当scp不可用时）：
```bash
base64 -i /tmp/module.py | ssh ubuntu@159.75.12.11 "base64 -d > /path/to/module.py"
```

### 2b. 安全修改服务器上的现有文件

**绝对不要用 `ssh ... << 'PYEOF'` 或 `ssh ... python3 << 'PYEOF'`！**
Shell heredoc会吃掉Python字符串中的引号、中文标点。

正确做法：写本地patch脚本 → scp上传 → 远程执行：
```bash
# 本地写 /tmp/patch_xxx.py（纯Python，操作文件）
# scp上传
scp /tmp/patch_xxx.py ubuntu@159.75.12.11:/tmp/
# 远程执行
ssh ubuntu@159.75.12.11 "python3 /tmp/patch_xxx.py"
```

### 3. 注册到module_dispatcher

**绝对不要用Python脚本插入行！** 引号会被shell吃掉，导致 `"key":` 变成 `key:`（NameError）。

正确做法——sed精确定位插入：
```bash
# 先找锚点行号
ssh ... "grep -n 'comic_bubble' module_dispatcher.py"
# sed在锚点行后插入（注意转义）
ssh ... "sed -i '45a\\    \"comic_script\":       (\"mochuang\", \"comic_planner\",       \"plan\"),' module_dispatcher.py"
# 验证
ssh ... "sed -n '46p' module_dispatcher.py"
```

或者用Python但写文件而非修改：
```bash
ssh ... "python3 -c \"
lines = open('module_dispatcher.py').readlines()
lines.insert(46, '    \\\"comic_script\\\":       (\\\"mochuang\\\", \\\"comic_planner\\\",       \\\"plan\\\"),\\n')
open('module_dispatcher.py','w').writelines(lines)
\""
# 注意三层转义：bash → python → python string — 容易出错
```

### 4. 重启Agent Worker

```bash
ssh ubuntu@159.75.12.11 "
pkill -f 'agent_worker.py <agent>'
sleep 1
cd /home/ubuntu/mojiajun-queue && nohup python3 -B agent_worker.py <agent> > /tmp/<agent>_worker.log 2>&1 &
sleep 2 && ps aux | grep 'agent_worker.py <agent>' | grep -v grep
"
```

### 5. 验证

**先直接测试模块（绕过task_queue调度层）——含.env预加载**：
```bash
# 测试脚本模板：在import模块前先加载.env
ssh ubuntu@159.75.12.11 "cd /home/ubuntu/mojiajun-queue && python3 -c \"
import sys, os, json
sys.path.insert(0, '.')
# === 预加载.env（worker环境可能没有） ===
env_file = '/home/ubuntu/mojiajun-queue/.env'
if os.path.exists(env_file):
    for line in open(env_file).read().splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, _, v = line.partition('=')
            os.environ.setdefault(k.strip(), v.strip().strip('\\\"').strip(\\\"'\\\"))
print('DEEPSEEK_API_KEY:', 'YES' if os.environ.get('DEEPSEEK_API_KEY') else 'NO')
# === 测试模块 ===
payload = json.loads('{\"key\":\"value\"}')  # 用json.loads避免shell引号问题
from agent_outputs.<agent>.<module> import <func>
r = <func>(payload)
print('success:', r.get('success'))
print('error:', r.get('error', '-'))
# 打印关键字段...
\""

**再测试module_dispatcher导入**：
```bash
ssh ... "cd /home/ubuntu/mojiajun-queue && python3 -c 'from module_dispatcher import TASK_MODULE_MAP; print(TASK_MODULE_MAP.get(\"<task_type>\"))'"
```

**最后通过task_queue派发验证全链路**：
```sql
INSERT INTO task_queue (...) VALUES (...);
```

## 三大经典陷阱

### 陷阱1：shell heredoc吃引号/中文标点
- `ssh ... << 'PYEOF'` 中Python字符串的 `"` 和中文全角标点被shell错误解析
- **解决**：用base64传输，或用 `json.loads('{}')` 单引号包裹payload

### 陷阱2：module_dispatcher注册后引号丢失
- Python字符串替换中 `"key":` 的引号被bash吃掉
- **解决**：用sed按行号插入，不用Python修改

### 陷阱3：Agent Worker不加载.env
- `agent_worker.py` 启动时不source .env，子模块的 `os.environ.get("DEEPSEEK_API_KEY")` 拿不到值
- **解决**：需要外部API的模块必须自己加载.env（见Step 1模板）

## 案例：comic_planner.py

给墨创添加漫画脚本策划能力。Payload规范：
```json
{
  "theme": "主题",
  "series": "窑滚人生",
  "grids": 4,
  "tone": "轻松幽默吐槽",
  "roles": {"角色名": "性格描述"},
  "note_req": "额外要求"
}
```

入口函数签名：`plan(payload: dict) -> dict`

返回格式：
```json
{"success": true, "script": {"title":"", "grids":[...], "q_bonus":{}, "note_text":""}, "saved_to": "/path/to/result.json"}
```

## 注入现有代码的已知Hook点

当新模块需要注入到已有代码中（如agent_worker、molan），优先用「写patch脚本→scp→执行」模式，避免heredoc。

### Hook点1：agent_worker 任务完成后的post-hook
位置：在 `extractMemories hook` 之后，`update_progress(task_id, 100)` 之前
```python
# 在 agent_worker.py 中搜索锚点：
old = """        except Exception:
            pass
        # =================================================================
        update_progress(task_id, 100"""
# 在中间插入新hook
```

### Hook点2：molan ai_create_note 生成后的自审注入
位置：`result["model"] = model` 之后，`return result` 之前
```python
old = '        result["model"] = model\n        return result'
# 在中间插入 self_review / slop_detect 调用
```

### Hook点3：molan ai_create_note user_prompt构建前的增强注入
位置：`user_prompt = f"""创作一篇小红书笔记。` 之前
```python
# 注入 few-shot + CoT 增强上下文
```

### Hook点4：dashboard.py 添加新路由
位置：`if __name__` 之前插入新路由函数
```python
# 用行号插入，找 __name__ 行所在位置
```

### 注入陷阱：f-string闭合
当注入代码包含多行字符串时，注意原文件的引号闭合。
**症状**：`SyntaxError: unterminated string literal`
**原因**：注入的 `"""` 与原文件的 `"""` 叠加成 `""""`
**修复**：检查替换后的引号数量是否匹配

## 2026-05-06 新增模块

| task_type | 文件 | 功能 |
|-----------|------|------|
| governance | mozi/governance.py | 预算熔断+审批门 |
| ai_slop_detect | mozi/ai_slop_detector.py | AI痕迹检测 |
| semantic_bookmark | mozi/semantic_bookmark.py | 语义收藏夹 |
| pdf_ingest | mozi/pdf_ingest.py | PDF→Markdown |
| task_trajectory | mozi/task_trajectory.py | 任务轨迹记录 |

## MySQL Decimal序列化陷阱
pymysql的 `SUM/AVG` 返回 `Decimal` 对象，`json.dumps` 报 `TypeError`。
修复：`float(value)` 显式转换，或写辅助函数递归处理。
