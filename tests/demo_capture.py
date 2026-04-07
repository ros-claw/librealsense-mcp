#!/usr/bin/env python3
"""
demo_capture.py — 完整演示：发现设备 -> 启动流 -> 捕获 RGBD -> 导出点云 -> 停止

直接调用 bridge.py API，不经过 MCP。
用法: python tests/demo_capture.py [serial]
"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bridge import RealSenseBridge

OUTPUT_DIR = "/tmp/realsense/demo"


def main() -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    bridge = RealSenseBridge.instance()

    # ── 1. 发现设备 ──
    print("=" * 60)
    print("RealSense Demo Capture")
    print("=" * 60)

    devices = bridge.list_devices()
    if not devices:
        print("❌ 未发现任何 RealSense 设备")
        sys.exit(1)

    print(f"\n📷 发现 {len(devices)} 台设备:")
    for d in devices:
        print(f"   {d['name']} | serial={d['serial']} | FW={d['firmware_version']}")

    # 选择设备
    serial = sys.argv[1] if len(sys.argv) > 1 else devices[0]["serial"]
    print(f"\n▶ 使用设备: {serial}")

    # ── 2. 获取设备详情 ──
    info = bridge.get_device_info(serial)
    print(f"\n📋 设备详情:")
    for key, val in info.items():
        if key not in ("sensors", "is_pipeline_active"):
            print(f"   {key}: {val}")
    print(f"   sensors: {[s['name'] for s in info.get('sensors', [])]}")

    # ── 3. 启动 pipeline ──
    print(f"\n🚀 启动 pipeline (640x480@15fps, color+depth)...")
    result = bridge.start_pipeline(
        serial=serial,
        width=640, height=480, fps=15,
        enable_color=True, enable_depth=True,
    )
    print(f"   streams: {result['streams']}")
    print(f"   depth_scale: {result['depth_scale']}")

    # 预热
    print("   等待相机预热...")
    time.sleep(2)

    # ── 4. 捕获彩色图 ──
    print(f"\n🎨 捕获彩色图...")
    color_path = os.path.join(OUTPUT_DIR, f"{serial}_color.png")
    result = bridge.capture_color_image(serial, color_path)
    print(f"   保存: {result['path']} ({result['width']}x{result['height']})")

    # ── 5. 捕获深度图（伪彩色） ──
    print(f"\n🌈 捕获深度图 (伪彩色)...")
    depth_color_path = os.path.join(OUTPUT_DIR, f"{serial}_depth_colorized.png")
    result = bridge.capture_depth_image(serial, depth_color_path, colorize=True)
    print(f"   保存: {result['path']}")

    # ── 6. 捕获深度图（原始 16-bit） ──
    print(f"\n📏 捕获深度图 (原始 16-bit)...")
    depth_raw_path = os.path.join(OUTPUT_DIR, f"{serial}_depth_raw.png")
    result = bridge.capture_depth_image(serial, depth_raw_path, colorize=False)
    print(f"   保存: {result['path']}")

    # ── 7. 对齐 RGBD ──
    print(f"\n🔗 捕获对齐 RGBD...")
    result = bridge.capture_aligned_rgbd(
        serial,
        os.path.join(OUTPUT_DIR, f"{serial}_aligned_color.png"),
        os.path.join(OUTPUT_DIR, f"{serial}_aligned_depth.png"),
    )
    print(f"   color: {result['color_path']}")
    print(f"   depth: {result['depth_path']}")
    print(f"   depth_scale: {result['depth_scale']}")

    # ── 8. 深度测量 ──
    print(f"\n📐 深度测量...")
    cx, cy = 320, 240
    dist = bridge.get_distance(serial, cx, cy)
    print(f"   像素 ({cx},{cy}) 距离: {dist['distance_meters']}m")

    stats = bridge.get_depth_stats(serial, roi_x=200, roi_y=150, roi_w=240, roi_h=180)
    if stats.get("mean_m") is not None:
        print(f"   ROI (200,150,240x180) 统计:")
        print(f"     min={stats['min_m']}m, max={stats['max_m']}m")
        print(f"     mean={stats['mean_m']}m, std={stats['std_m']}m")
        print(f"     valid pixels: {stats['valid_pixels']}/{stats['total_pixels']}")

    # ── 9. 像素反投影 ──
    print(f"\n🎯 像素反投影...")
    pt = bridge.deproject_pixel(serial, cx, cy)
    p3d = pt["point_3d"]
    print(f"   像素 ({cx},{cy}) -> 3D ({p3d['x']}, {p3d['y']}, {p3d['z']})m")

    # ── 10. 内参/外参 ──
    print(f"\n📐 相机内参 (depth)...")
    intr = bridge.get_intrinsics(serial, "depth")
    print(f"   {intr['width']}x{intr['height']}, fx={intr['fx']}, fy={intr['fy']}")
    print(f"   ppx={intr['ppx']}, ppy={intr['ppy']}, model={intr['model']}")

    print(f"\n📐 外参 (depth -> color)...")
    ext = bridge.get_extrinsics(serial, "depth", "color")
    print(f"   translation: {ext['translation']}")

    # ── 11. 配置滤波器 ──
    print(f"\n🔧 配置深度滤波器...")
    filt = bridge.apply_depth_filters(
        serial, spatial=True, temporal=True,
        hole_filling=True, threshold_min=0.2, threshold_max=4.0,
    )
    print(f"   启用: {filt['filters_enabled']}")

    # 用滤波器捕获
    depth_filtered_path = os.path.join(OUTPUT_DIR, f"{serial}_depth_filtered.png")
    result = bridge.capture_depth_image(serial, depth_filtered_path, colorize=True)
    print(f"   滤波后深度图: {result['path']}")

    # ── 12. 点云导出 ──
    print(f"\n☁️  导出点云 PLY...")
    ply_path = os.path.join(OUTPUT_DIR, f"{serial}_pointcloud.ply")
    result = bridge.capture_pointcloud(serial, ply_path, with_color=True)
    print(f"   保存: {result['path']} ({result['vertex_count']} 个顶点)")

    pc_data = bridge.get_pointcloud_data(serial, downsample=10)
    if pc_data.get("bounds"):
        b = pc_data["bounds"]
        c = pc_data["centroid"]
        print(f"   边界: X[{b['x_min']}, {b['x_max']}], Y[{b['y_min']}, {b['y_max']}], Z[{b['z_min']}, {b['z_max']}]")
        print(f"   质心: ({c['x']}, {c['y']}, {c['z']})")

    # ── 13. 传感器选项 ──
    print(f"\n⚙️  传感器选项 (depth, 前5项)...")
    opts = bridge.get_sensor_options(serial, "depth")
    items = list(opts.get("options", {}).items())[:5]
    for name, info in items:
        print(f"   {name}: {info['value']} (range: {info['min']}-{info['max']})")

    # ── 14. 停止 ──
    print(f"\n⏹  停止 pipeline...")
    bridge.stop_pipeline(serial)
    print("   已停止")

    # ── 汇总 ──
    print(f"\n{'='*60}")
    print(f"✅ Demo 完成! 输出文件在: {OUTPUT_DIR}")
    files = os.listdir(OUTPUT_DIR)
    for f in sorted(files):
        size = os.path.getsize(os.path.join(OUTPUT_DIR, f))
        print(f"   {f} ({size:,} bytes)")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
