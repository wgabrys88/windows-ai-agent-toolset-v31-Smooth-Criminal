# drawing.py
"""Drawing utilities for annotating screenshots with AI actions."""

from typing import Final

# Color constants (RGBA)
RED: Final = (255, 0, 0, 255)
GREEN: Final = (0, 255, 0, 255)
BLUE: Final = (0, 150, 255, 255)
YELLOW: Final = (255, 255, 0, 255)
WHITE: Final = (255, 255, 255, 255)
BLACK: Final = (0, 0, 0, 255)


def draw_crosshair(rgba: bytes, width: int, height: int, x: int, y: int, size: int = 20, color: tuple[int, int, int, int] = RED, thickness: int = 2) -> bytes:
    """Draw a crosshair at specified coordinates.
    
    Args:
        rgba: RGBA image data
        width: Image width
        height: Image height
        x: X coordinate
        y: Y coordinate
        size: Size of crosshair arms in pixels
        color: RGBA color tuple
        thickness: Line thickness in pixels
    
    Returns:
        Modified RGBA image data with crosshair
    """
    data = bytearray(rgba)
    r, g, b, a = color
    
    # Draw horizontal line with thickness
    for dx in range(-size, size + 1):
        for dy in range(-thickness // 2, thickness // 2 + 1):
            px = x + dx
            py = y + dy
            if 0 <= px < width and 0 <= py < height:
                idx = (py * width + px) * 4
                data[idx:idx + 4] = bytes([r, g, b, a])
    
    # Draw vertical line with thickness
    for dy in range(-size, size + 1):
        for dx in range(-thickness // 2, thickness // 2 + 1):
            px = x + dx
            py = y + dy
            if 0 <= px < width and 0 <= py < height:
                idx = (py * width + px) * 4
                data[idx:idx + 4] = bytes([r, g, b, a])
    
    # Draw center circle
    center_radius = 3
    for cy in range(-center_radius, center_radius + 1):
        for cx in range(-center_radius, center_radius + 1):
            if cx * cx + cy * cy <= center_radius * center_radius:
                px = x + cx
                py = y + cy
                if 0 <= px < width and 0 <= py < height:
                    idx = (py * width + px) * 4
                    data[idx:idx + 4] = bytes([r, g, b, a])
    
    return bytes(data)


def draw_circle(rgba: bytes, width: int, height: int, x: int, y: int, radius: int, color: tuple[int, int, int, int] = GREEN, filled: bool = False) -> bytes:
    """Draw a circle at specified coordinates.
    
    Args:
        rgba: RGBA image data
        width: Image width
        height: Image height
        x: X coordinate (center)
        y: Y coordinate (center)
        radius: Circle radius
        color: RGBA color tuple
        filled: Whether to fill the circle
    
    Returns:
        Modified RGBA image data with circle
    """
    data = bytearray(rgba)
    r, g, b, a = color
    
    for cy in range(-radius, radius + 1):
        for cx in range(-radius, radius + 1):
            dist_sq = cx * cx + cy * cy
            if filled:
                if dist_sq <= radius * radius:
                    px = x + cx
                    py = y + cy
                    if 0 <= px < width and 0 <= py < height:
                        idx = (py * width + px) * 4
                        data[idx:idx + 4] = bytes([r, g, b, a])
            else:
                # Draw ring (hollow circle)
                if (radius - 2) * (radius - 2) <= dist_sq <= radius * radius:
                    px = x + cx
                    py = y + cy
                    if 0 <= px < width and 0 <= py < height:
                        idx = (py * width + px) * 4
                        data[idx:idx + 4] = bytes([r, g, b, a])
    
    return bytes(data)


def draw_line(rgba: bytes, width: int, height: int, x1: int, y1: int, x2: int, y2: int, color: tuple[int, int, int, int] = BLUE, thickness: int = 3) -> bytes:
    """Draw a line between two points using Bresenham's algorithm.
    
    Args:
        rgba: RGBA image data
        width: Image width
        height: Image height
        x1, y1: Start coordinates
        x2, y2: End coordinates
        color: RGBA color tuple
        thickness: Line thickness
    
    Returns:
        Modified RGBA image data with line
    """
    data = bytearray(rgba)
    r, g, b, a = color
    
    dx = abs(x2 - x1)
    dy = abs(y2 - y1)
    sx = 1 if x1 < x2 else -1
    sy = 1 if y1 < y2 else -1
    err = dx - dy
    
    x, y = x1, y1
    
    while True:
        # Draw thick point
        for ty in range(-thickness // 2, thickness // 2 + 1):
            for tx in range(-thickness // 2, thickness // 2 + 1):
                px = x + tx
                py = y + ty
                if 0 <= px < width and 0 <= py < height:
                    idx = (py * width + px) * 4
                    data[idx:idx + 4] = bytes([r, g, b, a])
        
        if x == x2 and y == y2:
            break
        
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x += sx
        if e2 < dx:
            err += dx
            y += sy
    
    return bytes(data)


def draw_arrow(rgba: bytes, width: int, height: int, x1: int, y1: int, x2: int, y2: int, color: tuple[int, int, int, int] = BLUE, thickness: int = 3) -> bytes:
    """Draw an arrow from point 1 to point 2.
    
    Args:
        rgba: RGBA image data
        width: Image width
        height: Image height
        x1, y1: Start coordinates
        x2, y2: End coordinates (arrow points here)
        color: RGBA color tuple
        thickness: Line thickness
    
    Returns:
        Modified RGBA image data with arrow
    """
    import math
    
    # Draw main line
    rgba = draw_line(rgba, width, height, x1, y1, x2, y2, color, thickness)
    
    # Calculate arrow head
    arrow_length = 15
    arrow_angle = math.pi / 6  # 30 degrees
    
    angle = math.atan2(y2 - y1, x2 - x1)
    
    # Left arrow line
    left_x = int(x2 - arrow_length * math.cos(angle - arrow_angle))
    left_y = int(y2 - arrow_length * math.sin(angle - arrow_angle))
    rgba = draw_line(rgba, width, height, x2, y2, left_x, left_y, color, thickness)
    
    # Right arrow line
    right_x = int(x2 - arrow_length * math.cos(angle + arrow_angle))
    right_y = int(y2 - arrow_length * math.sin(angle + arrow_angle))
    rgba = draw_line(rgba, width, height, x2, y2, right_x, right_y, color, thickness)
    
    return rgba


def draw_rectangle(rgba: bytes, width: int, height: int, x1: int, y1: int, x2: int, y2: int, color: tuple[int, int, int, int] = YELLOW, thickness: int = 2) -> bytes:
    """Draw a rectangle between two corners.
    
    Args:
        rgba: RGBA image data
        width: Image width
        height: Image height
        x1, y1: Top-left corner
        x2, y2: Bottom-right corner
        color: RGBA color tuple
        thickness: Border thickness
    
    Returns:
        Modified RGBA image data with rectangle
    """
    rgba = draw_line(rgba, width, height, x1, y1, x2, y1, color, thickness)  # Top
    rgba = draw_line(rgba, width, height, x2, y1, x2, y2, color, thickness)  # Right
    rgba = draw_line(rgba, width, height, x2, y2, x1, y2, color, thickness)  # Bottom
    rgba = draw_line(rgba, width, height, x1, y2, x1, y1, color, thickness)  # Left
    return rgba


def normalize_coord(coord: int, max_val: int) -> int:
    """Convert normalized coordinate (0-1000) to actual pixel coordinate.
    
    Args:
        coord: Normalized coordinate (0-1000)
        max_val: Maximum pixel value (width or height)
    
    Returns:
        Actual pixel coordinate
    """
    return int((coord / 1000.0) * max_val)
