# FRANZ - Autonomous Windows Automation Agent

FRANZ is a vision-language model driven Windows automation system that observes, reasons, and interacts with the desktop environment through natural narrative-driven control loops.

## System Requirements

- Windows 11
- Python 3.12
- No external dependencies (stdlib only)
- Local LLM server compatible with OpenAI API format (tested with LM Studio)

## Architecture

The system consists of three core modules operating in a continuous observation-action loop:

### Core Modules

**screenshot.py**
- DPI-aware screen capture via Windows GDI
- Native PNG encoding without external libraries
- Configurable downsampling with high-quality StretchBlt
- Optional annotation injection for visual feedback
- Standalone CLI tool or importable module

**drawing.py**
- Pixel-level drawing primitives (crosshairs, circles, lines, arrows, rectangles)
- Action visualization overlay system
- Coordinate normalization utilities
- Color management with predefined constants

**main.py**
- VLM inference orchestration
- Response parsing and command extraction
- Smooth human-like mouse movement with easing functions
- Keyboard input synthesis with natural timing
- Action visualization pipeline
- Timestamped screenshot archiving

## Key Features

### Narrative-Driven Memory

The system maintains a self-evolving narrative that serves as episodic memory. Each iteration:
1. VLM observes screenshot with current narrative context
2. Generates new narrative segment describing observations and intent
3. Narrative replaces previous state (adaptive memory)
4. Actions emerge from narrative reasoning rather than explicit goals

This design allows the agent to maintain coherent behavior across iterations while adapting to changing screen states.

### Smooth Human-Like Actions

All interactions use interpolated motion with smoothstep easing:
- **Mouse movement**: 20-step interpolation from current position to target
- **Clicks**: Smooth approach, 150ms settle delay, then action
- **Drags**: Continuous motion with button held throughout
- **Typing**: Variable character delays (80ms) with word boundaries (150ms)
- **Visual feedback**: Actions annotated on archived screenshots

### Available Commands

- `click X Y` - Left click at normalized coordinates (0-1000)
- `rightclick X Y` - Right click at normalized coordinates
- `doubleclick X Y` - Double left click at normalized coordinates
- `drag X1 Y1 X2 Y2` - Drag from start to end coordinates
- `type "text"` - Keyboard input with natural timing

## Implementation

### screenshot.py

```python
# DPI awareness setup
shcore.SetProcessDpiAwareness(PROCESS_PER_MONITOR_DPI_AWARE)
```

# Capture flow
1. GetSystemMetrics for screen dimensions
2. BitBlt with SRCCOPY | CAPTUREBLT for screen copy
3. Optional downsample via StretchBlt with HALFTONE mode
4. BGRA to RGBA conversion with forced alpha=255
5. PNG encoding (manual IHDR/IDAT/IEND chunk construction)
6. Optional drawing function injection before encoding


### drawing.py

```python
# Pixel manipulation
- Direct bytearray indexing for RGBA channels
- Bresenham line algorithm for straight lines
- Parametric interpolation for arrows
- Filled/hollow primitives via distance checks
- Coordinate normalization: (0-1000) → (0-width/height)
```

### main.py

```python
# Action execution
- GetCursorPos for current position
- Smoothstep easing: t = t*t*(3-2*t)
- SetCursorPos in interpolated steps
- mouse_event for button states
- VkKeyScanW for character → virtual key mapping
- keybd_event with proper shift handling
```

## Configuration

Edit constants in main.py:

```python
API = "http://localhost:1234/v1/chat/completions"
MODEL = "qwen3-vl-2b-instruct-1m"
TARGET_WIDTH = 1536
TARGET_HEIGHT = 864
MOVEMENT_STEPS = 20
STEP_DELAY = 0.01
CLICK_SETTLE_DELAY = 0.15
TYPING_CHAR_DELAY = 0.08
TYPING_WORD_DELAY = 0.15
ENABLE_VISUAL_FEEDBACK = True
```

## Usage

### Start LLM Server
```bash
# Launch local model server (LM Studio, llama.cpp, etc)
# Ensure endpoint matches API constant
```

### Run Agent
```bash
python main.py
```

### Manual Screenshot
```bash
python screenshot.py output.png 1920 1080
```

## Output Structure

```
dump/
└── run_YYYYMMDD_HHMMSS/
    ├── 1234567890123.png  # Timestamped screenshots with action overlays
    ├── 1234567890456.png
    └── story.txt           # Current narrative state
```

## System Prompt Structure

The VLM receives:
- System prompt defining available commands and format requirements
- Current narrative state
- Last executed action
- Screenshot as base64 PNG

Expected response format:
```python
click 500 300
type "search term"

"""
STORY_START
Brief narrative describing observation and intent (max 150 chars).
STORY_END
"""
```

## Technical Notes

### Why No Dependencies

- ctypes provides direct Windows API access
- struct/zlib sufficient for PNG encoding
- urllib for HTTP requests
- Native modules ensure portability and eliminate version conflicts

### DPI Awareness

SetProcessDpiAwareness(2) is critical for 1:1 screen capture on scaled displays. Without this, GetSystemMetrics returns scaled coordinates causing image clipping.

### Alpha Channel Handling

StretchBlt does not preserve alpha channel. All alpha bytes are forced to 255 post-capture to prevent transparency artifacts in browsers.

### Coordinate System

VLM operates in normalized 0-1000 space for resolution independence. Actual pixel coordinates calculated via:
```python
pixel_x = int((normalized_x / 1000.0) * screen_width)
```

## Limitations

- Windows 11 only (GDI dependencies)
- Single monitor support
- No scroll wheel control
- No special key combinations (Ctrl+C, Alt+Tab, etc)
- Typing limited to VkKeyScanW character set

## Extension Points

To add capabilities:
1. Add command to system prompt
2. Implement parsing in parse_action()
3. Add execution logic in execute_action()
4. Optional: Add visualization in create_visualization()

## License

Implementation details specific to Windows automation research.
This README provides complete technical specification for reconstructing the system from scratch while documenting the narrative-driven architecture and smooth action implementation.
