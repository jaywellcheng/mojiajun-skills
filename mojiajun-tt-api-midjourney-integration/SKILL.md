---
name: mojiajun-tt-api-midjourney-integration
description: Integrate TT API Midjourney into the 墨家军 multi-agent system. Focuses on the specific module_dispatcher payload handling issue, jobId nesting, polling/download logic, and image_generator transformation.
---

# TT API Midjourney Integration for 墨家军

## Architecture

```
task_queue (image_generator task)
    ↓
module_dispatcher.py  → payload.get("args", {}) → **kwargs
    ↓
agent_outputs/moqing/image_generator.py → tt_api.py
    ↓
TT API: POST /imagine → GET /fetch?jobId=xxx → download images
```

## Critical Discoveries

### 1. module_dispatcher.py passes `payload.get("args", {})`

Line 99: `func_args = payload.get("args", {}) if isinstance(payload, dict) else {}`

This means the task_queue payload MUST have an `"args"` wrapper. Without it, the module function gets called with `**{}` (empty dict), resulting in all parameters being None/default.

**Correct payload format for task_queue:**
```json
{
  "task": "description",
  "args": {
    "image_descriptions": [
      {"title": "...", "description": "...", "type": "产品", "aspect_ratio": "竖版"}
    ]
  }
}
```

### 2. TT API /imagine returns jobId nested in data

```json
{"status": "SUCCESS", "data": {"jobId": "uuid"}}
```

NOT at the top level. Must extract as:
```python
job_id = result.get("data", {}).get("jobId") or result.get("jobId")
```

### 3. Old image_generator was prompt-only

Original module only generated MJ prompt text and marked completed. No actual API calls. Transformation needed:

- Old: `generate prompt text → return → completed (no image)`
- New: `generate prompt → POST /imagine → poll /fetch → download → return image paths`

### 4. MJ generation timing

- Typical: 45-60 seconds
- Poll interval: 5 seconds
- Max wait: 180 seconds (3 min timeout)
- Image URLs may expire → download immediately on fetch completion

## Files

| File | Purpose |
|------|---------|
| `agent_outputs/moyuan/api_toolkit/base_client.py` | Base HTTP client with retry/poll |
| `agent_outputs/moyuan/api_toolkit/tt_api.py` | TT API Midjourney client |
| `agent_outputs/moqing/image_generator.py` | Modified to call TT API |
| `agent_outputs/moqing/generated/` | Downloaded images output dir |
| `module_dispatcher.py` | Dispatcher (line 99 payload handling) |

## Payload Compatibility

The `generate()` function in `image_generator.py` handles multiple payload formats:
```python
def generate(image_descriptions=None, style=None, mode="fast", **kwargs):
    if not image_descriptions and kwargs:
        # Check kwargs root, kwargs.args, or single-image format
        image_descriptions = (kwargs.get("image_descriptions") or 
                             kwargs.get("args", {}).get("image_descriptions"))
```

## Key Management

TT API key is in SECRET.md. Not in .env. Consider moving to .env for security.

## TT API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/midjourney/v1/imagine` | POST | Create MJ task |
| `/midjourney/v1/fetch` | GET | Get result by jobId |

## Image Output

Generated images are saved to `agent_outputs/moqing/generated/` with filename format:
- `{jobId[:8]}_combined_{timestamp}.png` — 4-in-1 grid preview (6-8MB)
- `{jobId[:8]}_variant_{1-4}_{timestamp}.png` — Individual variants (2-3MB each)

## Fal.ai FLUX Specifics

| Item | Value |
|------|-------|
| API Base | `https://fal.run/{model_endpoint}` |
| Auth Header | `Authorization: Key {key_id}:{key_secret}` |
| Auth Format | NOT Basic Auth (key_id:secret as user:pass). Use `{\"Authorization\": f\"Key {FAL_KEY}\"}` header |
| Model | `fal-ai/flux/schnell` (fast, $0.003, 0.15s inference) |
| Image Size | `square_hd` (1024x1024), `portrait_4_3` (864x1152), `landscape_4_3` (1152x864) |
| CDN Download | Can be VERY slow from China (up to 110s for a 240KB file). Set download timeout to 180s. |
| SSL | Fal.ai CDN server certificate may cause SSL verification failures from China. Use `verify=False` and `urllib3.disable_warnings()`. |
| Response | `{\"images\": [{\"url\": \"...\", \"width\": 1024, \"height\": 1024}], \"seed\": N}` |

**Critical: Use `requests.Session()` with `session.verify = False`** to avoid SSL issues on both API call and image download.

## SiliconFlow (国内站) Specifics

| Item | Value |
|------|-------|
| API Base | `https://api.siliconflow.cn/v1/images/generations` |
| Auth Header | `Authorization: Bearer {key}` |
| Verified Working | `Kwai-Kolors/Kolors` only |
| NOT Working | `black-forest-labs/FLUX.1-*`, `stabilityai/*` → "Model disabled" |
| Model Availability | FLUX/SD models have been **removed** from 国内站. Use Fal.ai for FLUX instead. |
| 50元余额 | Can be used for Kolors or LLM models (DeepSeek/Qwen) |

## GPT Image 2 via Crun.AI - Human Portrait Generation

### Key Discovery: Image-to-Image for Face Consistency

GPT Image 2 (via Crun.AI, model `openai/gpt-image-2`) supports character-consistent generation by passing a reference image as base64 in the `image` field:

```python
import base64
with open("portrait.jpg", "rb") as f:
    b64 = base64.b64encode(f.read()).decode()

payload = {
    "model": "openai/gpt-image-2",
    "input": {
        "prompt": "A handsome young Chinese man in his early 30s, wearing a suit... same person as reference image, younger and more handsome version",
        "image": b64,  # Reference image as base64
        "aspect_ratio": "3:4",
        "num_outputs": 1,
    }
}
```

**Results**: GPT Image 2 handles face consistency reasonably well but the "same person" instruction is prompt-dependent. For better consistency with the actual person, also include detailed facial features in the prompt.

### Alternative: Midjourney `--cref` (Character Reference)

MJ's `--cref` parameter provides dedicated character reference:
```bash
curl -X POST "https://api.ttapi.io/midjourney/v1/imagine" \
  -H "TT-API-KEY: xxx" \
  -d '{"prompt": "... --cref http://public-url/photo.jpg --cw 80 --v 6", "mode": "fast"}'
```

Requirements:
1. Reference image must be at a **publicly accessible URL** (MJ fetches it, not local file)
2. Can serve from CORE-01 on port 8888 (`python3 -m http.server 8888 --directory /tmp`)
3. `--cw` controls how strongly the character is matched (0-100)
4. Typical generation: 45-60 seconds

### GPT Image 2 vs MJ cref Comparison

| Aspect | GPT Image 2 | MJ `--cref` |
|--------|------------|-------------|
| Face Consistency | Good (prompt-dependent) | Better (designed for this) |
| Generation Time | 3-5 min (Crun queue) | 45-60s (fast mode) |
| Cost | $0.02/img (4 credits) | $0.02-0.05/img |
| Image Quality | More realistic/physically accurate | More artistic/stylized |
| Suitability for Portraits | Very good for photorealistic | Better for artistic/stylized |

## Third Phase: Unified API Scheduling Layer (v3)

After individual API modules were built, a third phase unified them:

### Architecture

```
task_queue → module_dispatcher → agent_outputs/moqing/api_entry.py
    ↓
agent_outputs/moyuan/api_toolkit/__init__.py (unified exports + engine registry)
    ↓
Individual API modules (tt_api.py, fal_api.py, crun_api.py, ...)
```

### Key Decisions

1. **api_entry.py in moqing/**: Since dispatcher resolves module paths via `AGENT_OUTPUTS / agent / (module_name + ".py")`, wrapper files must live in the correct agent's output directory. For moqing-dispatched tasks, `api_entry.py` goes in `agent_outputs/moqing/`.

2. **api_toolkit in moyuan/**: All actual API client code lives under `agent_outputs/moyuan/api_toolkit/` for clean separation of concerns. The moqing-level api_entry.py imports from here.

3. **All functions use `**kwargs`**: To handle the dispatcher's `payload.get("args", {})` → `func(**args)` calling convention, all entry functions must accept `**kwargs` and extract `prompt` and other params from it, never relying on positional arguments.

4. **Unified `generate(**kwargs)` with `engine` param**: A single entry point with `engine="mj|flux|crun|kolors"` lets tasks specify which API to use without changing task_type.

### Critical: _extract_prompt pattern

```python
def _extract_prompt(**kwargs):
    """Handle all possible param formats from dispatcher"""
    prompt = kwargs.get("prompt", "")
    if not prompt:
        args = kwargs.get("args", {})
        if args:
            prompt = args.get("prompt", "")
    if not prompt:
        descs = kwargs.get("image_descriptions", [])
        if descs and len(descs) > 0:
            prompt = descs[0].get("description", "")
    return prompt
```

This handles: direct kwargs, nested `args` dict (dispatcher format), and `image_descriptions` array (old image_generator format).

### Dispatcher Registration (v2 API entries)

```python
TASK_MODULE_MAP = {
    "gen_image":           ("moqing", "api_entry", "generate"),
    "gen_image_mj":        ("moqing", "api_entry", "generate_mj"),
    "gen_image_flux":      ("moqing", "api_entry", "generate_flux"),
    "gen_image_crun":      ("moqing", "api_entry", "generate_crun"),
    "gen_image_kolors":    ("moqing", "api_entry", "generate_kolors"),
    "gen_video":           ("moqing", "api_entry", "generate_video"),
}
```

Note: Each entry presets `engine` so tasks don't need to specify it.

## Complete api_toolkit Architecture (final)

```
agent_outputs/moyuan/api_toolkit/
├── __init__.py           # Unified exports, engine registry, generate_image()
├── base_client.py        # Base HTTP client (retry, poll, timeout)
├── tt_api.py             # TT API Midjourney ($0.02-0.05/img, 45-60s)
├── fal_api.py            # Fal.ai FLUX ($0.003-0.025/img, 0.15s!) -- fastest/cheapest
├── crun_api.py           # Crun.AI 100+ models (1000 credits prepaid, 15-30s)
├── siliconflow_api.py    # SiliconFlow Kolors (50元 prepaid)
├── photoroom_api.py      # Photoroom smart cutout ($0.02/img)
├── kling_api.py          # Kling AI video (JWT auth, needs API activation)
├── minimax_api.py        # MiniMax TTS (needs Group ID)
└── fal_api.py            # Fal.ai FLUX

agent_outputs/moqing/
├── api_entry.py          # Unified dispatcher entry point
├── image_generator.py    # Original (patched, still works)
└── generated/            # All downloaded images
    ├── fal/
    ├── crun/
    ├── siliconflow/
    ├── kling/
    ├── photoroom/
    └── minimax/
```

Each module follows the same pattern:
1. `create_task()` → returns task_id
2. `wait_for_result(task_id)` → polls until done
3. Downloads media → saves to `generated/{provider}/`
4. Returns structured result with filepaths

## Four-Phase Project Evolution

### Phase 1: TT API (MJ) — Make Moqing Actually Generate Images
**Problem**: `image_generator.py` only generated MJ prompt text, never called any API.

**Fix**: Replaced prompt-only generation with actual TT API calls (`POST /imagine` + `GET /fetch` + download).

### Phase 2: Multi-API Toolkit (6 modules)
Integrated Crun.AI, Fal.ai FLUX, SiliconFlow, Photoroom, Kling AI, MiniMax into a unified `/api_toolkit/` directory under `agent_outputs/moyuan/`.

**Key integration issue**: Each API has completely different auth, polling, and response format.

### Phase 3: Unified Dispatcher Layer
Built `api_entry.py` in `agent_outputs/moqing/` and registered new task_types like `gen_image_flux`, `gen_image_crun`, etc. in `module_dispatcher.py`.

### Phase 4: Smart Pipeline + Asset Management
Built in this session:
- Smart engine selector (auto-chooses mj/flux/crun/gpt2 based on prompt keywords)
- Content pipeline orchestrator (note creation → image gen → archive)
- Cost monitor ($0.64 total for 22 images today)
- Fallback engine chain (gpt2→flux→gemini on failure)
- Cover maker (PIL-based image+text compositor)
- Media search (by keyword/category/engine/date)
- Media asset DB (`media_assets`, `media_tags`, `media_collections` — 5 tables)

## Human Portrait Generation with Face Consistency — CRITICAL LEARNINGS

This was the hardest problem: generating a specific person in different scenes while keeping their face consistent, WITHOUT GPU-based ComfyUI+IPAdapter.

### Attempt 1: GPT Image 2 Image-to-Image (via Crun.AI)
**Method**: Pass reference photo as base64 in `image` field + prompt "same person as reference image"
**Result**: Face NOT consistent enough. The model recognized "a person" but didn't preserve the specific individual's features.

### Attempt 2: Midjourney `--cref` (Character Reference, via TT API)
**Method**: `prompt: "... --cref http://public-url/photo.jpg --cw 80 --v 6"`
**Requirements**: Reference image MUST be at a public URL (MJ fetches it). Use CORE-01:8888 to serve temp files.
**Result**: Face was completely wrong. "完全不象我".

### Attempt 3 (Working): Fal.ai Ideogram Character API
**Method**: `POST https://fal.run/fal-ai/ideogram/character` with `reference_image_urls: ["http://..."]`
**Auth**: Same Fal.ai Key (`Authorization: Key {id}:{secret}`)
**Output**: `{"images": [{"url": "..."}], "seed": N}`
**Result**: 18 seconds, 620KB output. Face consistency was significantly better than both GPT-2 and MJ approaches — THE WINNING APPROACH for GPU-free face-consistent generation.
**Cost**: Fal.ai pay-per-use ($0.003-0.025/image)

### Key Lesson: For face-consistent portraits without GPU
1. ❌ GPT Image 2 (Crun) — not consistent enough  
2. ❌ MJ `--cref` (TT API) — completely wrong  
3. ✅ **Fal.ai Ideogram Character** — best result among no-GPU options

The fundamental limitation: without IPAdapter/FaceID on local GPU, no API currently delivers production-grade face consistency for arbitrary portraits.

### Media Asset Management (Phase 4 addition)
After getting images generated, they need structured storage:

**Tables created:**
```sql
media_assets       — master image table (filepath, size, dims, category, engine, prompt)
media_tags         — tag taxonomy (scene/style/character/object)
media_asset_tags   — many-to-many association
media_collections  — grouped sets (e.g., "一篇小红书笔记的全部配图")
media_collection_assets — collection membership with sort order
```

**Archive tool**: `/tmp/archive_media.py` scans all API output dirs, classifies images by filename/engine, and inserts into `media_assets`.

**Search tool**: `media_search.py` supports keyword, category, engine, and date-range filtering.

**Current stats (as of 2026-04-26)**: 23 assets, 57.3MB total, $0.64 total cost across all APIs.

### Cost Monitoring

```python
# Cost-per-image estimates (from actual usage):
COST_PER_IMAGE = {
    "crun": 0.02,        # GPT Image 2: 4 credits = $0.02
    "tt_api": 0.035,     # Midjourney via TT API
    "fal": 0.003,        # FLUX schnell via Fal.ai
    "siliconflow": 0.01, # Kolors via SiliconFlow
    "photoroom": 0.02,   # Background removal
}
```

### Cover Maker (PIL-based)
`cover_maker.py` composites images + title text for Xiaohongshu covers:
1. Crops to 3:4 portrait
2. Resizes to 1080x1440
3. Adds semi-transparent bottom bar
4. Renders title (multi-line support with `|` separator) + subtitle
5. Auto-archives to `media_assets` with category='cover'
6. Font search: STHeiti → wqy-microhei → NotoSansCJK → fc-list fallback

### Content Pipeline Orchestrator
`content_pipeline.py` creates a full note production flow:
1. Creates draft in `notes_published` table
2. For each image description, smart-selects engine via `suggest_engine()`
3. Dispatches tasks to `task_queue` with proper `args` wrapper
4. Supports status checking via `check_pipeline_status(note_id)`

### Fallback Engine Chain
`fallback_engine.py` provides automatic failover:
```python
ENGINE_CHAIN = {
    "gpt2": ["flux", "gemini"],    # GPT2 fails → FLUX → Gemini
    "flux": ["gemini", "gpt2"],    # FLUX fails → Gemini → GPT2
    "mj": ["gpt2", "flux"],        # MJ fails → GPT2 → FLUX
}
ENGINE_TIMEOUT = {"gpt2": 600, "flux": 200, "mj": 180, "gemini": 60}
```

## SiliconFlow Specifics

| Item | Value |
|------|-------|
| API Base | `https://api.siliconflow.cn/v1/images/generations` |
| Auth Header | `Authorization: Bearer {key}` |
| Method | POST with JSON body |
| Model Names | `Kwai-Kolors/Kolors` (verified working), `black-forest-labs/FLUX.1-dev` (needs account activation) |
| Image Size | `1024x1024`, `1440x1440`, etc. |
| Output | Returns URL or b64_json |
| Note | Image URLs expire in 1 hour → download immediately |

## Key Lessons from Real-World Integration

### 1. Execute Python on remote servers via file transport
The execute_code sandbox has severe quoting/escaping issues with multi-line embedded Python. Always use:
```
write_file(local_path, content) → cat local_path | ssh "cat > remote_path" → ssh "timeout N python3 remote_path"
```

### 2. Always test API endpoints with curl first
Before writing Python code, verify the raw API call works:
```bash
curl -X POST "https://api.ttapi.io/midjourney/v1/imagine" \
  -H "TT-API-KEY: xxx" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"test --ar 1:1 --v 6", "mode":"fast"}'
```

### 3. API response nesting is unpredictable
TT API returns `{"data": {"jobId": "xxx"}}` not `{"jobId": "xxx"}`. Always check multiple nesting levels.

### 4. Module_dispatcher payload format is strict
`payload.get("args", {})` means all params must be wrapped in `"args": {...}`. Agent-facing payload without `args` wrapper will pass empty dict to module function.

### 5. Python import paths on CORE-01
All agent modules under `agent_outputs/` require `sys.path.insert(0, '/home/ubuntu/mojiajun-queue')` before importing when run outside the worker context.

### 6. Fal.ai Ideogram Character CDN timing
The Ideogram Character API returns a URL immediately but the CDN image renders **asynchronously**. Downloading within 30s yields ~300KB truncated images with black bands. Wait 60s+ — the file should be 800KB-1.2MB for a complete 864x1152 image. Check `file_size` in the response as a heuristic: <800KB = still rendering.

### 7. SCP is more reliable than SSH pipe for large files
`ssh ... cat file > local_path` truncates images mid-transfer. Use `scp user@host:remote local` or download to server first then copy locally. For HTTP serving, ensure `python3 -m http.server --directory` points to the correct directory — it won't follow symlinks or serve parent directories.

### 8. Ideogram image_size must be object, not string
Use `{"width": 1152, "height": 1536}` not `"portrait_4_3"`. Preset strings produce black band artifacts. Only `"landscape_16_9"` works reliably as a preset string.

## Crun.AI Specifics

| Item | Value |
|------|-------|
| API Base | `https://api.crun.ai/api/v1/client` |
| Auth Header | `X-API-KEY: {key}` |
| Create Task | `POST /job/CreateTask` |
| Poll Status | `GET /job/TaskInfo?task_id=xxx` |
| Check Balance | `POST /account/balance` |
| Model Names | Format: `google/veo3-1-t2v`, `google/nano-banana` |
| Typical Generation | Image: 15-30s, Video: 2-10min |
| Poll Interval | Image: 15s, Video: 30s |
| Max Wait | Image: 180s, Video: 600s |

### Crun.AI Model Aliases

```python
MODEL_MAP = {
    "gemini": "google/nano-banana",
    "nano-banana-pro": "google/nano-banana-pro",
    "flux": "black-forest-labs/flux-2",
    "qwen-image": "qwen/qwen-imagen",
    "gpt-image": "openai/gpt-image-1.5",
    "grok": "xai/grok-imagine",
    "veo": "google/veo3-1-t2v",
    "sora": "openai/sora2-pro",
    "wan": "alibaba/wan-2.6",
    "seedance": "bytedance/seedance-1.5-pro",
    "vidu": "vidu/vidu-q3-pro",
}
```
