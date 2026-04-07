"""
SafetyGuard - 增强版参数校验模块

基于 sdk_to_mcp 安全约束系统设计，提供结构化的安全校验，
包括分辨率、FPS、像素坐标、文件路径、距离阈值等。

Features:
    - SafetyConstraint dataclass 定义安全约束
    - 分级安全级别 (CRITICAL/HIGH/MEDIUM/LOW)
    - 完整的错误定义和恢复建议
    - 自动生成的参数验证方法
"""

import os
import logging
from typing import Tuple, Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger("realsense.safety")


# ── 安全级别枚举 ─────────────────────────────────────────────────────────────

class SafetyLevel(Enum):
    """安全分类等级"""
    CRITICAL = "critical"      # 立即物理危险
    HIGH = "high"              # 潜在硬件损坏
    MEDIUM = "medium"          # 操作问题
    LOW = "low"                # 信息警告
    NONE = "none"              # 无安全顾虑


# ── 安全约束定义 ─────────────────────────────────────────────────────────────

@dataclass
class SafetyConstraint:
    """
    参数安全约束定义
    
    Attributes:
        parameter: 参数名称
        min_value: 最小允许值
        max_value: 最大允许值
        units: 物理单位 (pixels, fps, meters, etc.)
        safety_level: 安全级别
        description: 人类可读的描述
        hardware_limit: 是否是硬件强制限制
        software_guard: 软件是否应该强制执行此限制
    """
    parameter: str
    min_value: Optional[float]
    max_value: Optional[float]
    units: str
    safety_level: SafetyLevel
    description: str
    hardware_limit: bool = True
    software_guard: bool = True

    def validate(self, value: float) -> Tuple[bool, str]:
        """验证值是否符合约束"""
        if self.min_value is not None and value < self.min_value:
            return False, (
                f"{self.parameter}={value}{self.units} 低于最小值 "
                f"{self.min_value}{self.units}"
            )
        if self.max_value is not None and value > self.max_value:
            return False, (
                f"{self.parameter}={value}{self.units} 超过最大值 "
                f"{self.max_value}{self.units}"
            )
        return True, "OK"


# ── 错误定义 ─────────────────────────────────────────────────────────────────

@dataclass
class ErrorDefinition:
    """
    SDK 错误代码定义
    
    Attributes:
        code: 错误代码
        name: 错误标识符
        description: 人类可读的描述
        severity: 错误严重程度 (critical/error/warning/info)
        recoverable: 错误是否可恢复
        suggested_action: 建议的修复步骤
    """
    code: str
    name: str
    description: str
    severity: str
    recoverable: bool
    suggested_action: str


# ── RealSense 安全约束表 ─────────────────────────────────────────────────────

SAFETY_CONSTRAINTS: Dict[str, SafetyConstraint] = {
    "width": SafetyConstraint(
        parameter="width",
        min_value=320,
        max_value=1920,
        units="pixels",
        safety_level=SafetyLevel.HIGH,
        description="图像宽度必须在相机传感器支持范围内",
        hardware_limit=True,
        software_guard=True,
    ),
    "height": SafetyConstraint(
        parameter="height",
        min_value=240,
        max_value=1080,
        units="pixels",
        safety_level=SafetyLevel.HIGH,
        description="图像高度必须在相机传感器支持范围内",
        hardware_limit=True,
        software_guard=True,
    ),
    "fps": SafetyConstraint(
        parameter="fps",
        min_value=1,
        max_value=90,
        units="fps",
        safety_level=SafetyLevel.MEDIUM,
        description="帧率必须在相机支持范围内",
        hardware_limit=True,
        software_guard=True,
    ),
    "distance_m": SafetyConstraint(
        parameter="distance_m",
        min_value=0.0,
        max_value=65.535,
        units="meters",
        safety_level=SafetyLevel.LOW,
        description="D400系列最大量程 (uint16 * 0.001)",
        hardware_limit=True,
        software_guard=False,
    ),
    "pixel_x": SafetyConstraint(
        parameter="pixel_x",
        min_value=0,
        max_value=None,  # 动态检查，基于图像宽度
        units="pixels",
        safety_level=SafetyLevel.MEDIUM,
        description="像素X坐标必须在图像范围内",
        hardware_limit=False,
        software_guard=True,
    ),
    "pixel_y": SafetyConstraint(
        parameter="pixel_y",
        min_value=0,
        max_value=None,  # 动态检查，基于图像高度
        units="pixels",
        safety_level=SafetyLevel.MEDIUM,
        description="像素Y坐标必须在图像范围内",
        hardware_limit=False,
        software_guard=True,
    ),
    "downsample": SafetyConstraint(
        parameter="downsample",
        min_value=1,
        max_value=100,
        units="factor",
        safety_level=SafetyLevel.LOW,
        description="降采样步长",
        hardware_limit=False,
        software_guard=True,
    ),
    "exposure": SafetyConstraint(
        parameter="exposure",
        min_value=1,
        max_value=10000,
        units="microseconds",
        safety_level=SafetyLevel.MEDIUM,
        description="曝光时间",
        hardware_limit=True,
        software_guard=True,
    ),
    "gain": SafetyConstraint(
        parameter="gain",
        min_value=0,
        max_value=255,
        units="level",
        safety_level=SafetyLevel.LOW,
        description="传感器增益",
        hardware_limit=True,
        software_guard=True,
    ),
}


# ── RealSense 错误定义表 ─────────────────────────────────────────────────────

ERROR_DEFINITIONS: Dict[str, ErrorDefinition] = {
    "DEVICE_NOT_FOUND": ErrorDefinition(
        code="RS001",
        name="DEVICE_NOT_FOUND",
        description="指定的 RealSense 设备未找到或已断开连接",
        severity="error",
        recoverable=True,
        suggested_action="检查USB连接，确认设备序列号正确，尝试重新插拔设备",
    ),
    "PIPELINE_ALREADY_STARTED": ErrorDefinition(
        code="RS002",
        name="PIPELINE_ALREADY_STARTED",
        description="该设备的 pipeline 已在运行",
        severity="warning",
        recoverable=True,
        suggested_action="先调用 stop_pipeline 停止当前 pipeline，或使用当前 pipeline",
    ),
    "PIPELINE_NOT_STARTED": ErrorDefinition(
        code="RS003",
        name="PIPELINE_NOT_STARTED",
        description="该设备的 pipeline 未启动",
        severity="error",
        recoverable=True,
        suggested_action="先调用 start_pipeline 启动设备",
    ),
    "FRAME_TIMEOUT": ErrorDefinition(
        code="RS004",
        name="FRAME_TIMEOUT",
        description="等待帧数据超时",
        severity="warning",
        recoverable=True,
        suggested_action="检查相机连接，降低帧率，或增加超时时间",
    ),
    "INVALID_RESOLUTION": ErrorDefinition(
        code="RS005",
        name="INVALID_RESOLUTION",
        description="请求的分辨率不受支持",
        severity="error",
        recoverable=True,
        suggested_action="使用 list_devices 查看支持的配置，选择有效的分辨率",
    ),
    "INVALID_SERIAL": ErrorDefinition(
        code="RS006",
        name="INVALID_SERIAL",
        description="设备序列号格式无效",
        severity="error",
        recoverable=True,
        suggested_action="提供正确的 RealSense 设备序列号（12位数字）",
    ),
    "FILE_ACCESS_DENIED": ErrorDefinition(
        code="RS007",
        name="FILE_ACCESS_DENIED",
        description="文件路径访问被拒绝",
        severity="error",
        recoverable=True,
        suggested_action="选择允许写入的目录（如 /tmp/ 或 /home/），避免系统目录",
    ),
    "DEPTH_SENSOR_NOT_AVAILABLE": ErrorDefinition(
        code="RS008",
        name="DEPTH_SENSOR_NOT_AVAILABLE",
        description="深度传感器不可用",
        severity="error",
        recoverable=False,
        suggested_action="确认设备支持深度流（如 D435/D455），检查固件版本",
    ),
    "SAFETY_CONSTRAINT_VIOLATION": ErrorDefinition(
        code="RS100",
        name="SAFETY_CONSTRAINT_VIOLATION",
        description="参数违反安全约束",
        severity="critical",
        recoverable=True,
        suggested_action="检查参数是否在安全范围内，参考 SAFETY_CONSTRAINTS 定义",
    ),
}


# ── 常量 ──────────────────────────────────────────────────────────────────────

# 禁止写入的系统目录前缀
FORBIDDEN_PATH_PREFIXES = (
    "/etc", "/usr", "/bin", "/sbin", "/boot", "/lib",
    "/proc", "/sys", "/dev", "/var/run", "/run",
)

# 允许写入的目录白名单
ALLOWED_PATH_PREFIXES = (
    "/tmp/",
    "/home/",
)


# ── 异常类 ───────────────────────────────────────────────────────────────────

class SafetyError(Exception):
    """安全校验失败异常"""
    pass


# ── SafetyGuard 类 ───────────────────────────────────────────────────────────

class SafetyGuard:
    """
    参数安全校验器 - 增强版
    
    基于 SafetyConstraint 定义，提供结构化的参数验证。
    每个验证方法对应一个 SAFETY_CONSTRAINTS 中的约束。
    """

    @staticmethod
    def validate_width(width: int) -> Tuple[bool, str]:
        """验证图像宽度"""
        if not isinstance(width, int):
            return False, f"width 必须为整数, 实际: {type(width).__name__}"
        return SAFETY_CONSTRAINTS["width"].validate(width)

    @staticmethod
    def validate_height(height: int) -> Tuple[bool, str]:
        """验证图像高度"""
        if not isinstance(height, int):
            return False, f"height 必须为整数, 实际: {type(height).__name__}"
        return SAFETY_CONSTRAINTS["height"].validate(height)

    @staticmethod
    def validate_resolution(width: int, height: int) -> Tuple[bool, str]:
        """验证分辨率组合"""
        valid_w, msg_w = SafetyGuard.validate_width(width)
        if not valid_w:
            return False, msg_w
        valid_h, msg_h = SafetyGuard.validate_height(height)
        if not valid_h:
            return False, msg_h
        return True, "OK"

    @staticmethod
    def validate_fps(fps: int) -> Tuple[bool, str]:
        """验证帧率"""
        if not isinstance(fps, int):
            return False, f"fps 必须为整数, 实际: {type(fps).__name__}"
        return SAFETY_CONSTRAINTS["fps"].validate(fps)

    @staticmethod
    def validate_pixel(x: int, y: int, width: int, height: int) -> Tuple[bool, str]:
        """验证像素坐标是否在图像范围内"""
        if not isinstance(x, int) or not isinstance(y, int):
            return False, f"像素坐标必须为整数, 实际: x={type(x).__name__}, y={type(y).__name__}"
        if x < 0 or x >= width:
            return False, f"x 坐标 {x} 超出范围 [0, {width - 1}]"
        if y < 0 or y >= height:
            return False, f"y 坐标 {y} 超出范围 [0, {height - 1}]"
        return True, "OK"

    @staticmethod
    def validate_roi(
        roi_x: int, roi_y: int, roi_w: int, roi_h: int,
        frame_width: int, frame_height: int
    ) -> Tuple[bool, str]:
        """验证 ROI 区域是否在帧范围内"""
        if roi_x < 0 or roi_y < 0 or roi_w <= 0 or roi_h <= 0:
            return False, f"ROI 参数无效: x={roi_x}, y={roi_y}, w={roi_w}, h={roi_h}"
        if roi_x + roi_w > frame_width:
            return False, f"ROI 右边界 {roi_x + roi_w} 超出帧宽度 {frame_width}"
        if roi_y + roi_h > frame_height:
            return False, f"ROI 下边界 {roi_y + roi_h} 超出帧高度 {frame_height}"
        return True, "OK"

    @staticmethod
    def validate_file_path(path: str) -> Tuple[bool, str]:
        """验证文件路径是否安全"""
        if not path or not isinstance(path, str):
            return False, "文件路径不能为空"

        # 规范化路径
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

    @staticmethod
    def validate_distance_m(distance: float) -> Tuple[bool, str]:
        """验证距离值（米）"""
        if not isinstance(distance, (int, float)):
            return False, f"distance 必须为数值, 实际: {type(distance).__name__}"
        return SAFETY_CONSTRAINTS["distance_m"].validate(float(distance))

    @staticmethod
    def validate_distance_threshold(min_dist: float, max_dist: float) -> Tuple[bool, str]:
        """验证距离阈值范围"""
        valid_min, msg_min = SafetyGuard.validate_distance_m(min_dist)
        if not valid_min:
            return False, f"最小距离错误: {msg_min}"
        valid_max, msg_max = SafetyGuard.validate_distance_m(max_dist)
        if not valid_max:
            return False, f"最大距离错误: {msg_max}"
        if min_dist >= max_dist:
            return False, f"最小距离 {min_dist} 必须小于最大距离 {max_dist}"
        return True, "OK"

    @staticmethod
    def validate_serial(serial: str) -> Tuple[bool, str]:
        """验证设备序列号格式"""
        if not serial or not isinstance(serial, str):
            return False, "设备序列号不能为空"
        serial = serial.strip()
        if not serial:
            return False, "设备序列号不能为空白"
        if not serial.isdigit():
            return False, f"设备序列号格式无效 (应为纯数字): {serial}"
        return True, "OK"

    @staticmethod
    def validate_downsample(downsample: int) -> Tuple[bool, str]:
        """验证降采样倍率"""
        if not isinstance(downsample, int):
            return False, f"downsample 必须为整数, 实际: {type(downsample).__name__}"
        return SAFETY_CONSTRAINTS["downsample"].validate(downsample)

    @staticmethod
    def validate_exposure(exposure: int) -> Tuple[bool, str]:
        """验证曝光时间"""
        if not isinstance(exposure, int):
            return False, f"exposure 必须为整数, 实际: {type(exposure).__name__}"
        return SAFETY_CONSTRAINTS["exposure"].validate(exposure)

    @staticmethod
    def validate_gain(gain: int) -> Tuple[bool, str]:
        """验证传感器增益"""
        if not isinstance(gain, int):
            return False, f"gain 必须为整数, 实际: {type(gain).__name__}"
        return SAFETY_CONSTRAINTS["gain"].validate(gain)

    @staticmethod
    def check(valid: bool, message: str) -> None:
        """如果校验失败，抛出 SafetyError"""
        if not valid:
            logger.warning(f"SafetyGuard 拒绝: {message}")
            raise SafetyError(message)

    @staticmethod
    def get_constraint(parameter: str) -> Optional[SafetyConstraint]:
        """获取参数的安全约束定义"""
        return SAFETY_CONSTRAINTS.get(parameter)

    @staticmethod
    def get_error_definition(error_name: str) -> Optional[ErrorDefinition]:
        """获取错误定义"""
        return ERROR_DEFINITIONS.get(error_name)

    @staticmethod
    def list_constraints() -> Dict[str, SafetyConstraint]:
        """列出所有安全约束"""
        return SAFETY_CONSTRAINTS.copy()

    @staticmethod
    def list_errors() -> Dict[str, ErrorDefinition]:
        """列出所有错误定义"""
        return ERROR_DEFINITIONS.copy()