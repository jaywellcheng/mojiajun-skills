---
name: mojiajun-task-dispatch-payload-mapping
description: 墨家军task_queue任务派发时，payload格式必须与worker模块的entry function参数签名对齐。包含所有已注册task_type的payload格式映射表，避免"任务completed但产出不符合预期"的问题。
tags:
  - mojiajun
  - task_queue
  - module_dispatcher
  - payload-format
  - worker-module
---

# 墨家军任务派发 - Payload格式对齐方法论

## 核心问题

向 task_queue 派发任务时，即使 task_type 注册正确、worker 执行成功（status=completed），产出仍可能完全不符合预期。

**根因**：payload 的结构与 worker 模块的 entry function 期望的参数签名不匹配。

## 前置步骤：确定task_type和entry function

### 1. 查 module_dispatcher.py 的 TASK_MODULE_MAP

```bash
grep 'task_type' /home/ubuntu/mojiajun-queue/module_dispatcher.py
```

找到这一行：
```
"xiaohongshu_note": (target_agent, module_file, entry_function),
#                    ^molan       ^xiaohongshu_note   ^"create"
```

### 2. 查 entry function 的参数签名

```bash
grep -n 'def create\|def main\|^def ' /home/ubuntu/mojiajun-queue/agent_outputs/{agent}/{module_file}.py
```

注意看参数是：
- `def create(**kwargs)` → 扁平键值对，payload 直接作为 kwargs
- `def create(arg1, arg2, topic=None)` → 指名参数
- `def analyze(payload)` → 带 payload 字典参数

## Payload格式映射表（已验证）

下面表格列出了每个 task_type 对应的 entry function 期望的 payload 格式：

| task_type | agent | module | entry_func | Payload 格式要求 |
|-----------|-------|--------|------------|-----------------|
| `sample_analysis` | moyuan | `sample_analyzer` | `analyze()` | 无需参数，直接调用 |
| `xiaohongshu_note` | molan | `xiaohongshu_note` | `create(**kwargs)` | **扁平键值对！** 如 `{"brand": "天青浅", "topic": "回景德镇"}`。不要嵌套 `{"action":"create", "notes":[...]}`，模块的 `create()` 只看顶层参数名（topic/article_structure→promotion，product_name/brand/price_range→product） |
| `data_analysis` | moyuan | `data_analyzer` | `analyze()` | 无需参数或扁平 `{}` |
| `image_processor` | moqing | `image_processor` | `process()` | 无需参数或扁平 `{}` |
| `image_generator` | moqing | `image_generator` | `generate(prompt)` | payload 中需有 `prompt` 字段，或直接 `{"prompt": "..."}` |
| `gen_image` | moqing | `api_entry` | `generate(**kwargs)` | 扁平: `{"engine": "crun", "prompt": "..."}` |
| `gen_image_mj` | moqing | `api_entry` | `generate_mj(**kwargs)` | 扁平: `{"prompt": "...", "aspect_ratio": "1:1"}` |
| `make_cover` | moqing | `api_entry` | `make_cover(**kwargs)` | 扁平: `{"bg_image": "...", "title": "..."}` |
| `glm_ocr` | moyuan | `glm_ocr` | `parse(**kwargs)` | 扁平: `{"image_url": "...", "lang": "zh"}` |
| `glm_vision` | moyuan | `zhipu_vision` | `analyze(**kwargs)` | 扁平: `{"image_url": "...", "question": "..."}` |
| `content_planner` | mochuang | `content_planner` | `plan(**kwargs)` | 扁平: `{"topic": "...", "days": 7}` |
| `data_check` | mocheng | `data_checker` | `check_new_data(**kwargs)` | 扁平: `{"table": "xhs_sample_library"}` |

## 判断Payload格式的快捷方法

```bash
# 方法1：看entry function签名
ssh ubuntu@159.75.12.11 "grep -A5 '^def create(' /home/ubuntu/mojiajun-queue/agent_outputs/molan/xiaohongshu_note.py"

# 方法2：看代码入口处的参数处理逻辑
ssh ubuntu@159.75.12.11 "sed -n '320,340p' /home/ubuntu/mojiajun-queue/agent_outputs/molan/xiaohongshu_note.py"
```

关键判断：
- **`def create(**kwargs)`** → payload 的顶层 key 必须等于函数形参名
- **`def create()`** → 无需传参，payload 可以是 `{}`
- **`def analyze(payload)`** → 需要传 payload 对象

## 派发时payload格式

### 正确方式（扁平参数）

```python
# payload 直接放入任务
payload = json.dumps({
    "brand": "天青浅",
    "persona": "45岁景德镇人定居深圳",
    "topic": "回景德镇前的心情",
}, ensure_ascii=False)

# 写入task_queue
INSERT INTO task_queue (task_id, target_agent, task_type, payload, priority, status)
VALUES (UUID(), 'molan', 'xiaohongshu_note', %s, 1, 'pending')
```

### 错误方式（嵌套struct）

```python
# ❌ 错误：模块的 create() 不会解析 notes[0]["theme"]
payload = json.dumps({
    "action": "generate_notes",
    "notes": [{"theme": "回景德镇"}],
    ...
})
```

## 验证产出的标准流程

任务派发后等待15-30秒，然后：

```bash
# 1. 查最新任务状态
ssh ubuntu@159.75.12.11 "mysql -h127.0.0.1 -uxiaochuan -pxiaochuan_2026_mjj mojiajun -e 'SELECT id, target_agent, task_type, status FROM task_queue ORDER BY id DESC LIMIT 5;' 2>/dev/null"

# 2. 查result.json看具体产出
ssh ubuntu@159.75.12.11 "cat /home/ubuntu/mojiajun-queue/agent_outputs/{agent}/result.json"

# 3. 对比预期——看产出内容是否用了payload里的参数
# 比如payload传了topic="回景德镇"，但产出的note_title还是"松鼠杯"→说明payload没被消费
```

## 经验教训（2026-04-26）

1. `sample_analysis` 的 `analyze()` 无需参数——直接传 `{}` 即可
2. `xiaohongshu_note` 的 `create(**kwargs)` 按关键字匹配：
   - 有 `topic`/`article_structure` → promotion模式
   - 有 `product_name`/`brand`/`price_range` → product模式
   - 什么都不传 → product模式（默认）
3. `data_analysis` 和 `image_processor` 不读 xhs_sample_library——它们分析的是其他数据源
4. 任务completed ≠ 任务产出正确——payload格式不对时worker照样执行但产出的不是你要的
5. 如果模块不支持自定义payload，直接本地写内容传给用户更快，不用硬适配模块
