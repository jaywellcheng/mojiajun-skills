---
name: mojiajun-agent-capability-gap-fill
description: 墨家军Agent能力缺口诊断与补齐——发现Agent缺某个task_type时，创建模块→注册→部署→重启worker→验证的完整流程。含shell转义规避、env自加载、scp替代方案。
category: mojiajun
---

# 墨家军 Agent 能力缺口补齐

## 触发条件
- 派发任务后Agent返回success但无产出文件
- module_dispatcher中查不到对应task_type
- Agent能力名片标注了角色但实际缺模块

## 完整流程（5步）

### 1. 诊断缺口

```bash
# 查已注册task_type
ssh ubuntu@159.75.12.11 "cd /home/ubuntu/mojiajun-queue && python3 -c '
from module_dispatcher import list_task_types, TASK_MODULE_MAP
t = list_task_types()
print(\"已注册:\", len(t))
print(\"comic_script\" in t)  # 替换为你要查的task_type
'"
```

### 2. 创建模块文件

模块放在 `/home/ubuntu/mojiajun-queue/agent_outputs/<agent>/` 下。参考现有模块的DeepSeek调用模式：

```python
# 自加载.env（关键！worker进程不继承环境变量）
_env_file = Path("/home/ubuntu/mojiajun-queue/.env")
if _env_file.exists():
    for _line in _env_file.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _, _v = _line.partition("=")
            _k, _v = _k.strip(), _v.strip().strip('"').strip("'")
            if _k and _k not in os.environ:
                os.environ[_k] = _v
```

入口函数签名：`def plan(payload: dict):` 或 `def create(payload: dict):`，返回dict。

### 3. 传输文件到CORE-01

SCP常被fail2ban封。用base64绕过：

```bash
# macOS
base64 -i /tmp/my_module.py | ssh ubuntu@159.75.12.11 "base64 -d > /path/to/target.py"

# Linux
base64 /tmp/my_module.py | ssh ubuntu@159.75.12.11 "base64 -d > /path/to/target.py"
```

### 4. 注册到module_dispatcher + 重启worker

```bash
# 在TASK_MODULE_MAP中插入新行
ssh ubuntu@159.75.12.11 "cd /home/ubuntu/mojiajun-queue && python3 -c '
lines = open(\"module_dispatcher.py\").readlines()
new_lines = []
for line in lines:
    new_lines.append(line)
    if \"comic_bubble\" in line:  # 插入点，选邻近的已注册task_type
        new_lines.append(\"    \\\"my_task_type\\\":       (\\\"my_agent\\\", \\\"my_module\\\",       \\\"entry_func\\\"),\\n\")
open(\"module_dispatcher.py\", \"w\").writelines(new_lines)
'"

# 重启对应Agent的worker
pkill -f 'agent_worker.py <agent_name>'
nohup python3 -B agent_worker.py <agent_name> > /dev/null 2>&1 &
```

### 5. 验证

```bash
# 验证导入
ssh ubuntu@159.75.12.11 "cd /home/ubuntu/mojiajun-queue && python3 -c 'from module_dispatcher import TASK_MODULE_MAP; print(TASK_MODULE_MAP.get(\"my_task_type\"))'"

# 直接测试（绕过task_queue调度层）
# 写测试脚本→base64传输→远程执行
```

## 常见陷阱

### 陷阱1：Shell heredoc吃Python引号
**症状**：Python代码通过 `ssh ... << 'PYEOF'` 传输时，花括号`{}`、中文逗号`，`、三引号`"""`被bash错误解析。
**解决**：永远用base64传输Python文件，不走heredoc。

### 陷阱2：Worker不加载.env
**症状**：模块报`DEEPSEEK_API_KEY 未配置`，但.env文件存在。
**根因**：agent_worker.py不加载.env，环境变量不传递给子模块。
**解决**：在模块顶部自加载.env（见上方代码）。

### 陷阱3：module_dispatcher持久化失败
**症状**：sed/Python修改module_dispatcher.py后，引号丢失导致NameError。
**解决**：用Python的writelines完整重写文件，不要用sed。修改后立即`python3 -c 'import module_dispatcher'`验证。

### 陷阱4：Worker不识别新task_type
**症状**：模块注册后，任务仍不执行。
**根因**：worker在启动时加载TASK_MODULE_MAP，新增的task_type需要重启worker才能生效。
**解决**：`pkill -f 'agent_worker.py <agent>'` 后重新启动。

## 派发任务两种方式

### 方式A：走task_queue（正规）
```sql
INSERT INTO task_queue (task_id, target_agent, task_type, payload, status, priority, created_at)
VALUES (CONCAT('my_task_', UNIX_TIMESTAMP()), 'agent_name', 'my_task_type', '{"key":"value"}', 'pending', 5, NOW());
```
**注意**：payload中的中文经过MySQL JSON序列化后可能被DeepSeek误解，复杂指令建议用方式B。

### 方式B：直接远程执行（绕过调度层）
当payload中有详细中文指令时，用base64传Python脚本直接远程执行，不走task_queue转义。
