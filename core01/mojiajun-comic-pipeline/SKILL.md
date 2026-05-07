---
name: mojiajun-comic-pipeline
description: 墨家军出图流水线v2——T1-T8完整工具链，六层Prompt+光线+色彩+去AI+配方+气泡规范
team: 墨家军
version: 2.0.0
---

# 墨家军出图流水线 v2.0

## 架构

墨金搜灵感 → 墨蓝写prompt → 墨青出图 → 小云调度+入库

## 核心模块（CORE-01）

路径：`/home/ubuntu/mojiajun-queue/agent_outputs/tools/comic_pipeline/`

```python
from comic_pipeline import *

# T1 Prompt增强 v2.1（六层输出 + 智能选择）
enhance_prompt_local(scene="场景", characters=["青隐"])

# v2.1 新增参数
enhance_prompt_local(scene="场景", medium="连环画", lens="85mm",
                      realism_level=None,        # None=自动选择
                      auto_realism=True,         # 自动去AI级别
                      compatibility_mode=False,  # False=享受升级
                      return_meta=True,          # 效果预览
                      preset="product_ceramic",
                      preset_item="青花盖碗",
                      glaze_type="冰裂纹,亮面釉",  # 釉面质感
                      ceramic_lighting="青花透光") # 陶瓷光线

# T2 角色注入（含CRITICAL标注防米通变和尚）
inject("米通"); inject_all(); list_characters()

# T3 脚本拆解
parse_script(markdown) → generate_prompts(parsed)

# T4 并行调度
dispatch_comic_batch(panels) → check_batch_status(task_id)

# T5 模板库
templates/panel_single.md | panel_duo.md | panel_group.md | panel_q_bonus.md | style_anchor.md

# T6 风格研究员（挂载墨金）
style_research_weekly(); search_trends(["关键词"])

# T7 光线注入器 v2（关键词权重叠加+冲突检测）
match_lighting_from_scene("窑厂阳光") → 自动匹配光线配方
match_lighting_from_scene("古风茶具") → 返回 (光线描述, 冲突警告列表)
detect_lighting_conflicts(prompt) → 检测硬光/体积光等冲突
get_ceramic_lighting("青花") → 青花透光效果
register_lighting("新光线", "描述") → 动态注册光线预设
get_match_debug(scene) → 查看匹配过程

# T8 色彩控制器
inject_color("青隐", "暖高冷暗") → 角色70-25-5配色+冷暖对比
```

## 气泡叠加规范（Ep1实战教训）

- 每个气泡加说话人前缀 + 三角形尾巴指向说话人头部
- 位置靠近说话人，不遮脸
- GPT Image 2会自带"No text"之外的字（格5"控制不住"bug）→ 遮盖会破坏画面
- 群像格prompt加性别标记 + CRITICAL标注防角色混淆

## 程序化VFX层（新增 2026-05-06）

零API成本的代码生成纹理/特效叠层，与GPT Image 2 AI生图互补：
- **冰裂纹** (`crackle.py`): 金丝铁线双网，用于背景纹理叠加
- **粒子特效** (`particles.py`): 火焰/火花/烟雾，用于漫画格动态效果
- **纹样SVG** (`patterns.py`): 缠枝莲/冰梅纹/云纹/回纹/如意纹

模块位置：`~/.hermes/mojiajun-modules/mojiajun_vfx/`
bloom光晕实现教训见 `pil-particle-bloom-glowing` skill。

```
Markdown脚本 → T3拆解 → T2注入 → T1 v2六层增强 → T4并行出图 → PIL气泡 → 完成
```

## 引擎路由

| 场景 | 引擎 |
|------|------|
| 产品图/角色一致性/中文文字 | GPT Image 2 |
| 古风艺术/氛围感 | Midjourney |
| 快速测试 | FLUX |
| **纹理/粒子/纹样（零成本）** | **程序化生成(PIL/p5.js)** |

## 程序化生成补充能力（2026-05-06 从TOC+Generative Design提炼）

> 两本书(The Nature of Code / Generative Design)教的是procedural generation——算法驱动生成，不调API。零成本、无限变体、数学精确。与AI生图互补：**AI画角色和场景，代码生成纹理/特效/纹样**。

### 能力映射（按实用优先级）

| # | 技术 | 来源 | 漫画场景 | 实现方式 | 成本 |
|---|------|------|---------|---------|------|
| 1 | 冰裂/开片纹生成 | TOC Ch7 细胞自动机 | 窑变角色纹样、瓷器表面裂纹 | PIL像素级规则生成 | 零 |
| 2 | 粒子特效层 | TOC Ch4 粒子系统 | 窑火/烟尘/火花/光晕 | PIL绘制→叠加漫画格 | 零 |
| 3 | 传统纹样SVG库 | GD P.2 Shape | 缠枝莲/如意纹/云纹/回纹 | 数学公式→SVG矢量 | 零 |
| 4 | Perlin噪声纹理 | TOC Ch0+GD M.1 | 釉面流动感/自然云纹/纸底纹理 | Perlin噪声算法→PIL | 零 |
| 5 | 自动配色方案 | GD P.1 Color | 场景配色/角色服装色板 | 色环+噪声驱动 | 零 |
| 6 | 分形背景 | TOC Ch8 | 自然树/云/山背景装饰 | 递归算法→PIL | 零 |

### 何时用AI vs 何时用代码

| 需求 | 用AI(GPT Image 2) | 用代码(PIL/p5.js) |
|------|-------------------|-------------------|
| 角色形象/表情 | ✅ | ❌ 代码画脸太硬 |
| 场景构图/光影 | ✅ | ❌ |
| 重复性纹理（开片/冰裂） | ❌ 不可控 | ✅ 数学精确，无限变体 |
| 火/烟/粒子特效 | ❌ 每次不一样 | ✅ 参数可控 |
| 传统纹样 | ❌ AI不懂正确形制 | ✅ 算法保证正确 |
| 背景装饰元素 | ✅ 简单场景可 | ✅ 重复元素更高效 |

### 已有技术栈 vs 新补充

```
现有：GPT Image 2 → 角色+场景 + PIL → 气泡叠加
新增：PIL/p5.js → 纹理生成 + 粒子特效 + 纹样SVG → 叠加到AI生成的图上
```

### 关于TOC自主代理(Ch5/Ch10/Ch11)

遗传算法/神经网络/物理引擎对静态漫画无用，但若后续做**漫画动画化/视频化**(Seedance配合)，可再提取：
- Flow field → 多角色动态走位
- Matter.js → 物体碰撞/掉落动画
- Neuroevolution → 角色行为自动生成

## T1 v2.1 升级（2026-05-03）

基于小墨5条建议 + Taste-Skill 参数化思路的全量升级，30项测试全部通过。

### 新增模块

| 模块 | 文件 | 说明 |
|------|------|------|
| 风格参数化调控 | `style_params.py` | 3维独立控制(design_variance/visual_density/color_saturation) + 7种预设 |
| 天青浅品牌套件 | `brandkit_tianqing.py` | 配色/光线/构图/质感统一规范 + 4种模式 |
| 图→参逆向分析 | `image_analyzer.py` | 参考图分析→自动匹配T1参数 |

### 新增功能

| 功能 | 模块 | 说明 |
|------|------|------|
| 场景关键词权重匹配 | lighting_library | 替换简单字典匹配，多关键词加权投票 |
| 光线冲突检测 | lighting_library | 硬光+体积光等3组冲突对自动警告 |
| 陶瓷专属光线 | lighting_library | 青花透光/瓷质高光/釉面柔反 |
| 去AI自动级别 | realism_engine | 产品→L1/插画→L2/人像→L3 |
| 釉面质感参数 | preset_templates | 冰裂纹/开片/哑光釉/亮面釉/青花/窑变/兔毫/油滴 |
| 兼容模式 | prompt_enhancer | `compatibility_mode=True` 跳过所有新特性 |
| 效果预览 | prompt_enhancer | `return_meta=True` 返回配方信息 |
| 可扩展注册表 | lighting_library | `register_lighting()` 动态加光线 |
| 3维风格参数 | style_params | design_variance/visual_density/color_saturation 各1-10 |
| 天青浅品牌模式 | brandkit_tianqing | product/lifestyle/artistic/outdoor 4种场景 |
| 参考图分析 | image_analyzer | 上传竞品图→自动推荐T1参数 |

### 调用示例

```python
# 基础v2.1（享受全部升级）
enhance_prompt_local(scene="青花盖碗", return_meta=True)

# 风格参数化
enhance_prompt_local(scene="茶具", design_variance=8, visual_density=2, color_saturation=3)

# 品牌模式
enhance_prompt_local(scene="盖碗", brand_mode="product", return_meta=True)

# 图→参逆向
from image_analyzer import analyze_to_params
params = analyze_to_params(vision_analysis_text)
# → 直接传入 enhance_prompt_local(**params)
```
