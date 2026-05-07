---
name: gpt-image-2-comic-generation
description: GPT Image 2 漫画角色生成实战经验——角色一致性prompt写法、性别锁定、气泡叠加、标题策略。基于窑滚人生EP2实战。
version: 1.0.0
tags: [comic, gpt-image-2, character-consistency, bubble-overlay, mojiajun]
---

# GPT Image 2 漫画角色生成实战经验

## 核心发现

### 1. 角色一致性 = Prompt精确度
GPT Image 2没有MJ cref或Ideogram Character那样的面部锁定机制。角色一致性完全靠prompt精确描述。

**必须锁定5维度**：
- 发型（颜色、长度、造型、质感）
- 脸型（瓜子脸/圆脸/长脸）
- 眼神/表情（冷峻深邃/热情开朗/害羞内向）
- 服装（款式、颜色、纹样、层数）
- 体型/姿态（高挑修长/娇小/双臂交叉/双手叉腰）

❌ 模糊描述："an ancient-style character with blue clothes"
✅ 精确描述："a young man with shoulder-length messy wavy black hair, cold deep-set eyes, deep blue wide-sleeve Hanfu cross-collar robe with white inner layer and blue floral patterns, arms crossed"

### 2. 性别必须显式指定
GPT Image 2默认倾向模糊化性别。每个角色prompt必须显式写 `MALE` 或 `FEMALE`/`WOMAN`。

**教训**：Q版青隐变成了女性 → prompt加了 `MALE chibi character, masculine facial features NOT feminine` 后才正确。
**教训**：米通（设定女性）变成男性 → prompt从 `young man` 改为 `young WOMAN with long silver-white wavy hair`。

### 3. Prompt中 `` ` `` 和引号会炸shell heredoc
向CORE-01传Python文件时，shell heredoc (`<< 'PYEOF'`) 会解析代码中的特殊字符。

**解决方案**：
- 本地写文件 → base64编码 → SSH管道传 → base64解码写入
- 命令：`base64 -i local.py | ssh host "base64 -d > remote.py"`

### 4. Worker模块的.env加载
CORE-01的agent_worker不会自动加载.env。需要在模块顶部自行加载：

```python
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

### 5. task_queue返回值不含模块产出
`task_queue.result` 字段只有 `status/success/est_cost/output_file` 等元信息。实际模块产出（脚本JSON、图片URL）在 `agent_outputs/{agent}/` 目录中。

**正确做法**：从task_queue拿output_file路径 → 直接读该文件获取module_result。

### 6. 气泡叠加：本地PIL vs 远程comic_bubbler
SCP经常被封时，本地PIL叠加比远程comic_bubbler更可靠。

```python
def add_bubble(img_path, text, output_path, bubble_x_pct=0.5, bubble_y_pct=0.12):
    img = Image.open(img_path).convert('RGBA')
    w, h = img.size
    overlay = Image.new('RGBA', (w, h), (0,0,0,0))
    draw = ImageDraw.Draw(overlay)
    
    bbox = draw.textbbox((0,0), text, font=font)
    tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
    pad = 20
    bx = int(w * bubble_x_pct) - tw//2 - pad
    by = int(h * bubble_y_pct)
    bw, bh = tw + pad*2, th + pad*2
    
    r = 15
    draw.rounded_rectangle([bx, by, bx+bw, by+bh], radius=r, fill=(255,255,255,235), outline=(180,180,180,200), width=2)
    
    # 三角形尾巴
    tail_cx = bx + bw//2
    tail_points = [(tail_cx-12, by+bh-2), (tail_cx+12, by+bh-2), (tail_cx, by+bh+18)]
    draw.polygon(tail_points, fill=(255,255,255,235))
    
    draw.text((bx+pad, by+pad), text, fill=(30,15,5), font=font)
    result = Image.alpha_composite(img, overlay)
    result.save(output_path)
```

### 7. 标题策略：漫画标题 ≠ 笔记标题
漫画标题不需要描述内容或分类。大威被吸引的标题特征：**标题本身就是一条完整、有意思的信息**。

- 「蓝莓居然不是蓝色的」→ 反常识信息
- 「看一场五万块的雨」→ 数字画面
- 「你们明天还能上班吗？」→ 对白本身制造悬念

❌ "四种人""三种人"分类式 → 没吸引力
✅ 一句话信息/对白/反常识 → 让人想点

### 8. module_dispatcher注册陷阱
用Python修改module_dispatcher.py时，引号容易被吃掉：
```python
# ❌ 写入后变成裸奔的变量名
comic_script: (mochuang, comic_planner, plan)

# ✅ 正确
"comic_script": ("mochuang", "comic_planner", "plan"),
```
修复用sed：
```bash
sed -i '46s/.*/    "comic_script":       ("mochuang", "comic_planner",       "plan"),/' module_dispatcher.py
```

### 9. Prompt中 NO text 导致图空白
所有prompt加了 `NO text, NO speech bubbles` 后，图上是空白的。漫画格需要后续PIL叠加对白文字。这是设计选择——GPT Image 2中文渲染不稳定，PIL叠加更可控。

### 10. GPT Image 2不严格遵循aspect参数
prompt指定 `aspect: 1:1` 但实际出图是 1086x1448 (3:4)。需要在prompt中强调 `square format, 1:1 aspect ratio`。
