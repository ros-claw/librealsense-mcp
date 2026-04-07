#!/usr/bin/env python3
"""
librealsense-mcp — MCP Server for Intel RealSense via pyrealsense2.

Exposes device management, frame capture, depth measurement, point cloud,
filters, calibration, device control, and multi-camera operations as MCP tools.

Usage:
    python mcp_server.py              # stdio transport (default)
    python mcp_server.py --test       # dry-run import test
"""

import sys
import os
import json
import logging
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP

# Ensure the package directory is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bridge import RealSenseBridge, DEFAULT_OUTPUT_DIR, SDKMetadata
from safety_guard import SafetyGuard, SafetyError, SAFETY_CONSTRAINTS, ERROR_DEFINITIONS

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
)
logger = logging.getLogger("realsense.mcp")

# ── MCP Server ────────────────────────────────────────────────────────────────
mcp = FastMCP(
    "librealsense-mcp",
    instructions="Intel RealSense MCP Server — 直接封装 pyrealsense2 SDK，"
                 "提供设备管理、帧捕获、深度测量、点云导出、滤波器、标定和多相机控制。",
)

# Lazy bridge singleton
_bridge: Optional[RealSenseBridge] = None


def _get_bridge() -> RealSenseBridge:
    global _bridge
    if _bridge is None:
        _bridge = RealSenseBridge.instance()
    return _bridge


def _ok(data: Dict[str, Any]) -> str:
    """Wrap result as JSON string for MCP tool return."""
    return json.dumps(data, ensure_ascii=False, indent=2)


def _err(msg: str) -> str:
    return json.dumps({"error": msg}, ensure_ascii=False, indent=2)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 1. 设备管理
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@mcp.tool()
def list_devices() -> str:
    """列出所有已连接的 Intel RealSense 设备。返回 serial、name、firmware_version、product_line。"""
    try:
        devices = _get_bridge().list_devices()
        return _ok({"devices": devices, "count": len(devices)})
    except Exception as e:
        return _err(str(e))


@mcp.tool()
def get_device_info(serial: str) -> str:
    """获取指定 RealSense 设备的详细信息（传感器列表、固件版本等）。

    Args:
        serial: 设备序列号，例如 "231122070092"
    """
    try:
        info = _get_bridge().get_device_info(serial)
        return _ok(info)
    except (SafetyError, RuntimeError) as e:
        return _err(str(e))


@mcp.tool()
def hardware_reset(serial: str) -> str:
    """硬件重置指定 RealSense 设备。重置后设备会断开再重新连接。

    Args:
        serial: 设备序列号
    """
    try:
        _get_bridge().hardware_reset(serial)
        return _ok({"serial": serial, "reset": True, "message": "设备已重置，请等待几秒后重新连接"})
    except (SafetyError, RuntimeError) as e:
        return _err(str(e))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 2. Pipeline 流控制
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@mcp.tool()
def start_pipeline(
    serial: str,
    width: int = 640,
    height: int = 480,
    fps: int = 30,
    enable_color: bool = True,
    enable_depth: bool = True,
    enable_infrared: bool = False,
    enable_imu: bool = False,
) -> str:
    """启动指定设备的数据流。

    Args:
        serial: 设备序列号
        width: 图像宽度 (320-1920)
        height: 图像高度 (240-1080)
        fps: 帧率 (1-90)，D435I 常用 15/30/60
        enable_color: 启用彩色流 (BGR8)
        enable_depth: 启用深度流 (Z16)
        enable_infrared: 启用红外流 (Y8)
        enable_imu: 启用 IMU 流 (加速度计+陀螺仪)
    """
    try:
        result = _get_bridge().start_pipeline(
            serial=serial, width=width, height=height, fps=fps,
            enable_color=enable_color, enable_depth=enable_depth,
            enable_infrared=enable_infrared, enable_imu=enable_imu,
        )
        return _ok(result)
    except (SafetyError, RuntimeError) as e:
        return _err(str(e))


@mcp.tool()
def stop_pipeline(serial: str) -> str:
    """停止指定设备的数据流。

    Args:
        serial: 设备序列号
    """
    try:
        _get_bridge().stop_pipeline(serial)
        return _ok({"serial": serial, "stopped": True})
    except (SafetyError, RuntimeError) as e:
        return _err(str(e))


@mcp.tool()
def get_pipeline_status() -> str:
    """获取所有活动 pipeline 的状态（设备、分辨率、运行时长、滤波器等）。"""
    try:
        status = _get_bridge().get_pipeline_status()
        return _ok({"pipelines": status, "count": len(status)})
    except Exception as e:
        return _err(str(e))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 3. 帧捕获
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@mcp.tool()
def capture_frames(serial: str, align_depth: bool = True) -> str:
    """捕获一组帧，返回颜色/深度帧的元数据（分辨率、时间戳、帧号等）。

    Args:
        serial: 设备序列号
        align_depth: 是否将深度对齐到彩色坐标系
    """
    try:
        result = _get_bridge().capture_frames(serial, align_depth=align_depth)
        return _ok(result)
    except (SafetyError, RuntimeError) as e:
        return _err(str(e))


@mcp.tool()
def capture_color_image(serial: str, save_path: str = "") -> str:
    """捕获彩色图像并保存为 PNG/JPG 文件。

    Args:
        serial: 设备序列号
        save_path: 保存路径（默认 /tmp/realsense/<serial>_color.png）
    """
    try:
        if not save_path:
            save_path = os.path.join(DEFAULT_OUTPUT_DIR, f"{serial}_color.png")
        result = _get_bridge().capture_color_image(serial, save_path)
        return _ok(result)
    except (SafetyError, RuntimeError) as e:
        return _err(str(e))


@mcp.tool()
def capture_depth_image(serial: str, save_path: str = "", colorize: bool = True) -> str:
    """捕获深度图像并保存。可选伪彩色可视化或原始 16-bit 深度。

    Args:
        serial: 设备序列号
        save_path: 保存路径（默认 /tmp/realsense/<serial>_depth.png）
        colorize: True=伪彩色(JET)可视化, False=原始16-bit深度值
    """
    try:
        if not save_path:
            save_path = os.path.join(DEFAULT_OUTPUT_DIR, f"{serial}_depth.png")
        result = _get_bridge().capture_depth_image(serial, save_path, colorize=colorize)
        return _ok(result)
    except (SafetyError, RuntimeError) as e:
        return _err(str(e))


@mcp.tool()
def capture_aligned_rgbd(serial: str, color_path: str = "", depth_path: str = "") -> str:
    """捕获对齐的 RGBD 图像对（深度对齐到彩色坐标系）并分别保存。

    Args:
        serial: 设备序列号
        color_path: 彩色图保存路径
        depth_path: 深度图保存路径（16-bit PNG，无损）
    """
    try:
        if not color_path:
            color_path = os.path.join(DEFAULT_OUTPUT_DIR, f"{serial}_aligned_color.png")
        if not depth_path:
            depth_path = os.path.join(DEFAULT_OUTPUT_DIR, f"{serial}_aligned_depth.png")
        result = _get_bridge().capture_aligned_rgbd(serial, color_path, depth_path)
        return _ok(result)
    except (SafetyError, RuntimeError) as e:
        return _err(str(e))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 4. 深度测量
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@mcp.tool()
def get_distance(serial: str, x: int, y: int) -> str:
    """获取指定像素坐标的深度值（单位：米）。

    Args:
        serial: 设备序列号
        x: 像素 x 坐标 (0 ~ width-1)
        y: 像素 y 坐标 (0 ~ height-1)
    """
    try:
        result = _get_bridge().get_distance(serial, x, y)
        return _ok(result)
    except (SafetyError, RuntimeError) as e:
        return _err(str(e))


@mcp.tool()
def get_depth_stats(
    serial: str,
    roi_x: Optional[int] = None,
    roi_y: Optional[int] = None,
    roi_w: Optional[int] = None,
    roi_h: Optional[int] = None,
) -> str:
    """获取深度图的统计信息（最小/最大/均值/标准差，单位：米）。可指定 ROI 区域。

    Args:
        serial: 设备序列号
        roi_x: ROI 起始 x（可选，不传则统计全图）
        roi_y: ROI 起始 y
        roi_w: ROI 宽度
        roi_h: ROI 高度
    """
    try:
        result = _get_bridge().get_depth_stats(serial, roi_x, roi_y, roi_w, roi_h)
        return _ok(result)
    except (SafetyError, RuntimeError) as e:
        return _err(str(e))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 5. 点云
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@mcp.tool()
def capture_pointcloud(serial: str, save_path: str = "", with_color: bool = True) -> str:
    """捕获点云并导出为 PLY 文件。

    Args:
        serial: 设备序列号
        save_path: PLY 文件保存路径（默认 /tmp/realsense/<serial>_pointcloud.ply）
        with_color: 是否包含 RGB 颜色纹理
    """
    try:
        if not save_path:
            save_path = os.path.join(DEFAULT_OUTPUT_DIR, f"{serial}_pointcloud.ply")
        result = _get_bridge().capture_pointcloud(serial, save_path, with_color=with_color)
        return _ok(result)
    except (SafetyError, RuntimeError) as e:
        return _err(str(e))


@mcp.tool()
def get_pointcloud_data(serial: str, downsample: int = 1) -> str:
    """获取点云数据摘要（顶点总数、有效点数、3D 边界框、质心）。

    Args:
        serial: 设备序列号
        downsample: 降采样步长（1=不降采样，10=每10个点取1个）
    """
    try:
        result = _get_bridge().get_pointcloud_data(serial, downsample=downsample)
        return _ok(result)
    except (SafetyError, RuntimeError) as e:
        return _err(str(e))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 6. 滤波器
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@mcp.tool()
def apply_depth_filters(
    serial: str,
    decimation: bool = False,
    spatial: bool = True,
    temporal: bool = True,
    hole_filling: bool = False,
    threshold_min: float = 0.1,
    threshold_max: float = 10.0,
) -> str:
    """配置深度滤波器。配置后会自动应用于该设备后续所有深度帧的捕获操作。

    Args:
        serial: 设备序列号
        decimation: 启用抽取滤波器（降低分辨率，提升性能）
        spatial: 启用空间滤波器（边缘保持平滑）
        temporal: 启用时间滤波器（多帧平均去噪）
        hole_filling: 启用孔洞填充
        threshold_min: 距离阈值下限（米），小于此值的深度会被丢弃
        threshold_max: 距离阈值上限（米），大于此值的深度会被丢弃
    """
    try:
        result = _get_bridge().apply_depth_filters(
            serial, decimation=decimation, spatial=spatial,
            temporal=temporal, hole_filling=hole_filling,
            threshold_min=threshold_min, threshold_max=threshold_max,
        )
        return _ok(result)
    except (SafetyError, RuntimeError) as e:
        return _err(str(e))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 7. 标定信息
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@mcp.tool()
def get_intrinsics(serial: str, stream_type: str = "depth") -> str:
    """获取相机内参（焦距 fx/fy、主点 ppx/ppy、畸变模型和系数）。

    Args:
        serial: 设备序列号
        stream_type: 流类型 ("depth" / "color" / "infrared")
    """
    try:
        result = _get_bridge().get_intrinsics(serial, stream_type=stream_type)
        return _ok(result)
    except (SafetyError, RuntimeError) as e:
        return _err(str(e))


@mcp.tool()
def get_extrinsics(serial: str, from_stream: str = "depth", to_stream: str = "color") -> str:
    """获取两个流之间的外参（3x3 旋转矩阵 + 3D 平移向量）。

    Args:
        serial: 设备序列号
        from_stream: 源流类型 ("depth" / "color" / "infrared")
        to_stream: 目标流类型
    """
    try:
        result = _get_bridge().get_extrinsics(serial, from_stream=from_stream, to_stream=to_stream)
        return _ok(result)
    except (SafetyError, RuntimeError) as e:
        return _err(str(e))


@mcp.tool()
def deproject_pixel(serial: str, x: int, y: int) -> str:
    """将像素坐标(x,y)加深度值反投影为 3D 空间坐标（单位：米）。

    Args:
        serial: 设备序列号
        x: 像素 x 坐标
        y: 像素 y 坐标
    """
    try:
        result = _get_bridge().deproject_pixel(serial, x, y)
        return _ok(result)
    except (SafetyError, RuntimeError) as e:
        return _err(str(e))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 8. 设备控制
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@mcp.tool()
def get_sensor_options(serial: str, sensor_name: str = "depth") -> str:
    """列出传感器所有可用选项及当前值、范围、描述。

    Args:
        serial: 设备序列号
        sensor_name: 传感器名称 ("depth" / "color" / "RGB Camera" / "Stereo Module")
    """
    try:
        result = _get_bridge().get_sensor_options(serial, sensor_name=sensor_name)
        return _ok(result)
    except (SafetyError, RuntimeError) as e:
        return _err(str(e))


@mcp.tool()
def set_sensor_option(serial: str, sensor_name: str, option_name: str, value: float) -> str:
    """设置传感器的指定选项值。

    Args:
        serial: 设备序列号
        sensor_name: 传感器名称
        option_name: 选项名称（如 "exposure", "gain", "laser_power" 等，用 get_sensor_options 查看可用选项）
        value: 新的值（必须在选项的 min-max 范围内）
    """
    try:
        result = _get_bridge().set_sensor_option(serial, sensor_name, option_name, value)
        return _ok(result)
    except (SafetyError, RuntimeError) as e:
        return _err(str(e))


@mcp.tool()
def set_emitter(serial: str, enabled: bool) -> str:
    """控制 IR 结构光发射器的开关。

    Args:
        serial: 设备序列号
        enabled: True=开启发射器, False=关闭
    """
    try:
        result = _get_bridge().set_emitter(serial, enabled)
        return _ok(result)
    except (SafetyError, RuntimeError) as e:
        return _err(str(e))


@mcp.tool()
def set_exposure(serial: str, auto: bool = True, value: Optional[int] = None) -> str:
    """设置深度传感器的曝光模式。

    Args:
        serial: 设备序列号
        auto: True=自动曝光, False=手动曝光
        value: 手动曝光值（微秒），仅当 auto=False 时生效
    """
    try:
        result = _get_bridge().set_exposure(serial, auto=auto, value=value)
        return _ok(result)
    except (SafetyError, RuntimeError) as e:
        return _err(str(e))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 9. 高级模式
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@mcp.tool()
def get_advanced_mode_json(serial: str) -> str:
    """导出 D400 系列的高级模式配置（JSON 格式）。可用于备份或迁移配置。

    Args:
        serial: 设备序列号（必须是 D400 系列）
    """
    try:
        result = _get_bridge().get_advanced_mode_json(serial)
        return _ok(result)
    except (SafetyError, RuntimeError) as e:
        return _err(str(e))


@mcp.tool()
def load_advanced_mode_json(serial: str, json_path: str) -> str:
    """加载高级模式 JSON 配置到 D400 设备。

    Args:
        serial: 设备序列号
        json_path: JSON 配置文件的绝对路径
    """
    try:
        result = _get_bridge().load_advanced_mode_json(serial, json_path)
        return _ok(result)
    except (SafetyError, RuntimeError, FileNotFoundError) as e:
        return _err(str(e))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 10. 多相机
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@mcp.tool()
def start_multi_pipeline(configs: str) -> str:
    """批量启动多个 RealSense 相机的数据流。

    Args:
        configs: JSON 数组字符串，每项包含 serial 及可选的 width/height/fps/enable_color/enable_depth 等参数。
                 示例: '[{"serial":"231122070092","fps":15},{"serial":"147322071616","fps":15}]'
    """
    try:
        cfg_list = json.loads(configs)
        if not isinstance(cfg_list, list):
            return _err("configs 必须是 JSON 数组")
        results = _get_bridge().start_multi_pipeline(cfg_list)
        return _ok({"results": results})
    except json.JSONDecodeError as e:
        return _err(f"JSON 解析失败: {e}")
    except Exception as e:
        return _err(str(e))


@mcp.tool()
def capture_multi_frames(serials: str, align_depth: bool = True) -> str:
    """同时从多个相机捕获帧。

    Args:
        serials: JSON 数组字符串，包含设备序列号列表。
                 示例: '["231122070092","147322071616"]'
        align_depth: 是否对齐深度到彩色
    """
    try:
        serial_list = json.loads(serials)
        if not isinstance(serial_list, list):
            return _err("serials 必须是 JSON 数组")
        results = _get_bridge().capture_multi_frames(serial_list, align_depth=align_depth)
        return _ok({"results": results})
    except json.JSONDecodeError as e:
        return _err(f"JSON 解析失败: {e}")
    except Exception as e:
        return _err(str(e))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 5. SDK 元数据和系统信息 (基于 sdk_to_mcp 框架)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@mcp.tool()
def get_sdk_metadata() -> str:
    """获取 SDK 元数据信息。
    
    返回 RealSense SDK 的版本、源代码地址、文档链接、支持硬件等信息。
    基于 sdk_to_mcp 框架设计，用于版本跟踪和依赖管理。
    """
    try:
        metadata = SDKMetadata.get_instance()
        return _ok({
            "sdk_info": metadata.to_dict(),
            "server_version": "1.0.0",
            "framework": "sdk_to_mcp"
        })
    except Exception as e:
        return _err(str(e))


@mcp.tool()
def get_safety_constraints() -> str:
    """获取所有安全约束定义。
    
    返回所有参数的安全限制，包括最小/最大值、单位、安全级别等。
    用于了解系统安全边界和参数合法范围。
    """
    try:
        constraints = SafetyGuard.list_constraints()
        result = {}
        for name, constraint in constraints.items():
            result[name] = {
                "parameter": constraint.parameter,
                "min_value": constraint.min_value,
                "max_value": constraint.max_value,
                "units": constraint.units,
                "safety_level": constraint.safety_level.value,
                "description": constraint.description,
                "hardware_limit": constraint.hardware_limit,
                "software_guard": constraint.software_guard,
            }
        return _ok({
            "constraints": result,
            "count": len(result)
        })
    except Exception as e:
        return _err(str(e))


@mcp.tool()
def get_error_definitions() -> str:
    """获取所有错误定义。
    
    返回系统定义的错误代码、描述、严重程度和恢复建议。
    用于错误处理和故障排除。
    """
    try:
        errors = SafetyGuard.list_errors()
        result = {}
        for name, error in errors.items():
            result[name] = {
                "code": error.code,
                "name": error.name,
                "description": error.description,
                "severity": error.severity,
                "recoverable": error.recoverable,
                "suggested_action": error.suggested_action,
            }
        return _ok({
            "errors": result,
            "count": len(result)
        })
    except Exception as e:
        return _err(str(e))


@mcp.tool()
def validate_parameter(parameter: str, value: float) -> str:
    """验证单个参数是否符合安全约束。
    
    在发送命令前验证参数值是否有效。
    
    Args:
        parameter: 参数名称 (如 width, fps, distance_m 等)
        value: 要验证的数值
    
    Returns:
        验证结果，包含是否通过和详细消息
    """
    try:
        constraint = SafetyGuard.get_constraint(parameter)
        if constraint is None:
            return _err(f"未知参数: {parameter}")
        
        valid, message = constraint.validate(value)
        return _ok({
            "parameter": parameter,
            "value": value,
            "valid": valid,
            "message": message,
            "constraint": {
                "min": constraint.min_value,
                "max": constraint.max_value,
                "units": constraint.units,
                "safety_level": constraint.safety_level.value,
            }
        })
    except Exception as e:
        return _err(str(e))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Entry point
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if __name__ == "__main__":
    if "--test" in sys.argv:
        print("✅ librealsense-mcp server imported successfully")
        print(f"   Tools registered: {len(mcp._tool_manager._tools)}")
        for name in sorted(mcp._tool_manager._tools.keys()):
            print(f"   - {name}")
        sys.exit(0)

    mcp.run(transport="stdio")
