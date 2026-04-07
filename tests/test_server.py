#!/usr/bin/env python3
"""
test_server.py — 验证 librealsense-mcp server 能正常导入和初始化。
不需要连接硬件即可运行。
"""

import sys
import os
import importlib

# 确保能 import 项目模块
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

    print("\n=== librealsense-mcp Server Tests ===\n")

    # ── Test 1: safety_guard 可导入 ──
    print("[1] Import safety_guard")
    try:
        import safety_guard
        test("import safety_guard", True)
        test("SafetyGuard class exists", hasattr(safety_guard, "SafetyGuard"))
        test("SafetyError class exists", hasattr(safety_guard, "SafetyError"))
    except Exception as e:
        test("import safety_guard", False, str(e))

    # ── Test 2: safety_guard 校验逻辑 ──
    print("\n[2] SafetyGuard validation")
    from safety_guard import SafetyGuard, SafetyError

    ok, _ = SafetyGuard.validate_resolution(640, 480)
    test("valid resolution 640x480", ok)

    ok, _ = SafetyGuard.validate_resolution(4096, 2160)
    test("reject resolution 4096x2160", not ok)

    ok, _ = SafetyGuard.validate_fps(30)
    test("valid fps 30", ok)

    ok, _ = SafetyGuard.validate_fps(120)
    test("reject fps 120", not ok)

    ok, _ = SafetyGuard.validate_serial("231122070092")
    test("valid serial", ok)

    ok, _ = SafetyGuard.validate_serial("")
    test("reject empty serial", not ok)

    ok, _ = SafetyGuard.validate_file_path("/tmp/realsense/test.png")
    test("valid file path /tmp/...", ok)

    ok, _ = SafetyGuard.validate_file_path("/etc/passwd")
    test("reject /etc/passwd", not ok)

    ok, _ = SafetyGuard.validate_pixel(320, 240, 640, 480)
    test("valid pixel (320,240) in 640x480", ok)

    ok, _ = SafetyGuard.validate_pixel(640, 240, 640, 480)
    test("reject pixel x=640 in width=640", not ok)

    ok, _ = SafetyGuard.validate_distance_threshold(0.1, 10.0)
    test("valid distance threshold 0.1-10.0", ok)

    ok, _ = SafetyGuard.validate_distance_threshold(5.0, 3.0)
    test("reject min > max distance", not ok)

    # ── Test 3: bridge 可导入（允许 pyrealsense2 缺失时 rs=None） ──
    print("\n[3] Import bridge")
    try:
        import bridge
        test("import bridge", True)
        test("RealSenseBridge class exists", hasattr(bridge, "RealSenseBridge"))
        test("PipelineContext class exists", hasattr(bridge, "PipelineContext"))
        test("DEFAULT_OUTPUT_DIR defined", hasattr(bridge, "DEFAULT_OUTPUT_DIR"))
    except Exception as e:
        test("import bridge", False, str(e))

    # ── Test 4: mcp_server 可导入 ──
    print("\n[4] Import mcp_server")
    try:
        import mcp_server
        test("import mcp_server", True)
        test("mcp object exists", hasattr(mcp_server, "mcp"))
    except Exception as e:
        test("import mcp_server", False, str(e))

    # ── Test 5: MCP tool 函数签名检查 ──
    print("\n[5] MCP tool function signatures")
    if not hasattr(sys.modules.get("mcp_server", None), "mcp"):
        print("  ⚠️  mcp_server 未成功导入，跳过 tool 签名检查")
        total = PASSED + FAILED
        print(f"\n{'='*50}")
        print(f"Results: {PASSED}/{total} passed, {FAILED} failed")
        sys.exit(0 if FAILED == 0 else 1)
    import mcp_server
    expected_tools = [
        "list_devices", "get_device_info", "hardware_reset",
        "start_pipeline", "stop_pipeline", "get_pipeline_status",
        "capture_frames", "capture_color_image", "capture_depth_image",
        "capture_aligned_rgbd",
        "get_distance", "get_depth_stats",
        "capture_pointcloud", "get_pointcloud_data",
        "apply_depth_filters",
        "get_intrinsics", "get_extrinsics", "deproject_pixel",
        "get_sensor_options", "set_sensor_option", "set_emitter", "set_exposure",
        "get_advanced_mode_json", "load_advanced_mode_json",
        "start_multi_pipeline", "capture_multi_frames",
    ]
    for tool_name in expected_tools:
        exists = hasattr(mcp_server, tool_name) and callable(getattr(mcp_server, tool_name))
        test(f"tool function: {tool_name}", exists)

    # ── Summary ──
    total = PASSED + FAILED
    print(f"\n{'='*50}")
    print(f"Results: {PASSED}/{total} passed, {FAILED} failed")
    if FAILED == 0:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed")
    print()

    sys.exit(0 if FAILED == 0 else 1)


if __name__ == "__main__":
    main()
