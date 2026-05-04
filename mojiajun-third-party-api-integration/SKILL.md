---
name: mojiajun-third-party-api-integration
description: 墨家军第三方API工具集成方法 — 将TT API/Crun.AI/SiliconFlow/Fal.ai/Photoroom/Kling/MiniMax等外部API集成到墨家军Agent工作流的完整流程
---

# 墨家军第三方API工具集成

## 适用场景

当需要为墨家军Agent增加新的外部API能力（如图片生成、视频生成、图片处理、语音合成等）时使用。

## 架构设计

所有API模块统一放在 `agent_outputs/moyuan/api_toolkit/` 目录下，dispatcher通过 `agent_outputs/{agent_name}/` 下的包装文件调用。

```
agent_outputs/moyuan/api_toolkit/
├── base_client.py       # 基础HTTP客户端（重试+轮询+超时）
├── tt_api.py            # TT API Midjourney ✅已验证
├── crun_api.py          # Crun.AI 多模态(100+模型) ✅已验证
├── siliconflow_api.py   # SiliconFlow(Kolors可用,FLUX需开权限)
├── fal_api.py           # Fal.ai FLUX快速出图(0.15s) ✅已验证
├── photoroom_api.py     # Photoroom智能抠图(待测大图)
├── kling_api.py         # Kling AI文生视频(需开API权限)
└── minimax_api.py       # MiniMax语音合成(需Group ID)
```

## 集成步骤

### 1. 盘点已有的API工具

查看两个关键文档：

```bash
# SECRET.md — 所有API Key清单
ssh ubuntu@CORE-01 cat /home/ubuntu/mojiajun-queue/secrets/SECRET.md

# 武器库文档 — API调用方式
ssh ubuntu@CORE-01 cat /home/ubuntu/mojiajun-queue/墨家军综合工具武器库.md
```

**注意：** 武器库文档中有些Key有省略号（`sk-enn...qmwp`），需要向用户索取完整Key。SECRET.md中的Key是完整的。

### 2. 测试API端点

先用curl在服务器上直接测试API能否调通：

#### TT API (Midjourney)
```bash
# 创建任务
curl -X POST "https://api.ttapi.io/midjourney/v1/imagine" \
  -H "TT-API-KEY: xxx" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "test --ar 3:4 --v 6", "mode": "fast"}'
# 返回: {"status":"SUCCESS","data":{"jobId":"xxx"}}

# 查询结果（轮询，MJ生图约30-60秒）
curl -X GET "https://api.ttapi.io/midjourney/v1/fetch?jobId=xxx" \
  -H "TT-API-KEY: xxx"
# 返回: {"status":"SUCCESS","data":{"images":["url1","url2","url3","url4"],"cdnImage":"url"}}
```

**关键字段：** `jobId` 在 `data.jobId` 里，不在根级。

#### Crun.AI (多模态)
```bash
curl -X POST "https://api.crun.ai/api/v1/client/job/CreateTask" \
  -H "X-API-KEY: xxx" \
  -H "Content-Type: application/json" \
  -d '{"model": "google/nano-banana", "input": {"prompt": "test"}}'

# 轮询
curl -X GET "https://api.crun.ai/api/v1/client/job/TaskInfo?task_id=xxx" \
  -H "X-API-KEY: xxx"
```
**模型名格式：** `google/nano-banana`, `google/veo3-1-t2v`, `alibaba/wan-2.6` 等

#### SiliconFlow (图片生成)
```bash
curl -X POST "https://api.siliconflow.cn/v1/images/generations" \
  -H "Authorization: Bearer xxx" \
  -H "Content-Type: application/json" \
  -d '{"model": "Kwai-Kolors/Kolors", "prompt": "test", "image_size": "1024x1024"}'
```
**注意：** FLUX系列模型可能需要在后台开通权限，Kolors默认可用。

#### Fal.ai (FLUX快速出图)
```bash
curl -X POST "https://fal.run/fal-ai/flux/schnell" \
  -H "Authorization: Key {key_id}:{key_secret}" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"test","image_size":"square_hd","num_inference_steps":4}'
```
**注意：** 认证用 `Authorization: Key {id}:{secret}` 而不是Basic Auth。
**image_size格式：** 用 `square_hd`(1024x1024), `portrait_4_3`(864x1152) 等，不是 `1024x1024`。
**速度：** 约0.15秒出图，极快。

#### Photoroom (抠图)
```bash
curl -X POST "https://api.photoroom.com/v1/backgrounds/remove" \
  -H "x-api-key: xxx" \
  -F "image_file=@/path/to/image.png" \
  -F "format=png"
```

#### Kling AI (视频生成)
认证方式：AccessKey + SecretKey → JWT Bearer token
```python
import jwt, time
payload = {"iss": access_key, "exp": int(time.time())+1800, "nbf": int(time.time())-5}
token = jwt.encode(payload, secret_key, algorithm="HS256", headers={"alg":"HS256","typ":"JWT"})
# 然后用 Authorization: Bearer {token}
```
**注意：** Key需要在 https://klingai.com/dev/api-key 绑定IP或开通API权限。

### 3. 写API模块文件

在 `/home/ubuntu/mojiajun-queue/agent_outputs/moyuan/api_toolkit/` 下新建 `xxx_api.py`。

**核心模式：**

```python
#!/usr/bin/env python3
"""模块名 - 功能描述"""

import json, os, logging, requests
from datetime import datetime

logger = logging.getLogger("ModuleName")

API_KEY = "xxx"
OUTPUT_DIR = "/home/ubuntu/mojiajun-queue/agent_outputs/moqing/generated/xxx"

class Client:
    def __init__(self):
        self.stats = {"calls": 0, "failures": 0}
        os.makedirs(OUTPUT_DIR, exist_ok=True)

    def generate(self, prompt, **kwargs):
        """主功能接口"""
        # 组装payload → 发请求 → 处理响应 → 下载 → 返回结构化结果
        # ...
        return {"status": "success|error", "images": [{"filepath":"...", "url":"..."}]}

    def _download(self, url, task_id="unknown", index=0):
        try:
            resp = requests.get(url, timeout=60)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{task_id[:8]}_{index}_{ts}.jpg"
            filepath = os.path.join(OUTPUT_DIR, filename)
            with open(filepath, "wb") as f:
                f.write(resp.content)
            return filepath
        except Exception as e:
            logger.error(f"Download error: {e}")
            return None

# Agent入口函数（必须有，名称与module_dispatcher中注册的一致）
def generate(prompt, **kwargs):
    client = Client()
    return client.generate(prompt, **kwargs)
```

**关键规范：**
- 必须有Agent入口函数（如 `generate()`），名称与module_dispatcher中注册的一致
- 所有生成的图/视频下载到 `agent_outputs/moqing/generated/xxx/`
- 输出统一格式：`{"status": "success|error", "images": [{"filepath":"...", "url":"..."}]}`
- 返回结构必须能被json.dumps序列化（注意Decimal类型）

### 4. 在目标Agent下创建包装文件

dispatcher从 `agent_outputs/{agent_name}/` 找模块文件，所以需要在目标Agent目录创建包装文件转发到api_toolkit：

```bash
ssh ubuntu@CORE-01 "cat > /home/ubuntu/mojiajun-queue/agent_outputs/moqing/xxx_api.py << 'PYEOF'
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
from agent_outputs.moyuan.api_toolkit.xxx_api import generate
PYEOF"
```

**dispatcher的TASK_MODULE_MAP三元组逻辑：**
- `(agent, module, func)` → 从 `agent_outputs/{agent}/` 找 `{module}.py`，调用 `{func}()` 函数
- **注意：** 调用时传参方式为 `payload.get("args", {})` 作为 `**kwargs` 传入

### 5. 注册到 module_dispatcher

在 `/home/ubuntu/mojiajun-queue/module_dispatcher.py` 的 TASK_MODULE_MAP 中添加新条目：

```python
"xxx_task_type":  ("moqing",   "xxx_api",               "generate"),
```

**注意：** 
- 插入后必须检查Python语法：`python3 -c "import py_compile; py_compile.compile('module_dispatcher.py', doraise=True)"`
- 所有entry的key和value必须用引号括起来，不要用裸key（否则在import时报NameError）

### 6. 验证

```bash
# 直接调模块
cd /home/ubuntu/mojiajun-queue
python3 -c "from agent_outputs.moyuan.api_toolkit.xxx_api import generate; print(generate('test'))"

# 通过dispatcher调
python3 -c "from module_dispatcher import dispatch; r=dispatch('xxx_task_type', {'args':{'prompt':'test'}}, 'moqing'); print(r)"

# 通过task_queue派任务
# INSERT INTO task_queue (task_id, target_agent, task_type, payload, ...)
# VALUES ('xxx_01', 'moqing', 'xxx_task_type', '{"task":"...","args":{...}}', ...)
```

## 已验证的API认证方式汇总

| API | 认证方式 | Header格式 | 端点 |
|:----|:--------|:-----------|:-----|
| **TT API** | API Key | `TT-API-KEY: xxx` | `https://api.ttapi.io/midjourney/v1/imagine` |
| **Crun.AI** | API Key | `X-API-KEY: xxx` | `https://api.crun.ai/api/v1/client/job/CreateTask` |
| **SiliconFlow** | Bearer Token | `Authorization: Bearer xxx` | `https://api.siliconflow.cn/v1/images/generations` |
| **Fal.ai** | Key ID:Secret | `Authorization: Key {id}:{secret}` | `https://fal.run/fal-ai/flux/schnell` |
| **Photoroom** | API Key | `x-api-key: xxx` | `https://api.photoroom.com/v1/backgrounds/remove` |
| **Kling AI** | JWT Bearer | `Authorization: Bearer {jwt}` | `https://api-singapore.klingai.com/v1/videos/text2video` |
| **MiniMax** | Bearer Token + Group ID | `Authorization: Bearer xxx` | `https://api.minimax.io/v1/t2a_v2` |

## v3: Unified api_toolkit Architecture

After all individual APIs were integrated, a unified scheduling layer was built:

### File Layout

```
agent_outputs/moyuan/api_toolkit/
├── __init__.py           # Unified exports, engine registry, generate_image() helper
├── base_client.py        # Base HTTP client (retry, poll, timeout)
├── tt_api.py             # TT API Midjourney ($0.02-0.05/img, 45-60s)
├── fal_api.py            # Fal.ai FLUX ($0.003-0.025/img, 0.15s!)
├── crun_api.py           # Crun.AI 100+ models (1000 credits)
├── siliconflow_api.py    # SiliconFlow Kolors (50元)
├── photoroom_api.py      # Photoroom smart cutout ($0.02/img)
├── kling_api.py          # Kling AI video (needs API activation)
└── minimax_api.py        # MiniMax TTS (needs Group ID)

agent_outputs/moqing/
├── api_entry.py          # Unified dispatcher entry point (wraps all engines)
└── generated/            # All downloaded media
    ├── fal/              # Fal.ai FLUX outputs
    ├── crun/             # Crun.AI outputs
    ├── siliconflow/      # SiliconFlow outputs
    ├── kling/            # Kling AI outputs
    ├── photoroom/        # Photoroom outputs
    └── minimax/          # MiniMax TTS outputs
```

### Dispatcher Registration (v2 unified)

```python
TASK_MODULE_MAP = {
    "gen_image":           ("moqing", "api_entry", "generate"),       # auto-select engine
    "gen_image_mj":        ("moqing", "api_entry", "generate_mj"),    # force MJ
    "gen_image_flux":      ("moqing", "api_entry", "generate_flux"),  # force FLUX
    "gen_image_crun":      ("moqing", "api_entry", "generate_crun"),  # force Crun
    "gen_image_kolors":    ("moqing", "api_entry", "generate_kolors"),# force Kolors
    "gen_video":           ("moqing", "api_entry", "generate_video"), # video
}
```

### The `**kwargs` Rule

All entry functions in `api_entry.py` MUST use `**kwargs` because dispatcher calls them with:
```python
func(**payload.get("args", {}))
```

If a function has positional args like `def generate(prompt, engine)` but payload sends `{"task":"x", "prompt":"y"}` as kwargs, the function signature will extract `prompt` but `task` stays in kwargs — BUT if dispatcher sends `{}` (empty, because args wrapper missing), then `prompt` is None.

**Always use this pattern:**
```python
def generate(**kwargs):
    prompt = _extract_prompt(**kwargs)
    engine = kwargs.get("engine", "flux")
    if not prompt:
        return {"status": "no_input"}

def generate_flux(**kwargs):
    kwargs["engine"] = "flux"
    return generate(**kwargs)
```

The per-engine wrappers let dispatcher tasks specify which API to use without the task payload needing to include `engine` param.

### Engine Selection Guide

| Use Case | Engine | Why |
|----------|--------|-----|
| 小红书封面/配图 | **MJ (TT API)** | Best aesthetic, art style |
| 快速出图/产品图 | **FLUX (Fal.ai)** | Cheapest ($0.003), fastest (0.15s) |
| 视频生成 | **Crun.AI** | Only option with video support |
| 抠图换背景 | **Photoroom** | Professional e-commerce cutout |
| 语音合成 | **MiniMax** | TTS, needs Group ID |

### 8. Fal.ai SSL与CDN下载问题

Fal.ai有两个步骤都需要SSL绕过：
1. API请求：`requests.post(..., verify=False)` — 否则SSL握手失败
2. 图片下载：`requests.get(url, timeout=180, verify=False)` — Fal的CDN在国内非常慢（约110秒下载一张242KB的图）

**解决方案：** 使用 `requests.Session()` 全局设置 `session.verify = False`，下载超时设为180秒。

### 9. Crun.AI排队时间
Crun.AI的任务不是立即执行的，尤其是新模型（如GPT Image 2）可能排队：
- Gemini/Nano Banana：~15-30秒
- GPT Image 2：~6分钟（需排队）
- 视频模型：不定，建议设超时10分钟
- 推荐轮询间隔：15-30秒（Crun官方建议）

### 10. GPU服务器网络限制
服务器IP（159.75.12.11，腾讯云）访问海外API可能有网络限制：
- curl直接调API：正常（curl走不同网络栈）
- Python requests调API：可能遇到SSL证书验证问题
- **解决方法：** 统一加 `verify=False` 跳过SSL验证

### 11. 图片下载超时
不同API的CDN在国内访问速度差异大：
| API | CDN下载速度 | 建议超时 |
|:----|:-----------|:--------|
| TT API (MJ) | 快（国内CDN） | 30秒 |
| Crun.AI | 中等 | 60秒 |
| Fal.ai FLUX | 慢（海外CDN） | **180秒** |

### 12. Kling AI认证
Kling使用AccessKey + SecretKey → JWT token方式认证：
```python
import jwt, time
payload = {"iss": access_key, "exp": int(time.time())+1800, "nbf": int(time.time())-5}
token = jwt.encode(payload, secret_key, algorithm="HS256", headers={"alg":"HS256","typ":"JWT"})
# 然后 Authorization: Bearer {token}
```
Key还可能需要先去klingai.com后台绑定IP或购买Credits才能用。

### 13. MiniMax认证
MiniMax需要 API Key + Group ID 双重认证，Key格式是 `sk-xxx`，Group ID需要从 platform.minimax.io 获取。

### 14. siliconflow.cn FLUX模型已下架
截至2026年4月，SiliconFlow国内站（api.siliconflow.cn）已下架FLUX和Stable Diffusion等图片生成模型，只有Kolors可用。如需FLUX请走Fal.ai或国际站 api.siliconflow.com。

### 15. 任务队列提交规范
- **不要连续提交多个测试任务** — 等前一个出结果后再决定下一步
- **先小prompt测试** — 确认API通了再用正式prompt
- **控制任务数量** — 避免排队任务太多浪费Credits
- **一次只跑一个生成任务** — 等结果出来再提交下一个

## 常见问题

### 1. dispatcher找不到模块
- 检查包装文件是否在正确的Agent目录下（`agent_outputs/{agent_name}/`）
- 检查文件名是否匹配TASK_MODULE_MAP中的module名
- 包装文件路径：`agent_outputs/{agent}/{module_name}.py`

### 2. API返回401/403
- Key可能在武器库文档中有省略号（`sk-enn...qmwp`），SECRET.md才是完整Key
- 有些模型需要先在后台开通权限（如SiliconFlow的FLUX）
- Fal.ai的`-u key:secret` 不工作，要用 `Authorization: Key {key_id}:{key_secret}`

### 3. 任务completed但output_file=null / module_result为空
- dispatcher传参方式：`payload.get("args", {})`，参数需放 `args` 字段下
- 如果payload根级有参数但没放args里，传过去的是空字典
- 模块函数最好用 `**kwargs` 处理多余参数

### 4. payload格式规范
任务派发到task_queue时，参数必须放在 `args` 下：
```json
{"task":"描述", "args": {"prompt": "...", "model": "..."}}
```

### 5. 图片生成时间参考
| API | 出图时间 | 费用 |
|:----|:--------|:----|
| Fal.ai (FLUX Schnell) | ~0.15秒 | $0.003-0.025/张 |
| Crun.AI (Nano Banana) | ~15秒 | 3-12 credits |
| TT API (MJ v6) | ~45-60秒 | $0.02-0.05/张 |

### 6. 下载图片注意事项
- MJ返回的image_url有时效性，拿到后要立刻下载保存
- Crun.AI返回的media_urls同理
- 建议统一存到 `agent_outputs/moqing/generated/` 下按API分类

### 7. 引号陷阱
当通过execute_code在本地测试服务器命令时，Python字符串嵌套引号极易出错。**建议将测试脚本写成独立文件上传到服务器执行**，避免在终端命令中嵌入Python代码。
