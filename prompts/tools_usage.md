# Tools Usage Guide: Intel RealSense (pyrealsense2)

## Device Management

### `list_devices()`
List all connected RealSense cameras.

**Returns**: List of device serial numbers.

---

### `start_pipeline(serial_number=None)`
Start the camera pipeline.

**Parameters**:
- `serial_number`: Optional specific camera S/N

---

### `stop_pipeline()`
Stop the camera pipeline and release resources.

---

## Frame Capture

### `capture_frame()`
Capture synchronized color and depth frames.

**Returns**: Frame object with color and depth images.

---

### `get_depth_at_point(x, y)`
Get depth value at specific pixel coordinates.

**Parameters**:
- `x`: Horizontal pixel coordinate
- `y`: Vertical pixel coordinate

**Returns**: Depth in meters at that point.

---

### `export_point_cloud(filename)`
Export current frame as point cloud.

**Parameters**:
- `filename`: Output file path (.ply or .pcd)

---

## Configuration

### `set_exposure(exposure_ms)`
Set manual exposure time.

### `apply_filter(filter_type)`
Apply post-processing filter.

**Filter Types**:
- `decimation` - Downsample depth
- `spatial` - Smooth while preserving edges
- `temporal` - Reduce flickering
- `hole_filling` - Fill depth holes
