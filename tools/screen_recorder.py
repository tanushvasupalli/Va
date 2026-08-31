import sys
import os
import time
import datetime
import ctypes
from typing import Optional, Tuple
from pathlib import Path
import numpy as np

# Guard Windows DLLs on Linux/Android
user32 = getattr(getattr(ctypes, "windll", None), "user32", None)
gdi32 = getattr(getattr(ctypes, "windll", None), "gdi32", None)

RECORDINGS_DIR = Path(__file__).resolve().parent.parent / "data" / "recordings"

def record_screen_video(duration_seconds: int = 10, fps: int = 15) -> Tuple[Optional[str], str]:
    """
    Records the active Windows desktop for a specified duration into an MP4 video file.
    Uses Win32 GDI Display DC to guarantee active desktop pixel capture even in background threads.
    Args:
        duration_seconds: Duration to record (clamped between 2 and 60 seconds).
        fps: Target frame rate (default 15 FPS).
    Returns:
        (video_file_path or None, status_message)
    """
    if not user32 or not gdi32:
        return None, "Screen video recording is only supported on Windows desktop hosts."

    import imageio
    from ctypes import wintypes

    duration = max(2, min(int(duration_seconds), 60))
    fps = max(5, min(int(fps), 30))
    
    RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = RECORDINGS_DIR / f"screen_{timestamp_str}.mp4"

    # 1. Attach to active input desktop
    hdesk = user32.OpenInputDesktop(0, False, 0x01FF)
    if hdesk:
        user32.SetThreadDesktop(hdesk)

    srcdc = None
    memdc = None
    bmp = None

    try:
        srcdc = gdi32.CreateDCA(b"DISPLAY", None, None, None)
        if not srcdc:
            srcdc = user32.GetDC(0)

        # Get system metrics
        width = user32.GetSystemMetrics(0)
        height = user32.GetSystemMetrics(1)

        memdc = gdi32.CreateCompatibleDC(srcdc)
        bmp = gdi32.CreateCompatibleBitmap(srcdc, width, height)
        gdi32.SelectObject(memdc, bmp)

        bmi = bytearray(40)
        ctypes.c_uint32.from_buffer(bmi, 0).value = 40
        ctypes.c_int32.from_buffer(bmi, 4).value = width
        ctypes.c_int32.from_buffer(bmi, 8).value = -height  # Top-down DIB
        ctypes.c_uint16.from_buffer(bmi, 12).value = 1
        ctypes.c_uint16.from_buffer(bmi, 14).value = 32  # 32-bit BGRA

        buf_len = width * height * 4
        buf = bytearray(buf_len)
        buf_c = (ctypes.c_char * buf_len).from_buffer(buf)
        bmi_c = (ctypes.c_char * 40).from_buffer(bmi)

        frames = []
        frame_interval = 1.0 / fps
        start_time = time.time()
        
        while time.time() - start_time < duration:
            frame_start = time.time()
            
            # BitBlt with SRCCOPY | CAPTUREBLT
            gdi32.BitBlt(memdc, 0, 0, width, height, srcdc, 0, 0, 0x00CC0020 | 0x40000000)
            gdi32.GetDIBits(memdc, bmp, 0, height, buf_c, bmi_c, 0)
            
            # Convert BGRA buffer to RGB numpy array
            arr = np.frombuffer(buf, dtype=np.uint8).reshape((height, width, 4))
            rgb = arr[:, :, :3][:, :, ::-1].copy()
            frames.append(rgb)

            elapsed = time.time() - frame_start
            sleep_time = max(0.0, frame_interval - elapsed)
            if sleep_time > 0:
                time.sleep(sleep_time)

        if not frames:
            return None, "No frames were captured during screen recording."

        actual_duration = time.time() - start_time
        actual_fps = len(frames) / actual_duration

        # Write MP4 video using imageio-ffmpeg
        with imageio.get_writer(str(output_path), fps=actual_fps, codec="libx264", quality=8) as writer:
            for f in frames:
                writer.append_data(f)

        file_size_kb = round(output_path.stat().st_size / 1024, 1)
        msg = f"Screen recorded successfully: {len(frames)} frames ({round(actual_duration, 1)}s, {round(actual_fps, 1)} FPS, {file_size_kb} KB) -> {output_path.name}"
        return str(output_path), msg

    except Exception as e:
        return None, f"Screen recording failed: {e}"

    finally:
        if bmp and memdc:
            gdi32.DeleteObject(bmp)
        if memdc:
            gdi32.DeleteDC(memdc)
        if srcdc:
            gdi32.DeleteDC(srcdc)
        if hdesk:
            user32.CloseDesktop(hdesk)

def record_and_send_telegram_sync(duration_seconds: int = 10, caption: str = "") -> str:
    """
    Records the laptop screen for the specified seconds and immediately transmits
    the MP4 video to the authorized Telegram chat.
    """
    video_path, msg = record_screen_video(duration_seconds=duration_seconds)
    if not video_path:
        return f"Failed to record screen: {msg}"

    from core.telegram_bot import send_video_to_owner_sync
    cap = caption or f"🎥 Screen Recording ({duration_seconds}s)"
    send_msg = send_video_to_owner_sync(video_path, cap)
    return f"{msg}\n{send_msg}"
