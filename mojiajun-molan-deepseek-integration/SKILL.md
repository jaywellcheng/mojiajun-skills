---
name: mojiajun-molan-deepseek-integration
description: 为墨蓝（molan）内容创作引擎接入DeepSeek API，让Agent在服务器上直接调用AI生成完整笔记（标题+正文+MJ Prompt），替代占位符模式
---

# 墨蓝接入DeepSeek API 完整生成笔记

## 背景

墨蓝v2模块原先是输出"创作上下文"（选题、风格、标签，但标题和正文是占位符 `（请在运行时由AI填充）`），没有真正调用AI生成内容。需要接入DeepSeek API让笔记真正可产出。

## 关键步骤

### 1. 配置API Key

在CORE-01的 `.env` 文件中添加：
```
DEEPSEEK_API_KEY=sk-xxxx
DEEPSEEK_MODEL=deepseek-chat
```

注意不能用 `echo '$VAR'` 方式写入环境变量，SSH终端不会展开本地变量。必须直接用字面值写入。

### 2. engine.py 中读取Key

```python
# 从.env读取环境变量
env_vars = {}
with open("/home/ubuntu/mojiajun-queue/.env") as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env_vars[k] = v
for k, v in env_vars.items():
    os.environ[k] = v
```

### 3. API调用函数

```python
def _call_deepseek(system_prompt, user_prompt, model=None):
    import requests
    resp = requests.post(
        "https://api.deepseek.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                 "Content-Type": "application/json"},
        json={
            "model": model or "deepseek-chat",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.8,
            "max_tokens": 4096
        },
        timeout=60
    )
    data = resp.json()
    return data["choices"][0]["message"]["content"]
```

### 4. System Prompt设计

关键要素：
- 人设固定：45岁景德镇人定居深圳，真实不装
- 注入爆款学习数据（参考标题+公式+心理开关+风格指南）
- product_hint可选：软植入松鼠杯
- 要求输出严格的JSON格式（title/content/mj_prompt/tags）
- 温度0.8，max_tokens 4096

### 5. 解析AI返回

AI可能返回纯JSON或markdown代码块包裹的JSON。两种容错：
- 直接 `json.loads()`
- 正则提取 `r'```(?:json)?\s*(\{.*?\})\s*```'`

## 注意事项

- API调用不要放在 `__init__` 中，否则模块导入即触发
- 测试时用独立脚本写 `.env` 读取逻辑，不要依赖shell环境变量继承
- DeepSeek api返回速度约5-15秒，timeout设60秒
- 如果API失败，回退到占位符模式（fallback），不崩溃
- 记录usage信息（tokens消耗）用于成本追踪

## 重要经验：System Prompt决定内容质量

**早上的教训**：第一次注入prompt时用了"45岁回景德镇路上，一碗冷粉就让我破防"这种公众号情感文风格，大威批评"太矫情，小红书不是这样写的"。

**修正方案**：System Prompt必须包含**负面清单**（❌要避开什么），而不仅仅是正面要求：
```
【术轨：你的内容必须避开】
- ❌ 情感散文式开头（不要"突然眼眶就热了"这类）
- ❌ 煽情词（破防、泪目、哭了）
- ❌ 公众号风格的长段落

【术轨：内容风格要求】
- ✅ 真实生活感，带点调侃
- ✅ 短句，每段2-3行
- ✅ 有用感（攻略/教程/清单/对比）
- ✅ 让读者看完有评论的欲望
```

**每天注入最新双轨洞察**：墨渊分析产出后，把最新的标题公式+风格指南+禁忌清单注入system prompt，而不是用固定的写死prompt。

## 双轨洞察注入prompt模板

```python
# 先读双轨洞察文件
with open("agent_outputs/molang_v2/dual_insight_inject.txt") as f:
    dual_context = f.read()

# 注入到system prompt中
system_prompt = f"""...{dual_context}..."""
```

## 验证方法

```bash
# 写独立脚本测试（不要用-c参数嵌套f-string）
python3 /tmp/test_molan_final.py
# 或直接
python3 /home/ubuntu/mojiajun-queue/agent_outputs/molang_v2/engine.py
```

预期输出：标题和正文不为空，有真实内容，符合小红书风格而非公众号风格。

注意：测试时要确保.env里的DEEPSEEK_API_KEY正确读入，不要在ssh -c中嵌套Python代码。
预期输出：标题和正文不为空，有真实内容。
