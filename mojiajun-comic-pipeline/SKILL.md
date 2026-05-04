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

## 完整漫画流水线

```
Markdown脚本 → T3拆解 → T2注入 → T1 v2六层增强 → T4并行出图 → PIL气泡 → 完成
```

## 引擎路由

| 场景 | 引擎 |
|------|------|
| 产品图/角色一致性/中文文字 | GPT Image 2 |
| 古风艺术/氛围感 | Midjourney |
| 快速测试 | FLUX |

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
