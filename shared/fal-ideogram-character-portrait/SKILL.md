---
name: fal-ideogram-character-portrait
description: Use Fal.ai Ideogram Character API for face-consistent portrait generation across scenes — including CDN timing fixes, image size pitfalls, and prompt patterns
category: mojiajun
tags: [fal-ai, ideogram, character, portrait, face-consistency, api]
---

# Fal.ai Ideogram Character Portrait Generation

## Overview

Generate face-consistent portraits of a person across different scenes/outfits using Fal.ai's Ideogram Character API. This is the best available option before deploying GPU-based ComfyUI + IPAdapter.

## API Endpoint

```bash
POST https://fal.run/fal-ai/ideogram/character
Authorization: Key {KEY_ID}:{KEY_SECRET}
Content-Type: application/json
```

## Authentication

```python
headers = {
    "Authorization": f"Key 050d8ca7-3046-424e-805b-0e12dd024468:26f48e07e484631c2f611ea350656bb9",
    "Content-Type": "application/json"
}
```

## Request Payload

```json
{
  "prompt": "A slim handsome Chinese man around 28, fit, sharp facial features, warm smile...",
  "reference_image_urls": ["http://your-server/photo.jpg"],
  "style": "REALISTIC",
  "image_size": {"width": 1152, "height": 1536},
  "num_images": 1,
  "expand_prompt": false
}
```

## Image Size Pitfall

| Format | Result |
|--------|--------|
| `"portrait_4_3"` (string) | ❌ Black bands at bottom |
| `"square_hd"` (string) | ❌ Large black area (>50%) |
| `{"width": 1152, "height": 1536}` (object) | ✅ Clean output |
| `"landscape_16_9"` | ✅ Clean (can crop locally) |

**Always use custom object format** `{"width": X, "height": Y}`. Preset strings trigger a rendering bug.

Good dimensions for portrait: `{"width": 1152, "height": 1536}`
Good for square: `{"width": 1024, "height": 1024}`

## CDN Download Timing ⚠️ CRITICAL

The API **returns a URL immediately**, but the CDN hasn't finished rendering. 

```python
import time

# Submit job
resp = requests.post("https://fal.run/fal-ai/ideogram/character", headers=headers, json=payload)
img_url = resp.json()["images"][0]["url"]
file_size = resp.json()["images"][0]["file_size"]

# 🚨 DO NOT download immediately — wait for CDN
if file_size < 800000:  # Under 800KB = still rendering
    print(f"Image only {file_size} bytes, waiting for CDN...")
    time.sleep(60)

# Now download
img_resp = requests.get(img_url, timeout=120)
if len(img_resp.content) > 800000:
    print(f"✅ Complete: {len(img_resp.content)//1024}KB")
else:
    print(f"⚠️ Still small: {len(img_resp.content)//1024}KB")
```

**Rule of thumb:**
- Under 600KB → truncated, black bands
- 800KB-1.2MB → complete image

## Body Proportion Issue ⚠️ Ideogram's Known Bug

Ideogram Character API has a known issue with **over-stretching the body** — the generated person has:
- Neck too long
- Head too large compared to body
- Overall proportions feel "off"

### Mitigation Strategies

| Strategy | Effect | Verdict |
|----------|--------|---------|
| Add "natural proportions, normal neck length" to prompt | Marginal improvement | ⚠️ Helps slightly |
| Use `landscape_16_9` + crop locally to vertical | Best results, no black bars | ✅ **Best current fix** |
| Add "not elongated, well-proportioned" to prompt | Somewhat effective | ⚠️ Better than nothing |
| Try different image sizes | Mixed results, black bars risk | ⚠️ Risky |

### Recommended Workflow

```python
# Step 1: Generate in landscape to avoid proportion issues
"image_size": "landscape_16_9"  # Use string preset — it works for landscape!

# Step 2: Download full image (wait 60s)
time.sleep(60)
img_resp = requests.get(img_url, timeout=120)

# Step 3: Crop locally to vertical
from PIL import Image
img = Image.open(BytesIO(img_resp.content))
w, h = img.size
# Crop center vertical portion (roughly 9:16 aspect)
crop_w = int(h * 9/16)
left = (w - crop_w) // 2
cropped = img.crop((left, 0, left + crop_w, h))
cropped.save("final_portrait.png")
```

Proportions are still not perfect with this method, but better than portrait_4_3 which has black bars.

## Prompt Patterns

### For Younger/More Handsome Version
```python
prompt = f"A slim handsome Chinese man around 28, fit, sharp facial features, clear skin, warm smile, {scene_description}, same person as reference image, younger and more polished version, photorealistic 8K"
```

### For Natural Proportions (avoid long neck)
```python
prompt = "natural proportions, normal neck length, not elongated, well-proportioned body"
```

### For Full Body 
```python
prompt = "three-quarter body shot, environmental portrait, person in scene, not close-up"
```

### For Half-body/Portrait
```python
prompt = "head and shoulders portrait, face fills most of frame"
```

## Scene Templates (4 Scenes)

### Scene 1: City Professional
```python
"wearing a well-tailored navy blue suit with white shirt open collar, standing in a modern highrise office in Shenzhen, floor-to-ceiling windows with city skyline view, warm golden hour light streaming in"
```

### Scene 2: Beach Vacation
```python
"wearing a light beige linen shirt casually open, standing on a tropical beach at sunset, golden sunlight on face, gentle waves in background"
```

### Scene 3: Vintage Café
```python
"wearing a soft cream colored cashmere sweater, sitting by a window in a charming vintage cafe, wooden table with latte art coffee, warm afternoon sunlight"
```

### Scene 4: Workshop/Artisan
```python
"wearing a casual white linen shirt with sleeves rolled up, standing in a traditional pottery workshop, holding a ceramic vase, shelves of pottery behind, warm earthy tones"
```

## Complete Working Example

```python
import requests, time, json

KEY = "050d8ca7-3046-424e-805b-0e12dd024468:26f48e07e484631c2f611ea350656bb9"
FAL_URL = "https://fal.run/fal-ai/ideogram/character"
REF_IMAGE = "http://your-server:8888/me.jpg"

payload = {
    "prompt": "A slim handsome Chinese man around 28, fit, sharp facial features, clear skin, warm smile, wearing a light beige linen shirt, standing on a tropical beach at sunset, golden light on face, photorealistic 8K",
    "reference_image_urls": [REF_IMAGE],
    "style": "REALISTIC",
    "image_size": {"width": 1152, "height": 1536},
    "num_images": 1,
    "expand_prompt": False
}

resp = requests.post(FAL_URL, 
    headers={"Authorization": f"Key {KEY}", "Content-Type": "application/json"},
    json=payload, timeout=60
)

img_url = resp.json()["images"][0]["url"]
file_size = resp.json()["images"][0]["file_size"]
print(f"URL: {img_url}")
print(f"Size: {file_size} bytes")

if file_size < 800000:
    print("Waiting 60s for CDN...")
    time.sleep(60)

img_resp = requests.get(img_url, timeout=120)
print(f"Downloaded: {len(img_resp.content)//1024}KB")
```

## When to Use vs Alternatives

| Tool | Face Match | Speed | Cost | Best For |
|------|-----------|-------|------|----------|
| **Fal Ideogram Character** | ✅ Best | ~18s + 60s CDN | $0.01-0.02 | **Default choice for portraits** |
| GPT Image 2 (Crun) | ⚠️ Moderate | 3-6min queue | $0.02 | When you have time |
| MJ cref (TT API) | ❌ Poor for real faces | 45-60s | $0.02-0.05 | Art style only |
| ComfyUI + IPAdapter (GPU) | ✅✅ Ultimate | - | GPU cost | Future upgrade path |

## Usage in 墨家军

```python
# Direct Python call
from agent_outputs.moyuan.api_toolkit.fal_api import FalClient
c = FalClient()
result = c.generate("prompt", model="flux-schnell")

# Via task queue (task_type: gen_image_flux)
# payload.args.prompt and payload.args.model
```

Note: Ideogram Character endpoint is separate from FLUX. The `FalClient` class currently handles FLUX models only. For Ideogram Character, use curl or direct requests as shown above.
