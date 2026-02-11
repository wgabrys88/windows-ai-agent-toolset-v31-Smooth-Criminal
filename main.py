
# main.py
"""FRANZ - AI-driven Windows automation agent with smooth, human-like interactions."""

import base64
import ctypes
import json
import re
import time
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Final

import drawing
import screenshot

# Configuration
API: Final = "http://localhost:1234/v1/chat/completions"
MODEL: Final = "qwen3-vl-2b-instruct-1m"
TARGET_WIDTH: Final = 1536
TARGET_HEIGHT: Final = 864
SAMPLING: Final = {"temperature": 0.7, "top_p": 0.9, "max_tokens": 1000}
ENABLE_VISUAL_FEEDBACK: Final = True

# Animation settings
MOVEMENT_STEPS: Final = 20
STEP_DELAY: Final = 0.01  # 10ms per step = 200ms total movement time
CLICK_SETTLE_DELAY: Final = 0.15  # Pause after arriving before clicking
TYPING_CHAR_DELAY: Final = 0.08  # 80ms between characters (realistic typing)
TYPING_WORD_DELAY: Final = 0.15  # 150ms pause after spaces (thinking)

SYSTEM_PROMPT: Final = """You are FRANZ, a Windows controller. Analyze the screenshot and respond with exactly one ```python block containing:

Available commands (one per line):
- click X Y          (left click at normalized coords 0-1000)
- rightclick X Y     (right click at normalized coords 0-1000)
- doubleclick X Y    (double left click at normalized coords 0-1000)
- drag X1 Y1 X2 Y2   (drag from start to end coords)
- type TEXT          (type text with keyboard, use quotes if spaces: type "hello world")

Add a triple-quoted docstring with STORY_START/STORY_END (max 150 chars story).

Example:
```python
click 500 300
type "hello"
rightclick 600 400
\"\"\"
STORY_START
I clicked the search box and typed hello, then right-clicked the result.
STORY_END
\"\"\"
```

Keep simple. Sometimes just observe (story only, no commands)."""

USER_PROMPT_TEMPLATE: Final = """Current story:
{story}

Last action:
{last}"""


def infer(png_data: bytes, story: str, last: str) -> str:
    """Send inference request to API."""
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": USER_PROMPT_TEMPLATE.format(story=story, last=last)},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{base64.b64encode(png_data).decode()}"
                        },
                    },
                ],
            },
        ],
        **SAMPLING,
    }
    
    req = urllib.request.Request(
        API,
        json.dumps(payload).encode(),
        {"Content-Type": "application/json"},
    )
    
    with urllib.request.urlopen(req) as f:
        return json.load(f)["choices"][0]["message"]["content"]


def parse_response(content: str) -> tuple[list[str], str]:
    """Parse AI response for commands and story."""
    fence = re.search(r"```(?:python)?\s*(.*?)```", content, re.DOTALL | re.IGNORECASE)
    block = fence.group(1) if fence else content
    
    # Extract story from triple-quoted string
    doc = re.search(r'("""|' + r"''')(?P<body>.*?)(\\1)", block, re.DOTALL)
    if doc and "STORY_START" in doc["body"] and "STORY_END" in doc["body"]:
        if story_match := re.search(r"STORY_START(.*?)STORY_END", doc["body"], re.DOTALL):
            story = story_match.group(1).strip()
        else:
            story = doc["body"].strip()
        commands = [ln.strip() for ln in block.splitlines() if ln.strip() and not ln.strip().startswith(('"""', "'''", "#"))]
        commands = [cmd for cmd in commands if cmd.lower().split()[0] in ("click", "rightclick", "doubleclick", "drag", "type")]
        return commands, story
    
    # Try to extract story without docstring
    if story_match := re.search(r"STORY_START(.*?)STORY_END", block, re.DOTALL):
        story = story_match.group(1).strip()
        commands = [ln.strip() for ln in block.splitlines() if ln.strip() and ln.strip().lower().split()[0] in ("click", "rightclick", "doubleclick", "drag", "type")]
        return commands, story
    
    # Just extract commands
    commands = [ln.strip() for ln in block.splitlines() if ln.strip() and ln.strip().lower().split()[0] in ("click", "rightclick", "doubleclick", "drag", "type")]
    return commands, ""


def parse_action(cmd: str) -> tuple[str, list]:
    """Parse action type and parameters from command.
    
    Returns:
        Tuple of (action_type, parameters)
    """
    parts = cmd.strip().split(None, 1)
    if not parts:
        return "unknown", []
    
    action = parts[0].lower()
    
    if action in ("click", "rightclick", "doubleclick"):
        coords = parts[1].split() if len(parts) > 1 else []
        if len(coords) >= 2:
            return action, [int(coords[0]), int(coords[1])]
    
    elif action == "drag":
        coords = parts[1].split() if len(parts) > 1 else []
        if len(coords) >= 4:
            return action, [int(coords[0]), int(coords[1]), int(coords[2]), int(coords[3])]
    
    elif action == "type":
        if len(parts) > 1:
            text = parts[1]
            # Remove surrounding quotes if present
            if (text.startswith('"') and text.endswith('"')) or (text.startswith("'") and text.endswith("'")):
                text = text[1:-1]
            return action, [text]
    
    return "unknown", []


def create_visualization(last_action: str) -> callable:
    """Create drawing function based on last action."""
    def draw_annotations(rgba: bytes, width: int, height: int) -> bytes:
        if not ENABLE_VISUAL_FEEDBACK or last_action in ("init", "observe"):
            return rgba
        
        action_type, params = parse_action(last_action)
        
        if action_type in ("click", "doubleclick") and len(params) == 2:
            x = drawing.normalize_coord(params[0], width)
            y = drawing.normalize_coord(params[1], height)
            rgba = drawing.draw_crosshair(rgba, width, height, x, y, size=25, color=drawing.RED, thickness=3)
            rgba = drawing.draw_circle(rgba, width, height, x, y, radius=40, color=drawing.GREEN, filled=False)
        
        elif action_type == "rightclick" and len(params) == 2:
            x = drawing.normalize_coord(params[0], width)
            y = drawing.normalize_coord(params[1], height)
            rgba = drawing.draw_crosshair(rgba, width, height, x, y, size=25, color=drawing.BLUE, thickness=3)
            rgba = drawing.draw_circle(rgba, width, height, x, y, radius=40, color=drawing.YELLOW, filled=False)
        
        elif action_type == "drag" and len(params) == 4:
            x1 = drawing.normalize_coord(params[0], width)
            y1 = drawing.normalize_coord(params[1], height)
            x2 = drawing.normalize_coord(params[2], width)
            y2 = drawing.normalize_coord(params[3], height)
            rgba = drawing.draw_arrow(rgba, width, height, x1, y1, x2, y2, color=drawing.BLUE, thickness=4)
            rgba = drawing.draw_circle(rgba, width, height, x1, y1, radius=15, color=drawing.YELLOW, filled=True)
            rgba = drawing.draw_circle(rgba, width, height, x2, y2, radius=15, color=drawing.GREEN, filled=True)
        
        return rgba
    
    return draw_annotations


def get_cursor_position() -> tuple[int, int]:
    """Get current cursor position."""
    point = ctypes.wintypes.POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(point))
    return point.x, point.y


def smooth_move_to(target_x: int, target_y: int, steps: int = MOVEMENT_STEPS, delay: float = STEP_DELAY) -> None:
    """Smoothly move cursor from current position to target position."""
    start_x, start_y = get_cursor_position()
    
    for i in range(steps + 1):
        t = i / steps
        # Ease-in-out interpolation for more natural movement
        t = t * t * (3 - 2 * t)  # Smoothstep function
        
        x = int(start_x + (target_x - start_x) * t)
        y = int(start_y + (target_y - start_y) * t)
        
        ctypes.windll.user32.SetCursorPos(x, y)
        time.sleep(delay)


def press_key(vk_code: int) -> None:
    """Press and release a virtual key."""
    ctypes.windll.user32.keybd_event(vk_code, 0, 0, 0)  # Key down
    time.sleep(0.02)
    ctypes.windll.user32.keybd_event(vk_code, 0, 2, 0)  # Key up (KEYEVENTF_KEYUP = 2)


def type_text(text: str) -> None:
    """Type text with natural human-like timing.
    
    Args:
        text: Text to type
    """
    print(f'  → Typing: "{text}"')
    
    for char in text:
        if char == ' ':
            press_key(0x20)  # VK_SPACE
            time.sleep(TYPING_WORD_DELAY)  # Longer pause after spaces
        elif char == '\n':
            press_key(0x0D)  # VK_RETURN
            time.sleep(TYPING_WORD_DELAY)
        else:
            # Use Windows SendInput for proper character input
            # This handles special characters and different keyboard layouts
            ctypes.windll.user32.keybd_event(0, 0, 0, 0)  # Dummy to ensure focus
            
            # Convert character to virtual key and send
            vk = ctypes.windll.user32.VkKeyScanW(ord(char))
            if vk != -1:
                # Check if shift is needed (high byte)
                shift_needed = (vk >> 8) & 1
                vk_code = vk & 0xFF
                
                if shift_needed:
                    ctypes.windll.user32.keybd_event(0x10, 0, 0, 0)  # Shift down
                    time.sleep(0.01)
                
                press_key(vk_code)
                
                if shift_needed:
                    ctypes.windll.user32.keybd_event(0x10, 0, 2, 0)  # Shift up
            
            time.sleep(TYPING_CHAR_DELAY)


def execute_action(cmd: str) -> None:
    """Execute action with smooth, human-like behavior."""
    action_type, params = parse_action(cmd)
    
    screen_w = ctypes.windll.user32.GetSystemMetrics(0)
    screen_h = ctypes.windll.user32.GetSystemMetrics(1)
    
    if action_type == "click" and len(params) == 2:
        target_x = int((params[0] / 1000.0) * screen_w)
        target_y = int((params[1] / 1000.0) * screen_h)
        
        print(f"  → Moving to ({target_x}, {target_y})...")
        smooth_move_to(target_x, target_y)
        time.sleep(CLICK_SETTLE_DELAY)
        
        print(f"  → Left clicking...")
        ctypes.windll.user32.mouse_event(0x0002, 0, 0, 0, 0)  # MOUSEEVENTF_LEFTDOWN
        time.sleep(0.05)
        ctypes.windll.user32.mouse_event(0x0004, 0, 0, 0, 0)  # MOUSEEVENTF_LEFTUP
    
    elif action_type == "rightclick" and len(params) == 2:
        target_x = int((params[0] / 1000.0) * screen_w)
        target_y = int((params[1] / 1000.0) * screen_h)
        
        print(f"  → Moving to ({target_x}, {target_y})...")
        smooth_move_to(target_x, target_y)
        time.sleep(CLICK_SETTLE_DELAY)
        
        print(f"  → Right clicking...")
        ctypes.windll.user32.mouse_event(0x0008, 0, 0, 0, 0)  # MOUSEEVENTF_RIGHTDOWN
        time.sleep(0.05)
        ctypes.windll.user32.mouse_event(0x0010, 0, 0, 0, 0)  # MOUSEEVENTF_RIGHTUP
    
    elif action_type == "doubleclick" and len(params) == 2:
        target_x = int((params[0] / 1000.0) * screen_w)
        target_y = int((params[1] / 1000.0) * screen_h)
        
        print(f"  → Moving to ({target_x}, {target_y})...")
        smooth_move_to(target_x, target_y)
        time.sleep(CLICK_SETTLE_DELAY)
        
        print(f"  → Double clicking...")
        # First click
        ctypes.windll.user32.mouse_event(0x0002, 0, 0, 0, 0)
        time.sleep(0.05)
        ctypes.windll.user32.mouse_event(0x0004, 0, 0, 0, 0)
        time.sleep(0.08)  # Brief pause between clicks
        # Second click
        ctypes.windll.user32.mouse_event(0x0002, 0, 0, 0, 0)
        time.sleep(0.05)
        ctypes.windll.user32.mouse_event(0x0004, 0, 0, 0, 0)
    
    elif action_type == "drag" and len(params) == 4:
        x1 = int((params[0] / 1000.0) * screen_w)
        y1 = int((params[1] / 1000.0) * screen_h)
        x2 = int((params[2] / 1000.0) * screen_w)
        y2 = int((params[3] / 1000.0) * screen_h)
        
        print(f"  → Moving to drag start ({x1}, {y1})...")
        smooth_move_to(x1, y1)
        time.sleep(0.1)
        
        print(f"  → Grabbing...")
        ctypes.windll.user32.mouse_event(0x0002, 0, 0, 0, 0)
        time.sleep(0.1)
        
        print(f"  → Dragging to ({x2}, {y2})...")
        start_x, start_y = get_cursor_position()
        for i in range(MOVEMENT_STEPS + 1):
            t = i / MOVEMENT_STEPS
            t = t * t * (3 - 2 * t)  # Smoothstep
            
            x = int(start_x + (x2 - start_x) * t)
            y = int(start_y + (y2 - start_y) * t)
            
            ctypes.windll.user32.SetCursorPos(x, y)
            time.sleep(STEP_DELAY)
        
        print(f"  → Releasing...")
        time.sleep(0.1)
        ctypes.windll.user32.mouse_event(0x0004, 0, 0, 0, 0)
    
    elif action_type == "type" and len(params) == 1:
        type_text(params[0])


def main() -> None:
    """Main automation loop."""
    dump_dir = Path("dump") / datetime.now().strftime("run_%Y%m%d_%H%M%S")
    dump_dir.mkdir(parents=True, exist_ok=True)
    
    story = "FRANZ observing desktop."
    last_action = "init"
    
    iteration = 0
    
    print("\n" + "="*60)
    print("FRANZ - Smooth Human-Like Automation Agent")
    print("="*60)
    print(f"Screenshots: {dump_dir}")
    print(f"Movement: {MOVEMENT_STEPS} steps @ {STEP_DELAY*1000}ms = {MOVEMENT_STEPS*STEP_DELAY*1000}ms")
    print(f"Click settle: {CLICK_SETTLE_DELAY*1000}ms")
    print(f"Typing: {TYPING_CHAR_DELAY*1000}ms/char, {TYPING_WORD_DELAY*1000}ms/word")
    print("="*60 + "\n")
    
    while True:
        iteration += 1
        print(f"\n{'='*60}")
        print(f"Iteration {iteration}")
        print(f"{'='*60}")
        print(f"Story: {story}")
        print(f"Last: {last_action}")
        
        draw_func = create_visualization(last_action)
        img = screenshot.capture_screen_png(TARGET_WIDTH, TARGET_HEIGHT, draw_func=draw_func)
        
        timestamp = int(time.time() * 1000)
        (dump_dir / f"{timestamp}.png").write_bytes(img)
        
        print("Sending to AI...")
        content = infer(img, story, last_action)
        print(f"AI response:\n{content}\n")
        
        commands, story_candidate = parse_response(content)
        
        if commands:
            print(f"Executing {len(commands)} command(s):")
            for idx, cmd in enumerate(commands, 1):
                print(f"\n[{idx}] {cmd}")
                execute_action(cmd)
                last_action = cmd
                time.sleep(0.2)
        else:
            print("Observing only (no commands)")
            last_action = "observe"
        
        if story_candidate:
            story = story_candidate
            (dump_dir / "story.txt").write_text(story, encoding="utf-8")
            print(f"\nStory updated: {story}")
        
        time.sleep(0.5)


if __name__ == "__main__":
    main()
