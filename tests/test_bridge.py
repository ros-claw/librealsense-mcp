#!/usr/bin/env python3
"""
test_bridge.py — 测试 RealSenseBridge 的核心功能。
需要连接 RealSense 硬件。
"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PASSED = 0
FAILED = 0


def test(name: str, condition: bool, detail: str = "") -> None:
    global PASSED, FAILED
    if condition:
        PASSED += 1
        print(f"  ✅ {name}")
    else:
        FAILED += 1
        print(f"  ❌ {name}: {detail}")


def main() -> None:
    global PASSED, FAILED

    print("\n=== librealsense-mcp Bridge Tests (需要硬件) ===\n")

    from bridge import RealSenseBridge

    bridge = RealSenseBridge.instance()

    # ── Test 1: 设备发现 ──
    print("[1] Device Discovery")
    devices = bridge.list_devices()
    test("list_devices returns list", isinstance(devices, list))
    test("found at least 1 device", len(devices) >= 1, f"found {len(devices)}")

    if not devices:
        print("\n⚠️  无连接设备，跳过硬件测试")
        sys.exit(1)

    serial = devices[0]["serial"]
    print(f"    Using device: {devices[0]['name']} (serial={serial})")

    # ── Test 2: 设备信息 ──
    print("\n[2] Device Info")
    info = bridge.get_device_info(serial)
    test("get_device_info returns dict", isinstance(info, dict))
    test("has serial_number field", "serial_number" in info)
    test("has sensors field", "sensors" in info)

    # ── Test 3: Pipeline 生命周期 ──
    print("\n[3] Pipeline Lifecycle")
    result = bridge.start_pipeline(serial, width=640, height=480, fps=15,
                                    enable_color=True, enable_depth=True)
    test("start_pipeline succeeds", "serial" in result)
    test("streams includes depth", "depth" in result.get("streams", []))
    test("streams includes color", "color" in result.get("streams", []))

    status = bridge.get_pipeline_status()
    test("pipeline shows in status", len(status) >= 1)

    # 预热：丢弃前几帧
    time.sleep(1)

    # ── Test 4: 帧捕获 ──
    print("\n[4] Frame Capture")
    frames = bridge.capture_frames(serial, align_depth=True)
    test("capture_frames returns dict", isinstance(frames, dict))
    test("has depth info", "depth" in frames)
    test("has color info", "color" in frames)
    test("aligned=True", frames.get("aligned") is True)

    # ── Test 5: 彩色图保存 ──
    print("\n[5] Color Image Capture")
    color_path = "/tmp/realsense/test_color.png"
    result = bridge.capture_color_image(serial, color_path)
    test("capture_color_image returns path", "path" in result)
    test("file exists", os.path.isfile(result.get("path", "")))
    if os.path.isfile(result.get("path", "")):
        size = os.path.getsize(result["path"])
        test(f"file size > 0 ({size} bytes)", size > 0)

    # ── Test 6: 深度图保存 ──
    print("\n[6] Depth Image Capture")
    depth_path = "/tmp/realsense/test_depth.png"
    result = bridge.capture_depth_image(serial, depth_path, colorize=True)
    test("capture_depth_image returns path", "path" in result)
    test("file exists", os.path.isfile(result.get("path", "")))

    # ── Test 7: 对齐 RGBD ──
    print("\n[7] Aligned RGBD")
    result = bridge.capture_aligned_rgbd(
        serial,
        "/tmp/realsense/test_aligned_color.png",
        "/tmp/realsense/test_aligned_depth.png",
    )
    test("has color_path", "color_path" in result)
    test("has depth_path", "depth_path" in result)
    test("aligned=True", result.get("aligned") is True)

    # ── Test 8: 深度测量 ──
    print("\n[8] Depth Measurement")
    dist = bridge.get_distance(serial, 320, 240)
    test("get_distance returns dict", isinstance(dist, dict))
    test("has distance_meters", "distance_meters" in dist)
    d = dist.get("distance_meters", -1)
    print(f"    Distance at (320,240): {d}m")

    stats = bridge.get_depth_stats(serial)
    test("get_depth_stats returns dict", isinstance(stats, dict))
    test("has mean_m", "mean_m" in stats)
    if stats.get("mean_m") is not None:
        print(f"    Depth stats: min={stats['min_m']}m, max={stats['max_m']}m, mean={stats['mean_m']}m")

    # ── Test 9: 内参/外参 ──
    print("\n[9] Intrinsics / Extrinsics")
    intr = bridge.get_intrinsics(serial, "depth")
    test("get_intrinsics returns dict", isinstance(intr, dict))
    test("has fx", "fx" in intr)
    test("has fy", "fy" in intr)
    print(f"    Depth intrinsics: {intr.get('width')}x{intr.get('height')}, fx={intr.get('fx')}, fy={intr.get('fy')}")

    ext = bridge.get_extrinsics(serial, "depth", "color")
    test("get_extrinsics returns dict", isinstance(ext, dict))
    test("has rotation (9 elements)", len(ext.get("rotation", [])) == 9)
    test("has translation (3 elements)", len(ext.get("translation", [])) == 3)

    # ── Test 10: 像素反投影 ──
    print("\n[10] Deproject Pixel")
    pt = bridge.deproject_pixel(serial, 320, 240)
    test("deproject_pixel returns dict", isinstance(pt, dict))
    test("has point_3d", "point_3d" in pt)
    p3d = pt.get("point_3d", {})
    print(f"    Pixel (320,240) -> 3D ({p3d.get('x')}, {p3d.get('y')}, {p3d.get('z')})")

    # ── Test 11: 点云 ──
    print("\n[11] Point Cloud")
    pc_result = bridge.capture_pointcloud(serial, "/tmp/realsense/test_pointcloud.ply")
    test("capture_pointcloud returns path", "path" in pc_result)
    test("has vertex_count", "vertex_count" in pc_result)
    test("file exists", os.path.isfile(pc_result.get("path", "")))
    print(f"    Point cloud: {pc_result.get('vertex_count')} vertices")

    pc_data = bridge.get_pointcloud_data(serial, downsample=10)
    test("get_pointcloud_data returns dict", isinstance(pc_data, dict))
    test("has valid_points", "valid_points" in pc_data)

    # ── Test 12: 滤波器 ──
    print("\n[12] Depth Filters")
    filt = bridge.apply_depth_filters(serial, spatial=True, temporal=True, threshold_min=0.2, threshold_max=5.0)
    test("apply_depth_filters returns dict", isinstance(filt, dict))
    test("has filters_enabled", "filters_enabled" in filt)
    print(f"    Filters: {filt.get('filters_enabled')}")

    # 用滤波器再捕获一次深度
    result = bridge.capture_depth_image(serial, "/tmp/realsense/test_depth_filtered.png")
    test("filtered depth capture ok", "path" in result)

    # ── Test 13: 传感器选项 ──
    print("\n[13] Sensor Options")
    opts = bridge.get_sensor_options(serial, "depth")
    test("get_sensor_options returns dict", isinstance(opts, dict))
    test("has options", "options" in opts)
    opt_count = len(opts.get("options", {}))
    print(f"    Depth sensor has {opt_count} options")

    # ── Cleanup ──
    print("\n[Cleanup] Stop pipeline")
    bridge.stop_pipeline(serial)
    test("pipeline stopped", True)

    # ── Summary ──
    total = PASSED + FAILED
    print(f"\n{'='*50}")
    print(f"Results: {PASSED}/{total} passed, {FAILED} failed")
    if FAILED == 0:
        print("✅ All bridge tests passed!")
    else:
        print(f"❌ {FAILED} tests failed")
    print()

    sys.exit(0 if FAILED == 0 else 1)


if __name__ == "__main__":
    main()
