---
name: mojiajun-comic-series-production
description: 窑滚人生搞笑漫画系列全链路——角色拟人化+双风格混搭+规范冻结+cron定时生成。适用于将文化IP转化为可追更的搞笑漫画系列。
team: 墨家军
cost_per_episode: 0.12
---

# 墨家军漫画系列生产全链路

## 核心框架

### 战略定位
- **不做硬科普**，用搞笑漫画把文化IP"活"起来
- 角色性格 > 画工精致
- 系列化、可追更、培养粉丝群
- 小红书赛道验证："陶瓷拟人化+搞笑"=蓝海（零竞品）

### 双风格混搭（窑滚人生验证）

| 风格 | 用途 | 位置 |
|------|------|------|
| **日系古风插画** | 正片剧情 | 每期4-6格正文 |
| **Q版萌系** | 片尾科普彩蛋 | 最后一格"小课堂" |

理由：古风有质感但不适合搞笑，Q版天然好笑但深度不足。两者互补：古风讲故事，Q版讲知识。

---

## 角色设计四步法

### 1. 素材挖掘
从真实文化素材中提取"自带笑点"的特征：
- 青花瓷=釉下彩千年不褪→"老干部人设"
- 玲珑瓷=生产事故发明→"摸鱼改变世界"
- 颜色釉=窑变无双→"盲盒体质"
- 把桩师傅吐唾沫测温→"千年传统科技"

### 2. 命名公式
`艺术化名字（瓷器类型括号注）`，让不懂陶瓷的人也一眼看懂
- 青隐（青花瓷）——钴料隐于釉下
- 软彩（粉彩瓷）——粉彩古称
- 米通（玲珑瓷）——玲珑瓷别称
- 窑变（颜色釉）——核心特征

### 3. 角色视觉规范冻结（最关键）
每个角色必须冻结以下参数，一旦确认不可改：
- 发型、发色、脸型、眉型、眼型、五官
- 身高比例、体型
- 服装款式、纹样、精确色值（HEX）
- 站姿、表情特征
- **不可变细节标记**（如泪痣、镂空孔排列方式）

规范文档保存为项目资产，所有后续prompt严格引用。

### 4. 客串角色池
- 无语佛（博物馆IP借力）
- 窑工老李（人类吐槽担当）
- 珐琅彩（贵族亲戚，偶尔凡尔赛）
- 泥巴（原始形态，回忆杀出现）

---

## 一期漫画生产流水线

### 脚本格式
```markdown
## 格1
- 场景：窑厂院子，全景
- 人物：青隐（C位，抱臂仰头）
- 动作：正在说话，表情骄傲
- 对白：四大名瓷，青花为首

## 格2
...
```

### Prompt生成
每格Prompt = `角色锚定段` + `场景描述` + `NO text on image`

角色锚定段从规范文档提取，包含所有角色的外貌、服装、配色、比例。

**关键规则**：
- 每格Prompt必须引用完整角色锚定（不用缩写）
- `NO speech bubbles, NO text on image` 必须写
- 光源、阴影、风格关键词固定

### 生成方式
- **串行（当前）**：CORE-01上依次调cruna_api.generate_image()，每格2-3分钟
- **并行（升级后）**：task_queue 6 worker同时跑，总时间≈单格时间
- **cron定时**：设定凌晨自动生成，早上直接审

### 中文气泡叠加（2026-05-04 4轮迭代验证）

**为什么不用GPT Image 2直接渲染中文？** → 不稳定，且角色一致性优先。所有图生成后本地PIL叠加。

**标准参数**（1086×1448 图验证）：
```python
from PIL import Image, ImageDraw, ImageFont
font = ImageFont.truetype('/System/Library/Fonts/STHeiti Light.ttc', 52)  # 52px最佳
pad, radius = 35, 20  # 内边距和圆角
# 气泡：白色圆角矩形 + 向下三角形尾巴
draw.rounded_rectangle([bx,by,bx+bw,by+bh], radius=radius,
    fill=(255,255,255,242), outline=(100,100,100,220), width=3)
draw.polygon([(tc-18,by+bh-1),(tc+18,by+bh-1),(tc,by+bh+22)], fill=(255,255,255,242))
```

**位置规则**：
- y：统一 `h * 0.015`（21px贴顶），三角形尾巴向下指向角色头部，不遮脸
- x：左角色 `w * 0.28` / 中角色 `w * 0.50` / 右角色 `w * 0.63`
- 迭代教训：28px太小看不见 → 52px；4%遮头 → 1.5%贴顶；气泡不对准角色 → 按x_pct精调

**GPT Image 2 prompt必须加**：`NO text, NO speech bubbles, NO watermarks.`

---

## GPT Image 2 最新技巧（2026-05 社区共识）

### 五要素Prompt框架
```
[任务类型] + [主体描述] + [风格定义] + [技术参数] + [输出规格]
默认最佳：3:4竖版 / 1:1漫画格，2K分辨率，Thinking Mode复杂场景

### 5条铁律
1. **主体前置**：核心主题放prompt前30%
2. **上屏文字用引号**：中文双引号括起来，准确率70%→95%
3. **加镜头参数**：85mm/柔光/浅景深，物理引擎响应
4. **正向约束替代负向**：不说"no text"，说"image only, clean panels"
5. **编辑分两步**：改什么/保什么，分两个prompt

### 2026-05-06 升级：否定词+一致性（从 awesome-gpt-image-2 仓库学习）
6. **强否定词**（注入config.py）：`no plastic skin, no airbrushing, no different face, no 3D render, no realistic photo, no cosplay`
7. **身份一致性**：`same person, same face, same identity, consistent character design` 必须出现在每格prompt
8. **风格锚定**：`hand-drawn 2D animation, cel-shaded, flat color blocking` 避免AI默认走写实
9. **参考仓库**：freestylefly/awesome-gpt-image-2（360+案例），EvoLinkAI/awesome-gpt-image-2-prompts（7500星）

### 漫画格专用
1. 角色一致性：固定模板 age/ethnicity/features/attire 每格注入
2. 群像格：编号标注位置 "Left: [A], Center: [B], Right: [C]"
3. 气泡留白：末尾加 "NO speech bubbles, NO text overlay, clean panels"
4. 中文文字仍建议PIL叠加（95%准确但不绝对）
5. 不再堆砌"8K ultra detailed"等关键词（v2默认高质量）

### 已知边界
| 能力 | 状态 | 备注 |
|------|------|------|
| 中文渲染 | ✅ ≥95% | 短文本(≤5字)可直接用，长文本仍PIL叠加 |
| 人物一致性 | ⚠️ 有差异 | 靠角色锚定+参考图+规范三层锁定 |
| 编辑模式 | ✅ | /edit endpoint精准局部修改 |
| 1:1方形 | ✅ | aspect_ratio="1:1" |
| 费用 | $0.02/格 | 一期6格=$0.12 |
| 速度 | ~3s Instant / ~15s Thinking | 草稿用Instant，成品用Thinking |

---

## 能力转化方法论（学而不装）

遇到外部工具/项目时，遵循"吸收不安装"原则：
1. 拆解核心能力→哪些是墨家军可以自己做的
2. 按优先级排序→立即可做/短期/远期
3. 转化为墨家军module/skill
4. 避免新增外部依赖，除非有不可替代的价值

例：MeiGen的prompt增强→墨家军自己写`comic_prompt_enhancer.py`，更精准且不依赖第三方。

---

## 世界观设定（2026-05-04锁死，不可变）

四人同住一栋公寓（类似爱情公寓模式），各住各的房间，公共阳台/客厅是日常碰面场景。
- 青隐常年占据阳台泡茶位
- 窑变房间最乱，旅行箱永远没打开
- 软彩的冰箱被妈远程遥控塞满
- 米通房间最整洁（太少在家）

## 角色造型规范（2026-05-04 从EP1+概念图提取，不可变）

### 青隐（青花瓷）— 佛系躺平，爱吐槽
- 正片：黑色长发微卷凌乱，长脸，深蓝色宽袖汉服长袍+白色内衬+青花蓝纹，高挑修长，双臂交叉，冷峻内敛
- Q版：深蓝色发髻+白色蝴蝶结，蓝白汉服长袍+浅蓝花卉刺绣，温和微笑，双臂交叉

### 软彩（粉彩瓷）— 热情话多，容易激动
- 正片：深棕色双麻花辫+粉色花朵发饰，圆脸，粉色洛丽塔长裙+荷叶边+蕾丝+蝴蝶结，娇小，双手叉腰，笑容灿烂露齿
- Q版：棕色长卷发+粉色花朵发饰，粉色连衣裙+金色花纹+蝴蝶结，笑容灿烂，双手叉腰

### 米通（玲珑瓷）— 老实憨厚，经常被坑
- 正片：银白色长发波浪披肩，瓜子脸，白色长裙+镂空蕾丝+淡蓝金色星点花纹，娇小纤细，双手交叠胸前，害羞内向
- Q版：银白色长直发+蓝色小花珠串，白色长裙+淡蓝花纹，温柔恬静，双手合十胸前

### 窑变（颜色釉）— 热情奔放，玩疯了
- 正片：橙红色短发蓬松凌乱，长脸，深红→深绿渐变长袍+流苏碎布+不规则边缘，高大修长，双臂张开，开朗自信张扬
- Q版：橙红色短发蓬松，彩虹渐变长袍（橙→绿→蓝）+星光斑点，笑容开朗露齿，双臂张开

## 自动化模块

### comic_planner.py（墨创Agent，CORE-01）
- 位置：`/home/ubuntu/mojiajun-queue/agent_outputs/mochuang/comic_planner.py`
- 注册：`module_dispatcher.py` → `"comic_script": ("mochuang", "comic_planner", "plan")`
- 功能：接收theme/roles/grids/tone → 调DeepSeek生成4格脚本+Q版彩蛋+配文
- 依赖：`DEEPSEEK_API_KEY`（模块顶部自动加载`.env`，不依赖worker环境变量）
- 费用：~824 tokens/次 ≈ $0.001
- 部署方式：base64编码传输（SSH heredoc会破坏Python字符串中的引号）

## 漫画标题方法论（大威 2026-05-04 亲自验证，多轮淘汰）

**核心发现：漫画标题 ≠ 笔记标题。笔记可以用"X种人""X个方法"的分类式，漫画不行。**

大威在看到以下标题后的真实反馈：
- ❌「五一朋友圈三种人」「收假前夜全世界分两种人」→ "没吸引力"
- ❌「放完五天假，朋友步数3万，我步数极少」→ "37步夸张了"
- ❌ 太抽象、太描述内容 → 一律不行
- ✅「你们明天还能上班吗？」→ "还行"

**大威被吸引的标题规律**（从他亲口说的例子分析）：
- 「蓝莓居然不是蓝色的」→ 反常识，自己就是答案
- 「看一场五万块的雨」→ 数字画面，自己就是故事  
- 「想买个盖碗从七八百蹲到一千多」→ 真实经历，自己就是共鸣

**漫画标题正确写法：标题本身就是一条完整、有意思的信息，不需要额外解释。**

三大有效策略（按优先级）：
1. **裸放一句有力对白**：「你们明天还能上班吗？」— 0.5秒触发"谁说的？为什么？"
2. **反常识事实**：漫画里有什么和常人认知相反的点？
3. **具体画面/数字**：不是"步数很少"而是具体的画面感

**硬规则**：
- 绝对不用"X种人""X类人"分类式标题（大威亲自毙了多轮）
- 不在标题里解释漫画内容
- 不超过20字
- 封面和标题配合——标题是钩子，封面给答案

## 封面出图标准流程（2026-05-04验证）

1. **底图生成**：`gen_image_crun` (GPT Image 2) → aspect 3:4，日系古风，角色造型严格引用EP1规范，上方三分之一留白
2. **标题叠加**：`make_cover` (PIL) → 在留白区域叠加中文标题文字
3. **输出**：JPEG，~200KB，无文字水印

## 运营节奏

- 每周2期
- 每期4格正片+1格Q版彩蛋
- 评论区预埋3条引导互动的评论
- 每5期微调一次角色规范（基于数据反馈）
- 世界观和角色造型一旦确认锁死，后续prompt严格引用

---

## 完整生产流水线（实战验证 2026-05-04）

```
大威下需求 → 小川制定计划 → 墨创comic_planner出脚本(DeepSeek) → 大威审核 
→ 墨青并行出图(6张:封面+4格+Q版) → 封面叠加标题 → 桌面交付
```

关键环节：
- **脚本策划**：墨创 `comic_planner.py` 调 DeepSeek，payload含 theme/roles/grids/tone/note_req
- **并行出图**：6个 `gen_image_crun` task 同时入队，墨青 worker 逐个处理（2-4min/张）
- **封面标题**：先用 GPT Image 2 出底图，再用 `make_cover` 叠加中文标题

## 喜剧创作核心教训（2026-05-06 实战验证）

**DeepSeek无法写出真正好笑的段子**。多轮实测证明：
- DeepSeek生成的脚本只是"构造"笑点（结构对但没灵魂）
- 真正好笑的内容来自：①人类验证过的段子 ②角色特性驱动的自然冲突 ③短对话+意外反转
- 正确流程：人找素材（网上好笑段子/自身经历）→ 换角色名 → 人审 → 出图

**四种验证有效的喜剧结构**：
1. 预期反转：米通说透光→窑变验证手冷→米通"今天没吃饭"
2. 物理特性喜剧：玲珑镂空孔→漏风→伸手验证→反转
3. 一句话暴击：前三格铺垫，第四格用最少字收尾
4. 属性错用：把瓷器专业术语用在日常场景

**失败经验**：
- 强行科普=必死。先好笑，知识藏在笑点里
- 长篇叙事=没人看。对话越短越好（每格≤15字）
- AI生成笑话=不行。必须人审素材
- 陶瓷知识错误=致命（瓷器都防水、四大名瓷都高温、粉彩先高温后低温烤彩）

**EP1生产全链路实录**（2026-05-06）：
1. 主题：四人阳台+天冷+米通镂空漏风→反转
2. comic_planner出脚本（DeepSeek）→ 大威审 → "C有点好笑"
3. CrunClient.generate_image(model="gpt-image-2", aspect_ratio="1:1") 生成5张
4. 本地PIL 2x2拼图 + 36px STHeiti气泡贴顶 + 52px标题
5. 已知问题：AI多画了一个人（软彩不该在场）、个别面板角色造型漂移

## 漫画标题方法论（实战教训）

❌ 不要用：分类式（"X种人"）、描述式（描述漫画内容）、讲道理式
✅ 要用：**对白直接做标题**——漫画里最有冲击力的一句台词，不加任何解释

用户真正会点的标题特征（来自用户本人反馈）：
- 「蓝莓居然不是蓝色的」→ 反常识，自己就是答案
- 「看一场五万块的雨」→ 数字画面，自己就是故事
- 「想买个盖碗从七八百蹲到一千多」→ 真实经历，自己就是共鸣

漫画标题同理——**标题本身就是一条完整、有意思的信息**，不需要"室友原话""窑滚人生"等解释词。

## 角色造型锁定规范（EP1参考）

所有 GPT Image 2 prompt 必须注入精确角色描述（从 EP1 概念图提取）：

**青隐（青花瓷）**：young man, shoulder-length slightly messy wavy black hair, delicate oval face, cold deep-set eyes, slightly downturned lips, deep blue wide-sleeve Hanfu cross-collar robe + white inner, blue floral porcelain patterns, arms crossed, aloof restrained

**软彩（粉彩瓷）**：petite young woman, brown hair in double braids + pink flower decorations, round cute face, bright cheerful smile, pink Lolita-style dress with ruffled layers and lace, hands on hips

**米通（玲珑瓷）**：slender delicate young man, long silver-white wavy hair, small delicate face, shy timid, white flowing dress with lace, hands clasped at chest

**窑变（颜色釉）**：tall young man, messy orange-red short spiky hair, confident wild grin, gradient robe deep-red→green→blue with tattered edges and fringe, arms spread wide

## 世界观锁定

四人同住一栋公寓（爱情公寓模式），公共阳台是碰面场景。空间关系：
- 青隐常年占据阳台泡茶位
- 窑变房间最乱，旅行箱永远没打开
- 软彩冰箱被妈远程遥控塞满
- 米通房间最整洁（太少在家）

## 墨创 comic_planner 模块部署要点

1. **文件位置**：`agent_outputs/mochuang/comic_planner.py`
2. **注册到 module_dispatcher**：`"comic_script": ("mochuang", "comic_planner", "plan")`
3. **.env 加载**：模块顶部必须自己加载 `.env`（agent_worker 不会注入环境变量）
4. **传输方式**：SSH heredoc 和 Python 字符串冲突 → 用 `base64` 编码传输
5. **重启 worker**：修改 module_dispatcher.py 后必须 `pkill -f 'agent_worker.py mochuang'` 并重启

## GPT Image 2 Prompt 升级（2026-05-06 从 2 个仓库 + 1 篇实战文章提炼）

### 负面词升级（config.py DEFAULT_NEGATIVE）
```
旧：low quality, blurry, distorted anatomy, extra fingers, missing limbs, watermark, text, signature
新：+ no plastic skin, no airbrushing, no different face, no face change,
    + no 3D render, no realistic photo, no cosplay, no modern clothing,
    + consistent character design, same person, same identity
```

### 古风锚点升级（config.py STYLE_ANCHOR_ANCIENT）
```
+ consistent character appearance, fixed costume design,
+ hand-drawn 2D animation style, non-photorealistic,
+ flat color blocking, cel-shaded
```

### 技术参数升级（config.py DEFAULT_TECH_PARAMS）
```
+ consistent art style across all panels, coherent visual storytelling,
+ editorial illustration quality, clean composition
```

### Prompt增强器规则（prompt_enhancer.py 新增第6条）
```
CRITICAL: For multi-panel comics, add 'consistent character design, 
same face, same identity across all panels' to negative and tech params.
```

### 来源
- EvoLinkAI/awesome-gpt-image-2-prompts（7500星，340+案例）
- freestylefly/awesome-gpt-image-2（360+案例，13类模板）
- 文章《gpt-image-2-prompt两天冲上7500星，拆解340个cases总结7种高级prompt结构》

## 实战教训（2026-05-06 窑滚人生EP1实战）

### 脚本创作
- ❌ DeepSeek写不好笑点——它能构造"正确"的笑话结构，但写不出自然好笑的内容
- ✅ 从网上验证过的段子改编到角色身上，效果远好于AI原创
- ✅ 瓷器本身的物理特性是天然笑点（透光、变色、千年不褪），比硬塞日常梗更自然
- ✅ 四人对白节奏：格1设问→格2解释→格3质疑→格4反转。每格对白≤15字

### 画风选择
- ❌ 日系古风动画风 → 大威不喜欢
- ❌ 水墨画风（水墨画）→ "太复杂，零零碎碎，没有美感"
- ❌ 画风必须在正式批量出图前，用单张测试图确认偏好
- ⚠️ 后续方向：极简线描/白描/干净色块

### 出图技术
- ✅ GPT Image 2 通过 CrunClient (`agent_outputs.moyuan.api_toolkit.crun_api`) 调用
- ✅ `generate_image()` 返回的是本地文件路径（`filepath`），不是URL
- ✅ prompt必须加 `EXACTLY N characters, NO fourth person` 防止多出角色
- ✅ 角色描述用简洁英文关键词，不写长段落

### 气泡叠加
- ✅ PIL叠加中文——字体 STHeiti 36px，白色圆角矩形+三角形尾巴
- ❌ 气泡不能统一放顶角——应该精准贴近每个说话角色的嘴部
- ⚠️ 气泡位置需后续迭代精调

### 名字太直白
"青花""粉彩"→用户无感。要艺术化+括号注明：青隐(青花瓷)

### Prompt不引用规范文档
每期手写prompt→角色造型漂移。必须程序化注入规范文档。

### 忽视"冷知识"的价值
搞笑漫画的护城河不是笑话，是背后的真实素材。玲珑瓷是生产事故发明的、把桩师傅吐唾沫测温——这些"冷知识"才是用户收藏分享的理由。

### 造型确认后再改
造型一旦确认锁死。后续所有prompt严格引用规范文档，不允许"微调一下"。

### GPT Image 2角色一致性实战教训（2026-05-04）
- **性别必须显式声明**：prompt中必须写"MALE"/"FEMALE"/"young man"/"young woman"，否则chibi风格默认偏女性
- **EP1参考图是唯一标准**：prompt偏离EP1造型一个字，角色就会漂移（如长发披肩 vs 及肩微卷）
- **Q版必须单独标注性别**：Q版prompt中"cute"等词会触发女性化默认

### 对话气泡叠加实战参数（2026-05-04）
基于1086×1448图片的验证参数：
- 字号：52px（STHeiti，28px完全看不见）
- 气泡位置：bx_pct对准角色头部x中心，by_pct≈0.015（紧贴顶部）
- 三角形尾巴：向下指向角色，tc±18/20px
- 气泡padding：35px，圆角radius：20px
- 关键原则：气泡贴顶放，尾巴指向人物 → 不挡脸

### SSH heredoc吃引号
向CORE-01传Python脚本时，**优先用 base64 编码**，避免所有 shell 转义问题。
```bash
base64 -i local_file.py | ssh server "base64 -d > /remote/path/file.py"
```

### module_dispatcher 引号丢失
用 Python 编辑远程 Python 文件时，`"` 可能被 shell 吃掉。始终用 `sed -i` 或 Python 脚本精确替换，事后验证导入。

### GPT Image 2 封面造型漂移
不提供精确角色描述 → 生成柔美长发版而非冷峻内敛版。每张图 prompt 必须包含发型/脸型/五官/服装的完整描述。

### 漫画格图并行策略
6张图一次性入队让墨青串行处理（~15min），比逐个提交效率高。每张 1:1 方形，prompt 末尾加 `NO text, NO speech bubbles, NO watermarks.`
