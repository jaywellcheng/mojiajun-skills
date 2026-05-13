---
name: xiaohongshu-4-panel-comic-generation
description: >-
  为小红书笔记生成4格搞笑漫画的完整工作流。经过多工具实战对比（FLUX/MJ/PIL/GPT Image），
  唯一可行方案是GPT Image。含Crun API调用、PIL中文叠加、字体路径、常见避坑。
---

# 小红书4格漫画生成工作流（2026-04-28实战验证）

## 核心结论：只有GPT Image能画4格漫画

经过一整天对比测试：

| 工具 | 多场景控制 | 人物一致性 | 漫画风格 | 中文 | 结论 |
|------|-----------|-----------|---------|------|------|
| FLUX schnell | ❌ | ❌ | ❌ 僵硬不搞笑 | ❌ 乱码 | 不可用 |
| MJ niji 单prompt | ❌ 场景被简化 | ✅ | ✅ 专业 | ❌ 乱码 | 场景不准 |
| MJ niji 分格+seed | ✅ | ❌ 每张不同人 | ✅ | ❌ 乱码 | 人物不一致 |
| MJ niji --cref | ⚠️ | ❌ 不像 | ✅ | ❌ | 参考图不生效 |
| PIL纯代码 | ✅ | ✅ | ❌ 太简陋 | ✅ | 用户看不懂 |
| **GPT Image（Crun）** | ✅ | ✅ **唯一** | ✅ | ❌ | **🏆 胜出** |

**关键发现：** GPT Image是唯一能在4格漫画中保持同一人物长相的AI。其他工具要么人物变来变去，要么场景不可控。

## 方案A：GPT Image单prompt 4格（已验证可用）

### 适用场景
快速出图，人物一致，场景基本还原。适合"够用就行"的场景。

### Prompt结构
```
A 4-panel comic strip drawn in warm-toned cute cartoon style with soft colors.
Panel 1: [场景描述 + 人物状态 + 关键道具 + 背景]
Panel 2: [同上]
Panel 3: [同上]
Panel 4: [同上]
The four panels must show THE SAME [人物描述] with consistent appearance throughout.
Clear 2x2 grid layout with white borders. Warm colors, no text on image.
```

### 人物描述模板
```
A chubby middle-aged Chinese man, 45, short black hair, round gentle face, 
warm expression, wearing a blue collared shirt
```

### 关键技巧
- **不要用英文月份名**："April"会被GPT理解为人名，用"April 28th"或数字
- **每格明确标注Panel N**：帮助GPT理解布局
- **强调"THE SAME"**：大写强调人物一致性
- **no text on image**：GPT也不支持中文，乱码不如空白

## 方案B：GPT Image分格生成+拼接（精度更高，验证中）

### 原理
4个prompt各描述一个场景，都用同一角色描述锁定人物，PIL拼接2×2。

### Prompt结构
```python
CHARACTER = 'A chubby middle-aged Chinese man, 45, short black hair, round gentle face, warm expression, wearing a blue collared shirt'

prompts = [
    f'{CHARACTER}. [场景1描述]. Cartoon illustration style, soft warm colors, no text.',
    f'{CHARACTER}. [场景2描述]. Cartoon illustration style, soft warm colors, no text.',
    # ...
]
```

### 优势
- 场景精度远高于单prompt（每张专注一个场景）
- 人物一致性靠相同角色描述保证（GPT已验证能做到）

## Crun.AI API调用细节

### Key信息
- Key在 `/home/ubuntu/mojiajun-queue/agent_outputs/moyuan/api_toolkit/crun_api.py`
- 35字符，格式 `ak_xxx...`（终端显示截断但Python import正常）
- 不要被截断显示误导！实际完整可用

### 创建任务
```python
resp = requests.post(
    'https://api.crun.ai/api/v1/client/job/CreateTask',
    headers={'X-API-KEY': API_KEY, 'Content-Type': 'application/json'},
    json={
        'model': 'openai/gpt-image-2',
        'input': {
            'prompt': prompt,
            'aspect_ratio': '1:1',
            'num_outputs': 1,
        }
    },
    timeout=30
)
task_id = resp.json()['data']['task_id']  # 注意嵌套!
```

### 轮询结果
```python
resp = requests.get(
    f'https://api.crun.ai/api/v1/client/job/TaskInfo?task_id={task_id}',
    headers={'X-API-KEY': API_KEY}, timeout=15
)
data = resp.json()
status = data['data']['status']  # 注意嵌套: data.data.status

# 取图URL：data.data.result.media_urls[0]
media_urls = data['data']['result']['media_urls']
```

### ⚠️ API响应嵌套结构（这是最大的坑）
```
{
  "data": {
    "task_id": "xxx",          // task_id在data.data里
    "status": "success",       // status也在data.data里
    "result": {
      "media_urls": ["url"]    // 图片URL在data.data.result.media_urls
    }
  }
}
```
**不要**用 `data.get('task_id')` — 它在两层嵌套下。正确：`data['data']['task_id']`

### 生成时间
- 每张：3-5分钟（GPT排队+生成）
- 4张并行：约5-10分钟
- 轮询间隔：10秒

## PIL中文叠加

### CORE-01字体路径（2026-04-28确认）
```python
font_paths = [
    '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc',        # 文泉驿正黑
    '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',  # Noto Sans CJK
]
```
**注意**：之前文档中的 `wqy-microhei.ttc` 路径已不存在！

### 叠加布局设计
推荐 "顶部标题栏 + 底部对话栏" 模式：

```python
# 布局参数
top_h, bot_h = 60, 260      # 顶部标题栏60px + 底部260px
canvas_w, canvas_h = w, h + top_h + bot_h

# 顶部：半透明深色bar + 白色标题（32-38号字体）
overlay = Image.new('RGBA', (w, top_h), (50, 35, 20, 220))
draw.text((16, 10), '🏺 标题', fill=(255, 245, 220), font=ftitle)

# 底部：米色面板 + 对话文字（22号字体）+ 标签
draw.rectangle([(0, bot_y), (w, bot_y + bot_h)], fill=(255, 248, 235, 255))
for line in dialog_lines:
    draw.text((16, y), line, fill=(55, 30, 18), font=fbody)
```

### 字体大小参考
- 标题：38号
- 副标题：26号
- 正文对话：22号（太小看不见！之前18号就踩坑了）

### 对话气泡内嵌文字（待实现）
PIL可以在图任意位置覆盖文字。需要定位对话气泡坐标——可估算（4格网格均分），用白底覆盖原气泡再写中文。

## 故事脚本设计原则

### DO ✅
- 真实生活场景（猪脚饭、失眠、看医生）——用户有共鸣
- 轻松幽默、不煽情、不尬
- 接地气的对话（"翻底款"、"没药"）
- 最后一格有反转包袱
- 场景有明显视觉区分（快餐店/卧室/诊室/递处方）

### DON'T ❌
- 硬塞陶瓷/产品元素——不自然
- 用"姐妹们""集美们"——大威45岁男人
- 刻意煽情"破防""泪目"
- 4格场景太相似（会混淆）
- 对话太长——一格最多两句话

## 失败方案记录（避免重蹈）

### MJ niji 单prompt → 场景被简化
prompt描述了"快餐店→卧室→诊室→递处方"，niji把4格全变成了诊室场景。niji偏好视觉连续性。

### MJ niji 分格+seed锁定 → 人物不一致
4张都用 `--seed 7777`，但每张的人物长相都不同。seed不保证人物一致性。

### MJ --cref 角色参考 → 不像
需要公网URL上传参考图，但生成结果"完全不象我"。

### FLUX → 漫画风格差
人物表情僵硬、不搞笑、暖色调不够温暖。FLUX本质是照片写实模型。

### PIL纯代码 → 太简陋
几何图形拼人物，用户说"不知所云""如果不是看到过方案故事，一张图都看不懂"。

## 完整出图流程总结

```
1. 故事脚本（大威确认）
    ↓
2. GPT Image生成4格漫画（Crun API）
    ↓
3. 下载 → PIL叠加中文对话（顶部标题+底部文字）
    ↓
4. 拉本地 → 大威审核
    ↓
5. 发布小红书 + 预埋评论
```

## 墨家军能力目标

将此流程固化为墨家军标准能力：
- `moqing/api_entry.py` 注册 `gen_comic_4panel` 任务类型
- 输入：故事脚本JSON
- 输出：带中文的4格漫画PNG
- 自动化：Crun提交→轮询→下载→PIL叠加→入库
