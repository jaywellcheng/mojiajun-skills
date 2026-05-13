---
name: xiaochuan-recovery-dead
title: 小川掉线恢复排查清单
description: 当小川（本地 Hermes Agent）切换模型后掉线，一直报 OpenRouter 401/500 时的系统化排查流程。小墨可以直接拿着这份清单指导大威一步步修复。
category: mojiajun
---

# 小川掉线恢复排查清单

## 错误特征
日志显示: `provider=openrouter`, `base_url=https://openrouter.ai/api/v1`, 报 401 或 500。
**结论: provider 被路由到了 OpenRouter，但 OpenRouter 没配 key。**

## 排查步骤

### 1. 检查 config.yaml
大威在 Mac 终端执行:
```
head -5 ~/.hermes/config.yaml
```

**情况 A: model 是字符串** (如 `model: deepseek-v4-flash`)
→ **问题4: 字符串格式导致 provider 退化为 auto**
修复: 改成 dict 格式
```
sed -i '' 's/^model:.*/model:\n  default: deepseek-v4-flash\n  provider: deepseek\n  base_url: https:\/\/api.deepseek.com\/v1/' ~/.hermes/config.yaml
```

**情况 B: providers 是 {}**
→ **问题2: config set 清空了 providers**
修复: 补回 deepseek 配置:
- api_key: sk-e813bb143bfb43f2a06b3269be721674
- base_url: https://api.deepseek.com/v1

### 2. 检查 auth.json
大威执行:
```
cat ~/.hermes/auth.json | python3 -m json.tool
```

看 `providers` 字段:
- 如果是 `{}` → **问题3: auth.json 优先级高于 config.yaml**
修复: 用 Python 写入:
```python
import json
with open('/Users/jaywell/.hermes/auth.json') as f:
    data = json.load(f)
data['providers'] = {
    'deepseek': {
        'label': 'DeepSeek',
        'credential_pool_id': 'deepseek',
        'base_url': 'https://api.deepseek.com/v1',
        'default_model': 'deepseek-v4-flash'
    }
}
with open('/Users/jaywell/.hermes/auth.json', 'w') as f:
    json.dump(data, f, indent=2)
```

### 3. 重启
```
pkill -9 -f hermes
hermes chat --new "你好"
```

### 4. 验证
大威新开窗口测试，确认正常对话后再关旧窗口。

## 关键踩坑
- `hermes config set model deepseek/deepseek-v4-flash` 带斜杠 → **问题1**: provider 自动切 openrouter
- `config set` 会清空 `providers` 字段 → **问题2**
- auth.json 优先级高于 config.yaml → **问题3**
- model 字符串格式导致 provider 退化为 auto → **问题4**
