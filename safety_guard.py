"""
SafetyGuard - 参数校验模块

对 RealSense MCP Server 的所有输入参数进行安全校验，
包括分辨率、FPS、像素坐标、文件路径和距离阈值等。
"""

import os
import logging
from typing import Tuple, Optional

logger = logging.getLogger("realsense.safety")

# ── 常量 ──────────────────────────────────────────────────────────────────────

MIN_WIDTH = 320
MAX_WIDTH = 1920
MIN_HEIGHT = 240
MAX_HEIGHT = 1080
MIN_FPS = 1
MAX_FPS = 90
MIN_DISTANCE = 0.0
MAX_DISTANCE = 65.535  # D400 系列最大量程 (uint16 * 0.001)

# 禁止写入的系统目录前缀
FORBIDDEN_PATH_PREFIXES = (
    "/etc", "/usr", "/bin", "/sbin", "/boot", "/lib",
    "/proc", "/sys", "/dev", "/var/run", "/run",
)

# 允许写入的目录白名单（如果设置了，只允许这些前缀）
ALLOWED_PATH_PREFIXES = (
    "/tmp/",
    "/home/",
)


class SafetyError(Exception):
    """安全校验失败异常"""
    pass


class SafetyGuard:
    """参数安全校验器"""

    # ── 分辨率 ────────────────────────────────────────────────────────────

    @staticmethod
    def validate_resolution(width: int, height: int) -> Tuple[bool, str]:
        """
        校验分辨率是否在允许范围内。

        Args:
            width: 图像宽度
            height: 图像高度

        Returns:
            (valid, message) 元组
        """
        if not isinstance(width, int) or not isinstance(height, int):
            return False, f"分辨率必须为整数, 实际: width={type(width).__name__}, height={type(height).__name__}"
        if width < MIN_WIDTH or width > MAX_WIDTH:
            return False, f"宽度 {width} 超出范围 [{MIN_WIDTH}, {MAX_WIDTH}]"
        if height < MIN_HEIGHT or height > MAX_HEIGHT:
            return False, f"高度 {height} 超出范围 [{MIN_HEIGHT}, {MAX_HEIGHT}]"
        return True, "OK"

    # ── FPS ───────────────────────────────────────────────────────────────

    @staticmethod
    def validate_fps(fps: int) -> Tuple[bool, str]:
        """
        校验帧率是否在允许范围内。

        Args:
            fps: 帧率

        Returns:
            (valid, message) 元组
        """
        if not isinstance(fps, int):
            return False, f"FPS 必须为整数, 实际: {type(fps).__name__}"
        if fps < MIN_FPS or fps > MAX_FPS:
            return False, f"FPS {fps} 超出范围 [{MIN_FPS}, {MAX_FPS}]"
        return True, "OK"

    # ── 像素坐标 ──────────────────────────────────────────────────────────

    @staticmethod
    def validate_pixel(x: int, y: int, width: int, height: int) -> Tuple[bool, str]:
        """
        校验像素坐标是否在图像范围内。

        Args:
            x: 像素 x 坐标
            y: 像素 y 坐标
            width: 图像宽度
            height: 图像高度

        Returns:
            (valid, message) 元组
        """
        if not isinstance(x, int) or not isinstance(y, int):
            return False, f"像素坐标必须为整数, 实际: x={type(x).__name__}, y={type(y).__name__}"
        if x < 0 or x >= width:
            return False, f"x 坐标 {x} 超出范围 [0, {width - 1}]"
        if y < 0 or y >= height:
            return False, f"y 坐标 {y} 超出范围 [0, {height - 1}]"
        return True, "OK"

    # ── ROI ───────────────────────────────────────────────────────────────

    @staticmethod
    def validate_roi(
        roi_x: int, roi_y: int, roi_w: int, roi_h: int,
        frame_width: int, frame_height: int
    ) -> Tuple[bool, str]:
        """
        校验 ROI 区域是否在帧范围内。

        Args:
            roi_x: ROI 起始 x
            roi_y: ROI 起始 y
            roi_w: ROI 宽度
            roi_h: ROI 高度
            frame_width: 帧宽度
            frame_height: 帧高度

        Returns:
            (valid, message) 元组
        """
        if roi_x < 0 or roi_y < 0 or roi_w <= 0 or roi_h <= 0:
            return False, f"ROI 参数无效: x={roi_x}, y={roi_y}, w={roi_w}, h={roi_h}"
        if roi_x + roi_w > frame_width:
            return False, f"ROI 右边界 {roi_x + roi_w} 超出帧宽度 {frame_width}"
        if roi_y + roi_h > frame_height:
            return False, f"ROI 下边界 {roi_y + roi_h} 超出帧高度 {frame_height}"
        return True, "OK"

    # ── 文件路径 ──────────────────────────────────────────────────────────

    @staticmethod
    def validate_file_path(path: str) -> Tuple[bool, str]:
        """
        校验文件路径是否安全（不允许写入系统目录）。

        Args:
            path: 文件保存路径

        Returns:
            (valid, message) 元组
        """
        if not path or not isinstance(path, str):
            return False, "文件路径不能为空"

        # 规范化路径（解析 .. 和符号链接）
        abs_path = os.path.realpath(os.path.abspath(path))

        # 检查是否在禁止的系统目录下
        for prefix in FORBIDDEN_PATH_PREFIXES:
            if abs_path.startswith(prefix):
                return False, f"禁止写入系统目录: {prefix}"

        # 确保父目录存在或可以创建
        parent = os.path.dirname(abs_path)
        if parent and not os.path.exists(parent):
            try:
                os.makedirs(parent, exist_ok=True)
            except OSError as e:
                return False, f"无法创建目录 {parent}: {e}"

        return True, "OK"

    # ── 距离阈值 ──────────────────────────────────────────────────────────

    @staticmethod
    def validate_distance_threshold(
        min_dist: float, max_dist: float
    ) -> Tuple[bool, str]:
        """
        校验距离阈值是否合理。

        Args:
            min_dist: 最小距离 (米)
            max_dist: 最大距离 (米)

        Returns:
            (valid, message) 元组
        """
        if min_dist < MIN_DISTANCE:
            return False, f"最小距离 {min_dist} 不能小于 {MIN_DISTANCE}"
        if max_dist > MAX_DISTANCE:
            return False, f"最大距离 {max_dist} 不能大于 {MAX_DISTANCE}"
        if min_dist >= max_dist:
            return False, f"最小距离 {min_dist} 必须小于最大距离 {max_dist}"
        return True, "OK"

    # ── Serial Number ────────────────────────────────────────────────────

    @staticmethod
    def validate_serial(serial: str) -> Tuple[bool, str]:
        """
        校验设备序列号格式。

        Args:
            serial: 设备序列号

        Returns:
            (valid, message) 元组
        """
        if not serial or not isinstance(serial, str):
            return False, "设备序列号不能为空"
        if not serial.strip():
            return False, "设备序列号不能为空白"
        # RealSense 序列号通常是纯数字，12位
        serial = serial.strip()
        if not serial.isdigit():
            return False, f"设备序列号格式无效 (应为纯数字): {serial}"
        return True, "OK"

    # ── Downsample ───────────────────────────────────────────────────────

    @staticmethod
    def validate_downsample(downsample: int) -> Tuple[bool, str]:
        """
        校验降采样倍率。

        Args:
            downsample: 降采样步长 (>=1)

        Returns:
            (valid, message) 元组
        """
        if not isinstance(downsample, int) or downsample < 1:
            return False, f"降采样步长必须为正整数, 实际: {downsample}"
        if downsample > 100:
            return False, f"降采样步长 {downsample} 过大 (最大 100)"
        return True, "OK"

    # ── 组合校验 ──────────────────────────────────────────────────────────

    @staticmethod
    def check(valid: bool, message: str) -> None:
        """
        如果校验失败，抛出 SafetyError。

        Args:
            valid: 校验结果
            message: 校验消息

        Raises:
            SafetyError: 校验失败时
        """
        if not valid:
            logger.warning(f"SafetyGuard 拒绝: {message}")
            raise SafetyError(message)
