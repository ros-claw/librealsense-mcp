# librealsense-mcp

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![RealSense](https://img.shields.io/badge/Intel-RealSense-blue.svg)](https://www.intelrealsense.com/)

Intel RealSense MCP Server — 直接封装 pyrealsense2 SDK，提供 26 个 MCP tools，让 AI 助手能够直接控制 Intel RealSense 深度相机。

[English](#english) | [中文](#中文)

---

## 中文

### 📋 功能特性

#### 设备管理
- `list_devices` — 列出所有已连接的 Intel RealSense 设备
- `get_device_info` — 获取设备详细信息（传感器列表、固件版本等）
- `hardware_reset` — 硬件重置设备

#### 流控制
- `start_pipeline` — 启动设备数据流（color/depth/infrared/IMU）
- `stop_pipeline` — 停止数据流
- `get_pipeline_status` — 查看所有活动 pipeline 状态

#### 帧捕获
- `capture_frames` — 捕获帧元数据
- `capture_color_image` — 捕获彩色图并保存 PNG
- `capture_depth_image` — 捕获深度图（伪彩色或原始 16-bit）
- `capture_aligned_rgbd` — 捕获对齐的 RGBD 图像对

#### 深度测量
- `get_distance` — 获取像素坐标的深度值（米）
- `get_depth_stats` — 深度统计（min/max/mean/std），支持 ROI

#### 点云
- `capture_pointcloud` — 导出 PLY 点云文件
- `get_pointcloud_data` — 点云数据摘要（边界框、质心）

#### 滤波器
- `apply_depth_filters` — 配置深度滤波器链（阈值/抽取/空间/时间/孔洞填充）

#### 标定
- `get_intrinsics` — 相机内参（fx/fy/ppx/ppy/畸变系数）
- `get_extrinsics` — 流间外参（旋转+平移）
- `deproject_pixel` — 像素反投影为 3D 坐标

#### 设备控制
- `get_sensor_options` — 列出传感器可用选项
- `set_sensor_option` — 设置传感器选项
- `set_emitter` — IR 发射器开关
- `set_exposure` — 曝光控制

#### 高级模式
- `get_advanced_mode_json` — 导出 D400 高级模式 JSON
- `load_advanced_mode_json` — 加载高级模式配置

#### 多相机
- `start_multi_pipeline` — 批量启动多相机
- `capture_multi_frames` — 多相机同步帧捕获

---

### 🚀 快速开始

#### 安装依赖

```bash
# 安装 pyrealsense2 (根据你的平台选择)
# Ubuntu/Debian
pip install pyrealsense2

# 或从源码构建 (ARM64 平台如 Jetson)
# 参考: https://github.com/IntelRealSense/librealsense/blob/master/doc/installation.md

# 安装 Python 依赖
pip install -r requirements.txt
```

#### 测试服务器

```bash
# 测试 server 是否可启动
python mcp_server.py --test

# 运行 server (stdio 传输)
python mcp_server.py
```

#### MCP 配置

添加到 OpenClaw `config.yaml`:

```yaml
mcp:
  servers:
    librealsense:
      command: python3
      args: ["/path/to/librealsense-mcp/mcp_server.py"]
```

或使用 Claude Desktop 配置:

```json
{
  "mcpServers": {
    "librealsense": {
      "command": "python3",
      "args": ["/path/to/librealsense-mcp/mcp_server.py"]
    }
  }
}
```

---

### 🛠️ 硬件要求

- Intel RealSense D400/L500 系列相机
  - D435/D435i (推荐)
  - D455
  - D415
  - L515
- USB 3.0 连接 (必须)
- Python 3.8+

---

### 📝 示例用法

```python
# 列出所有设备
list_devices()
# 返回: {"devices": [{"serial": "12345", "name": "Intel RealSense D435"}], "count": 1}

# 启动相机 pipeline
start_pipeline(serial="12345", enable_color=True, enable_depth=True)

# 捕获彩色图像
capture_color_image(serial="12345", filename="color.png")

# 获取深度值
get_distance(serial="12345", x=320, y=240)
# 返回: {"distance_m": 1.25}

# 捕获点云
capture_pointcloud(serial="12345", filename="scene.ply")

# 停止 pipeline
stop_pipeline(serial="12345")
```

---

### 🔧 架构

```
┌─────────────────────────────────────────────────────────┐
│                     MCP Client                          │
│              (Claude / OpenClaw / etc.)                 │
└────────────────────┬────────────────────────────────────┘
                     │ stdio
                     ▼
┌─────────────────────────────────────────────────────────┐
│                 librealsense-mcp                        │
│              (mcp_server.py / FastMCP)                  │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│                   bridge.py                             │
│         (RealSenseBridge - pyrealsense2)                │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│              Intel RealSense SDK 2.0                    │
│                  (pyrealsense2)                         │
└────────────────────┬────────────────────────────────────┘
                     │ USB 3.0
                     ▼
┌─────────────────────────────────────────────────────────┐
│             Intel RealSense Camera                      │
│                (D435/D455/L515/etc.)                    │
└─────────────────────────────────────────────────────────┘
```

---

### 🧪 测试

```bash
# 运行测试
cd tests
python demo_capture.py
```

---

### 🤝 相关项目

- [realsense-ros-mcp](https://github.com/ros-claw/realsense-ros-mcp) — ROS2 版本的 RealSense MCP Server

---

### 📄 许可证

MIT License - 详见 [LICENSE](LICENSE)

---

## English

### 📋 Features

#### Device Management
- `list_devices` — List all connected Intel RealSense devices
- `get_device_info` — Get detailed device information
- `hardware_reset` — Hardware reset the device

#### Stream Control
- `start_pipeline` — Start device streaming (color/depth/infrared/IMU)
- `stop_pipeline` — Stop streaming
- `get_pipeline_status` — Check all active pipeline status

#### Frame Capture
- `capture_frames` — Capture frame metadata
- `capture_color_image` — Capture color image and save as PNG
- `capture_depth_image` — Capture depth image (colorized or raw 16-bit)
- `capture_aligned_rgbd` — Capture aligned RGBD image pair

#### Depth Measurement
- `get_distance` — Get depth value at pixel coordinates (meters)
- `get_depth_stats` — Depth statistics (min/max/mean/std), supports ROI

#### Point Cloud
- `capture_pointcloud` — Export PLY point cloud file
- `get_pointcloud_data` — Point cloud data summary (bounding box, centroid)

#### Filters
- `apply_depth_filters` — Configure depth filter chain (threshold/decimation/spatial/temporal/hole-filling)

#### Calibration
- `get_intrinsics` — Camera intrinsics (fx/fy/ppx/ppy/distortion coefficients)
- `get_extrinsics` — Stream-to-stream extrinsics (rotation + translation)
- `deproject_pixel` — Deproject pixel to 3D coordinates

#### Device Control
- `get_sensor_options` — List available sensor options
- `set_sensor_option` — Set sensor option
- `set_emitter` — IR emitter on/off
- `set_exposure` — Exposure control

#### Advanced Mode
- `get_advanced_mode_json` — Export D400 advanced mode JSON
- `load_advanced_mode_json` — Load advanced mode configuration

#### Multi-Camera
- `start_multi_pipeline` — Batch start multiple cameras
- `capture_multi_frames` — Multi-camera synchronized frame capture

---

### 🚀 Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Test server
python mcp_server.py --test

# Run server
python mcp_server.py
```

---

### 🛠️ Hardware Requirements

- Intel RealSense D400/L500 series cameras
- USB 3.0 connection (required)
- Python 3.8+

---

### 📄 License

MIT License

---

**Made with ❤️ for the robotics community**