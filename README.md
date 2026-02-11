# FRANZ — Narrative-Driven Autonomous Desktop Agent

> A stateless, vision-language-model-powered computer-use agent that maintains coherent
> long-running autonomy through an evolving narrative memory — not conversation history.

---

## System Overview

FRANZ is an autonomous desktop automation agent that operates in a continuous
perception–reasoning–action loop against a **stateless** VLM API endpoint. Rather than
accumulating an ever-growing conversation history (which is both token-expensive and
context-window-limited), FRANZ maintains a **compressed narrative story** that is
**replaced in full** on every iteration. The story functions as an adaptive episodic
memory: it summarises what has happened, what the current state is, and what remains
to be done — all in natural language, all within a fixed token budget.

This architecture has a critical property: **the agent can run indefinitely**. Because
the narrative is regenerated each cycle rather than appended, context never overflows.
The VLM receives a fresh screenshot, the current story, and the last action taken — a
complete situational snapshot — and produces exactly one next action plus an updated
narrative. The loop is therefore **temporally unbounded**.

### Key Architectural Innovations

| Concept | Description |
|---|---|
| **Narrative Memory** | A natural-language story replaces traditional chat history. It is rewritten each iteration, compressing past context into a fixed-size representation that the VLM can both read and write. |
| **Stateless Inference** | Every API call is self-contained: system prompt + user prompt (with story and last action) + screenshot. No session state is maintained server-side. |
| **Perceptual Grounding** | Every decision is grounded in a current screenshot, not stale state. The agent re-perceives the world before every action. |
| **Single-Step Commitment** | The agent commits to exactly one action per cycle, then re-observes. This prevents compounding errors from multi-step open-loop plans. |
| **Human-Mimetic Execution** | Actions are executed with smooth cursor trajectories (smoothstep interpolation), realistic typing cadence, and natural inter-action delays — making the agent's behaviour compatible with applications that expect human-speed input. |
| **Visual Action Feedback** | The last executed action is rendered as an overlay annotation (crosshairs, arrows, circles) on the screenshot sent to the VLM, providing the model with explicit visual evidence of what was just done. |

### Future Extension: Self-Modifying Goal Specification

The current implementation uses a fixed user request template. A planned extension will
allow the VLM itself to **rewrite the goal specification** as part of its output —
transforming FRANZ from a task-completion agent into a **persistent autonomous desktop
assistant** with no terminal state. The narrative memory architecture already supports
this: since the story is the sole carrier of inter-iteration state, expanding it to
include dynamically revised objectives requires no structural changes to the loop.

---

## Workflow

```
┌─────────────────────────────────────────────────────────────────────┐
│                        FRANZ MAIN LOOP                              │
│                                                                     │
│  ┌───────────┐    ┌──────────────┐    ┌──────────────────────────┐  │
│  │  CAPTURE   │───▶│  ANNOTATE    │───▶│  ENCODE PNG              │  │
│  │ screenshot │    │ last action  │    │  (screenshot.py)         │  │
│  │  (GDI)     │    │ overlay      │    │                          │  │
│  │            │    │ (drawing.py) │    │                          │  │
│  └───────────┘    └──────────────┘    └────────────┬─────────────┘  │
│                                                     │                │
│                                                     ▼                │
│                                       ┌──────────────────────────┐  │
│                                       │  COMPOSE API REQUEST     │  │
│                                       │                          │  │
│                                       │  ┌────────────────────┐  │  │
│                                       │  │ system prompt      │  │  │
│                                       │  ├────────────────────┤  │  │
│                                       │  │ user prompt with:  │  │  │
│                                       │  │  • goal template   │  │  │
│                                       │  │  • full story      │  │  │
│                                       │  │  • last action     │  │  │
│                                       │  │  • base64 PNG      │  │  │
│                                       │  └────────────────────┘  │  │
│                                       └────────────┬─────────────┘  │
│                                                     │                │
│                                                     ▼                │
│                                       ┌──────────────────────────┐  │
│                                       │  VLM INFERENCE           │  │
│                                       │  (stateless endpoint)    │  │
│                                       │                          │  │
│                                       │  POST /v1/chat/          │  │
│                                       │       completions        │  │
│                                       └────────────┬─────────────┘  │
│                                                     │                │
│                                                     ▼                │
│                                       ┌──────────────────────────┐  │
│                                       │  PARSE RESPONSE          │  │
│                                       │                          │  │
│                                       │  Extract:                │  │
│                                       │  • function call(s)      │  │
│                                       │  • narrative story       │  │
│                                       └────────────┬─────────────┘  │
│                                                     │                │
│                                          ┌──────────┴──────────┐     │
│                                          ▼                     ▼     │
│                              ┌─────────────────┐  ┌───────────────┐ │
│                              │ EXECUTE ACTION   │  │ UPDATE STORY  │ │
│                              │                  │  │               │ │
│                              │ • smooth move    │  │ story ← new   │ │
│                              │ • click/type/    │  │ narrative     │ │
│                              │   drag           │  │ (full replace)│ │
│                              │ • human timing   │  │               │ │
│                              └────────┬─────────┘  └───────┬───────┘ │
│                                       │                    │         │
│                                       └────────┬───────────┘         │
│                                                │                     │
│                                                ▼                     │
│                                       ┌────────────────┐             │
│                                       │ LOOP BACK TO   │             │
│                                       │ CAPTURE        │─────────┐   │
│                                       └────────────────┘         │   │
│                                                                  │   │
│  ◄───────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Data Flow per Iteration

```
  story(n-1)  +  last_action(n-1)  +  screenshot(n)
                        │
                        ▼
                   ┌─────────┐
                   │   VLM   │
                   └────┬────┘
                        │
                ┌───────┴───────┐
                ▼               ▼
          action(n)        story(n)
                │               │
                ▼               │
         execute on OS          │
                │               │
                └───────┬───────┘
                        ▼
                  next iteration
```

### Memory Model

```
  Traditional Agent          FRANZ
  ─────────────────          ─────

  msg[0]  system             system prompt     (fixed)
  msg[1]  user + img₁        user prompt       (fixed template)
  msg[2]  assistant₁           + story(n)      (replaced each cycle)
  msg[3]  user + img₂          + last_action   (replaced each cycle)
  msg[4]  assistant₂           + screenshot(n) (replaced each cycle)
  msg[5]  user + img₃
  ...     (grows forever)    ← CONSTANT SIZE →
  msg[2n]  ← context overflow
```

---

## File Reference

### `main.py` — Agent Core

The orchestration module implementing the perception–reasoning–action loop.

#### Constants & Configuration

| Constant | Type | Description |
|---|---|---|
| `API` | `str` | VLM inference endpoint URL |
| `MODEL` | `str` | Model identifier for the API |
| `TARGET_WIDTH` | `int` | Screenshot width sent to VLM (pixels) |
| `TARGET_HEIGHT` | `int` | Screenshot height sent to VLM (pixels) |
| `SAMPLING` | `dict` | Inference sampling parameters (`temperature`, `top_p`, `max_tokens`) |
| `ENABLE_VISUAL_FEEDBACK` | `bool` | Toggle action-overlay annotations on screenshots |
| `MOVEMENT_STEPS` | `int` | Number of interpolation steps for cursor movement |
| `STEP_DELAY` | `float` | Delay between movement steps (seconds) |
| `CLICK_SETTLE_DELAY` | `float` | Pause after cursor arrives before clicking (seconds) |
| `TYPING_CHAR_DELAY` | `float` | Delay between individual keystrokes (seconds) |
| `TYPING_WORD_DELAY` | `float` | Delay after space/newline (simulates thinking, seconds) |
| `SYSTEM_PROMPT` | `str` | VLM system prompt defining the agent's role and output format |
| `USER_PROMPT_TEMPLATE` | `str` | Template with `{story}` and `{last}` placeholders |

#### Functions

| Function | Signature | Description |
|---|---|---|
| `infer` | `(png_data: bytes, story: str, last: str) -> str` | Sends a single stateless inference request containing the system prompt, formatted user prompt (with story and last action), and base64-encoded screenshot. Returns the raw VLM response text. |
| `parse_response` | `(content: str) -> tuple[list[tuple[str, list]], str]` | Extracts function calls (e.g. `left_click(500,300)`) and narrative text from the VLM response. Returns a list of `(function_name, parameters)` tuples and the story string. |
| `_parse_args` | `(func_name: str, raw_args: str) -> list \| None` | Parses raw argument strings into typed parameter lists. Handles numeric args for spatial commands and string args for `type()`. |
| `create_visualization` | `(last_action: str) -> Callable` | Returns a drawing callback that overlays action annotations (crosshairs, arrows, circles) onto RGBA image data based on the last executed command. |
| `execute_action` | `(func_name: str, params: list) -> None` | Executes a parsed action on the OS with human-mimetic timing: smooth cursor movement (smoothstep interpolation), settle delays, realistic click/type cadence. |
| `_format_command` | `(func_name: str, params: list) -> str` | Reconstructs a function-call string from parsed components for logging and `last_action` tracking. |
| `get_cursor_position` | `() -> tuple[int, int]` | Returns current cursor position via Win32 API. |
| `smooth_move_to` | `(target_x: int, target_y: int, steps: int, delay: float) -> None` | Moves cursor from current position to target using smoothstep interpolation. |
| `press_key` | `(vk_code: int) -> None` | Presses and releases a single virtual key. |
| `type_text` | `(text: str) -> None` | Types a string character-by-character with human-like timing, handling shift states and special characters via `VkKeyScanW`. |
| `main` | `() -> None` | Entry point. Initialises dump directory, runs the infinite perception–action loop. |

#### Supported VLM Output Commands

| Command | Format | Coordinates | Description |
|---|---|---|---|
| `left_click` | `left_click(x, y)` | 0–1000 normalised | Single left mouse click |
| `right_click` | `right_click(x, y)` | 0–1000 normalised | Single right mouse click |
| `double_left_click` | `double_left_click(x, y)` | 0–1000 normalised | Double left mouse click |
| `drag` | `drag(x1, y1, x2, y2)` | 0–1000 normalised | Click-drag from start to end |
| `type` | `type("text")` | N/A | Keystroke input |

#### Internal Regex

| Pattern | Variable | Purpose |
|---|---|---|
| `\b(left_click\|right_click\|double_left_click\|drag\|type)\s*\(([^)]*)\)` | `_FUNC_CALL_RE` | Matches all supported function-call formats in VLM output |

---

### `screenshot.py` — Screen Capture & Encoding

A self-contained Windows screen capture module using GDI with DPI awareness. Can be
used as both an importable module and a standalone CLI tool.

#### CLI Usage

```
python screenshot.py                       # Full screen → screenshot.png
python screenshot.py capture.png           # Full screen → capture.png
python screenshot.py out.png 1920 1080     # Capture and resize → out.png
```

#### Classes

| Class | Description |
|---|---|
| `BITMAPINFOHEADER` | ctypes Structure mapping the Win32 `BITMAPINFOHEADER` struct. |
| `BITMAPINFO` | ctypes Structure mapping the Win32 `BITMAPINFO` struct (header + color table). |
| `Win32Context` | Frozen dataclass wrapping `user32`, `gdi32`, and `shcore` DLL handles. Sets process DPI awareness on creation. |

#### Functions

| Function | Signature | Description |
|---|---|---|
| `get_screen_size` | `() -> tuple[int, int]` | Returns `(width, height)` of the primary display in physical pixels (DPI-aware). |
| `capture` | `(sw: int, sh: int) -> bytes` | Captures the entire screen as raw BGRA pixel data using GDI `BitBlt` with `CAPTUREBLT` flag (includes layered windows). Returns `sw × sh × 4` bytes. All GDI resources are properly released. |
| `downsample` | `(src: bytes, sw: int, sh: int, dw: int, dh: int) -> bytes` | Resizes BGRA bitmap from `(sw, sh)` to `(dw, dh)` using GDI `StretchBlt` with `HALFTONE` stretch mode for high-quality downsampling. Fixes alpha channel to 255 (opaque). |
| `bgra_to_rgba` | `(bgra: bytes) -> bytes` | Swizzles BGRA channel order to RGBA. Sets alpha to 255 for all pixels. |
| `encode_png` | `(rgba: bytes, sw: int, sh: int) -> bytes` | Manual PNG encoder. Produces a valid PNG file (signature + IHDR + IDAT + IEND) from raw RGBA data using zlib compression level 6. No external image library required. |
| `capture_screen_png` | `(target_width: int \| None, target_height: int \| None, draw_func: Callable \| None) -> bytes` | **Primary API.** Captures screen, optionally downsamples to target resolution, converts BGRA→RGBA, applies optional annotation callback, and returns PNG bytes. |
| `main` | `() -> None` | CLI entry point for standalone screenshot capture. |

#### Module-Level State

| Variable | Description |
|---|---|
| `_ctx` | Singleton `Win32Context` instance, created at import time. Sets `PROCESS_PER_MONITOR_DPI_AWARE` once. |

#### Callback Protocol for `draw_func`

```
def draw_func(rgba: bytes, width: int, height: int) -> bytes:
    """
    Receives RGBA pixel data and image dimensions.
    Returns modified RGBA pixel data (same length).
    Called after BGRA→RGBA conversion and before PNG encoding.
    """
```

---

### `drawing.py` — Pixel-Level Annotation Primitives

Pure-Python drawing utilities operating directly on RGBA byte buffers. No external
dependencies. All functions are non-mutating (they create a `bytearray` copy internally
and return new `bytes`).

#### Color Constants

| Constant | Value (R, G, B, A) | Usage |
|---|---|---|
| `RED` | `(255, 0, 0, 255)` | Left click / double click crosshair |
| `GREEN` | `(0, 255, 0, 255)` | Click target circle, drag endpoint |
| `BLUE` | `(0, 150, 255, 255)` | Right click crosshair, drag arrow |
| `YELLOW` | `(255, 255, 0, 255)` | Right click circle, drag startpoint |
| `WHITE` | `(255, 255, 255, 255)` | Available for custom annotations |
| `BLACK` | `(0, 0, 0, 255)` | Available for custom annotations |

#### Functions

| Function | Signature | Description |
|---|---|---|
| `draw_crosshair` | `(rgba, width, height, x, y, size=20, color=RED, thickness=2) -> bytes` | Draws a crosshair (horizontal + vertical lines with center dot) at `(x, y)`. Used to mark click targets. |
| `draw_circle` | `(rgba, width, height, x, y, radius, color=GREEN, filled=False) -> bytes` | Draws a filled or hollow circle. Hollow circles use a 2px ring. Used for click target highlights and drag endpoints. |
| `draw_line` | `(rgba, width, height, x1, y1, x2, y2, color=BLUE, thickness=3) -> bytes` | Draws a line between two points using Bresenham's algorithm with configurable thickness. Foundation for `draw_arrow` and `draw_rectangle`. |
| `draw_arrow` | `(rgba, width, height, x1, y1, x2, y2, color=BLUE, thickness=3) -> bytes` | Draws a line with an arrowhead (30° angle, 15px arms) pointing at `(x2, y2)`. Used to visualise drag operations. |
| `draw_rectangle` | `(rgba, width, height, x1, y1, x2, y2, color=YELLOW, thickness=2) -> bytes` | Draws an axis-aligned rectangle outline. Currently unused by the agent but available for future annotations (e.g. region-of-interest highlighting, bounding box overlays). |
| `normalize_coord` | `(coord: int, max_val: int) -> int` | Converts a normalised coordinate (0–1000 range) to a pixel coordinate. Central to the coordinate system shared between VLM output and screen rendering. |

#### Coordinate System

All drawing functions operate in **pixel coordinates**. The `normalize_coord()` function
bridges between the VLM's 0–1000 normalised coordinate space and actual pixel space:

```
pixel_x = (normalized_x / 1000) × image_width
pixel_y = (normalized_y / 1000) × image_height
```

This normalisation makes the VLM's output resolution-independent — the same coordinates
work regardless of the capture resolution or display DPI.

---

## Coordinate Pipeline

```
VLM output:  left_click(650, 420)        ← normalised 0–1000
                    │
                    ▼
Visualisation:  normalize_coord(650, 1536) = 998px   ← for annotation overlay
                normalize_coord(420, 864)  = 363px
                    │
                    ▼
Execution:      (650/1000) × screen_w = actual pixel  ← for OS cursor/click
                (420/1000) × screen_h = actual pixel
```

Note: the visualisation pipeline maps to **image dimensions** (1536×864), while the
execution pipeline maps to **screen dimensions** (native resolution). These may differ
when downsampling is active.

---

## Deployment

### Requirements

- **OS**: Windows (uses Win32 GDI, `user32.dll`, `gdi32.dll`, `shcore.dll`)
- **Python**: 3.10+ (uses `match` statements, `X | Y` type unions, `slots=True`)
- **VLM Endpoint**: OpenAI-compatible `/v1/chat/completions` with vision support
- **No pip dependencies**: All modules use only the Python standard library and `ctypes`

### Configuration

Edit constants at the top of `main.py`:

```python
API = "http://localhost:1234/v1/chat/completions"  # VLM endpoint
MODEL = "qwen3-vl-2b-instruct-1m"                  # Model name
TARGET_WIDTH = 1536                                 # Screenshot width for VLM
TARGET_HEIGHT = 864                                 # Screenshot height for VLM
```

### Running

```
python main.py
```

Screenshots and story state are saved to `dump/run_YYYYMMDD_HHMMSS/`.

---

## Design Philosophy

FRANZ treats the VLM not as a chatbot but as a **perceptual cortex** — a stateless
function that maps `(visual_input, narrative_context, last_action)` to
`(next_action, updated_narrative)`. The narrative is not a log; it is a **lossy
compression of episodic memory** that the agent rewrites on every cycle to maintain
relevance within a fixed context window.

This design was chosen because:

1. **Stateless APIs are the norm.** Most VLM serving infrastructure does not maintain
   session state. FRANZ works with any OpenAI-compatible endpoint without requiring
   server-side memory.

2. **Context windows are finite.** Appending conversation turns eventually exceeds
   the model's context length. Narrative replacement keeps token usage constant.

3. **Agents need to run forever.** A desktop assistant that crashes after 50 iterations
   because it ran out of context is not useful. FRANZ's memory model has no theoretical
   iteration limit.

4. **Natural language is a universal state representation.** The story can encode
   arbitrary state — completed steps, current UI context, error recovery status,
   revised sub-goals — without requiring structured state schemas.

The agent's single-step commitment policy (one action per observation) sacrifices speed
for robustness: after every action, the agent re-perceives the world and can correct
course. This is essential when operating on a real desktop where UI state is
unpredictable and actions can fail silently.
