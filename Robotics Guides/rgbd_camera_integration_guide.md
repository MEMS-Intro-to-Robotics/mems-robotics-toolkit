# RGBD Camera Integration Guide

## Intel RealSense D435i with Kinova Gen3 Lite and MoveIt2

This guide covers integrating RGBD cameras into robotic manipulation workflows, from hardware setup through perception-based motion planning. It addresses both physical hardware (Intel RealSense D435i) and simulation environments.

---

## Table of Contents

1. [Overview and Architecture](#1-overview-and-architecture)
2. [Hardware Setup](#2-hardware-setup)
3. [RealSense ROS2 Driver](#3-realsense-ros2-driver)
4. [Simulation with Gazebo](#4-simulation-with-gazebo)
5. [Camera Calibration](#5-camera-calibration)
6. [Point Cloud Processing Fundamentals](#6-point-cloud-processing-fundamentals)
7. [Object Detection Pipeline](#7-object-detection-pipeline)
8. [MoveIt2 Perception Integration](#8-moveit2-perception-integration)
9. [Dynamic Pick and Place](#9-dynamic-pick-and-place)
10. [Troubleshooting](#10-troubleshooting)

---

## 1. Overview and Architecture

### What RGBD Cameras Provide

RGBD cameras combine:
- **RGB**: Color image (standard camera)
- **D**: Depth information (distance to each pixel)

This combination enables:
- 3D point cloud generation
- Object localization in 3D space
- Obstacle detection for collision avoidance
- Grasp point estimation

### System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           RGBD Camera                                    │
│                    (Intel RealSense D435i)                              │
└─────────────────────────────────────────────────────────────────────────┘
                                   │
                    ┌──────────────┴──────────────┐
                    ▼                              ▼
         ┌──────────────────┐           ┌──────────────────┐
         │   Color Image    │           │   Depth Image    │
         │ /camera/color/   │           │ /camera/depth/   │
         │   image_raw      │           │  image_rect_raw  │
         └────────┬─────────┘           └────────┬─────────┘
                  │                              │
                  └──────────────┬───────────────┘
                                 ▼
                    ┌────────────────────────┐
                    │   Aligned Point Cloud  │
                    │  /camera/depth/        │
                    │    color/points        │
                    └────────────┬───────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              ▼                  ▼                  ▼
    ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
    │ Object Detection│ │    Octomap      │ │  Grasp Planning │
    │  & Segmentation │ │ (MoveIt2 Scene) │ │                 │
    └────────┬────────┘ └────────┬────────┘ └────────┬────────┘
             │                   │                   │
             └───────────────────┼───────────────────┘
                                 ▼
                    ┌────────────────────────┐
                    │   Motion Planning      │
                    │   (MoveIt2 + Kinova)   │
                    └────────────────────────┘
```

### Camera Mounting Options

| Configuration | Description | Use Case |
|--------------|-------------|----------|
| **Eye-to-Hand** | Camera fixed in workspace (e.g., on tripod) | Large workspace coverage, static scenes |
| **Eye-in-Hand** | Camera mounted on robot end-effector | Close inspection, dynamic tracking |

This guide primarily covers **eye-to-hand** configuration, which is simpler for pick-and-place tasks.

---

## 2. Hardware Setup

### Intel RealSense D435i Specifications

| Property | Value |
|----------|-------|
| Depth Technology | Active IR Stereo |
| Depth Range | 0.1m - 10m |
| Depth Resolution | Up to 1280 × 720 |
| Depth FPS | Up to 90 fps |
| RGB Resolution | 1920 × 1080 |
| RGB FPS | Up to 30 fps |
| Field of View | 87° × 58° (depth) |
| IMU | Built-in (6-axis) |
| Interface | USB 3.0 |

### Physical Mounting Considerations

**For Eye-to-Hand Setup:**

1. **Height**: Mount 0.5-1.0m above the workspace
2. **Angle**: 30-45° downward tilt for tabletop viewing
3. **Distance**: Position so the workspace is within optimal depth range (0.3-3m for best accuracy)
4. **Stability**: Use rigid mounting to prevent vibration
5. **Lighting**: Avoid direct sunlight on IR sensors

**Workspace Geometry:**

```
        Camera (mounted above)
            │  ╲
            │   ╲  30-45°
            │    ╲
            ▼     ╲
    ┌───────────────────┐
    │                   │
    │    Workspace      │
    │    (table)        │
    │                   │
    └───────────────────┘
            │
       Robot Base
```

### USB Considerations

- **Use USB 3.0** (USB 2.0 limits bandwidth, reducing resolution/framerate)
- Avoid USB hubs if possible
- Check with `lsusb` that camera is recognized
- Use `rs-enumerate-devices` to verify firmware and connectivity

---

## 3. RealSense ROS2 Driver

### Installation

**Option 1: Binary Installation (Recommended for Jazzy)**

```bash
# Install librealsense2
sudo apt install ros-jazzy-librealsense2*

# Install ROS2 wrapper
sudo apt install ros-jazzy-realsense2-camera
```

**Option 2: Source Installation**

```bash
cd ~/ros2_ws/src
git clone https://github.com/IntelRealSense/realsense-ros.git -b ros2-master
cd ~/ros2_ws
rosdep install -i --from-paths src --rosdistro jazzy -y
colcon build --packages-select realsense2_camera realsense2_camera_msgs realsense2_description
```

### Launching the Camera

**Basic Launch:**

```bash
ros2 launch realsense2_camera rs_launch.py
```

**With Common Options:**

```bash
ros2 launch realsense2_camera rs_launch.py \
    depth_module.profile:=640x480x30 \
    rgb_camera.profile:=640x480x30 \
    enable_sync:=true \
    align_depth.enable:=true \
    pointcloud.enable:=true
```

**For RGBD with Aligned Point Cloud:**

```bash
ros2 launch realsense2_camera rs_launch.py \
    enable_rgbd:=true \
    enable_sync:=true \
    align_depth.enable:=true \
    enable_color:=true \
    enable_depth:=true \
    pointcloud.enable:=true
```

### Key Topics Published

| Topic | Type | Description |
|-------|------|-------------|
| `/camera/camera/color/image_raw` | `sensor_msgs/Image` | RGB image |
| `/camera/camera/color/camera_info` | `sensor_msgs/CameraInfo` | RGB intrinsics |
| `/camera/camera/depth/image_rect_raw` | `sensor_msgs/Image` | Depth image (aligned) |
| `/camera/camera/depth/camera_info` | `sensor_msgs/CameraInfo` | Depth intrinsics |
| `/camera/camera/depth/color/points` | `sensor_msgs/PointCloud2` | Colored point cloud |
| `/camera/camera/imu` | `sensor_msgs/Imu` | IMU data (D435i) |

### Launch Parameters Reference

| Parameter | Default | Description |
|-----------|---------|-------------|
| `camera_name` | `camera` | Namespace prefix |
| `serial_no` | (auto) | Specific camera serial number |
| `depth_module.profile` | `640x480x30` | Depth resolution and FPS |
| `rgb_camera.profile` | `640x480x30` | RGB resolution and FPS |
| `enable_sync` | `false` | Synchronize depth and color |
| `align_depth.enable` | `false` | Align depth to color frame |
| `pointcloud.enable` | `false` | Generate point cloud |
| `enable_gyro` | `false` | Enable gyroscope |
| `enable_accel` | `false` | Enable accelerometer |

### Verifying Camera Operation

```bash
# List topics
ros2 topic list | grep camera

# Check image publishing rate
ros2 topic hz /camera/camera/color/image_raw

# View camera info
ros2 topic echo /camera/camera/color/camera_info --once

# Visualize in RViz
rviz2
# Add Image display, set topic to /camera/camera/color/image_raw
# Add PointCloud2 display, set topic to /camera/camera/depth/color/points
```

---

## 4. Simulation with Gazebo

### Why Simulate?

- Develop and test perception algorithms without hardware
- Reproduce specific scenarios reliably
- Safe testing of manipulation behaviors
- CI/CD integration

### Adding a Depth Camera to Your Robot Model

**URDF/Xacro Depth Camera Definition:**

```xml
<!-- Camera link -->
<link name="camera_link">
  <visual>
    <origin xyz="0 0 0" rpy="0 0 0"/>
    <geometry>
      <box size="0.02 0.09 0.025"/>
    </geometry>
    <material name="silver"/>
  </visual>
  <collision>
    <origin xyz="0 0 0" rpy="0 0 0"/>
    <geometry>
      <box size="0.02 0.09 0.025"/>
    </geometry>
  </collision>
  <inertial>
    <mass value="0.1"/>
    <inertia ixx="0.0001" ixy="0" ixz="0" iyy="0.0001" iyz="0" izz="0.0001"/>
  </inertial>
</link>

<!-- Camera optical frame (Z forward, X right, Y down) -->
<link name="camera_depth_optical_frame"/>

<joint name="camera_optical_joint" type="fixed">
  <origin xyz="0 0 0" rpy="-1.5708 0 -1.5708"/>
  <parent link="camera_link"/>
  <child link="camera_depth_optical_frame"/>
</joint>

<!-- Mount camera to world or robot -->
<joint name="camera_mount_joint" type="fixed">
  <origin xyz="0.5 0.0 0.8" rpy="0 0.5 3.14159"/>
  <parent link="world"/>
  <child link="camera_link"/>
</joint>
```

**Gazebo Sensor Plugin (for Classic Gazebo):**

```xml
<gazebo reference="camera_link">
  <sensor name="depth_camera" type="depth">
    <update_rate>30</update_rate>
    <camera>
      <horizontal_fov>1.5184</horizontal_fov>  <!-- 87 degrees -->
      <image>
        <width>640</width>
        <height>480</height>
        <format>R8G8B8</format>
      </image>
      <clip>
        <near>0.1</near>
        <far>10.0</far>
      </clip>
    </camera>
    <plugin name="depth_camera_plugin" filename="libgazebo_ros_camera.so">
      <ros>
        <namespace>/camera</namespace>
        <remapping>image_raw:=color/image_raw</remapping>
        <remapping>camera_info:=color/camera_info</remapping>
        <remapping>depth/image_raw:=depth/image_rect_raw</remapping>
        <remapping>depth/camera_info:=depth/camera_info</remapping>
        <remapping>points:=depth/color/points</remapping>
      </ros>
      <frame_name>camera_depth_optical_frame</frame_name>
      <hack_baseline>0.07</hack_baseline>
      <min_depth>0.1</min_depth>
      <max_depth>10.0</max_depth>
    </plugin>
  </sensor>
</gazebo>
```

**For Gazebo Ignition (Fortress/Garden):**

```xml
<gazebo reference="camera_link">
  <sensor name="rgbd_camera" type="rgbd_camera">
    <camera>
      <horizontal_fov>1.5184</horizontal_fov>
      <image>
        <width>640</width>
        <height>480</height>
      </image>
      <clip>
        <near>0.1</near>
        <far>10.0</far>
      </clip>
    </camera>
    <always_on>1</always_on>
    <update_rate>30</update_rate>
    <visualize>true</visualize>
    <topic>rgbd_camera</topic>
    <gz_frame_id>camera_depth_optical_frame</gz_frame_id>
  </sensor>
</gazebo>
```

### Bridging Gazebo Topics to ROS2

For Gazebo Ignition, use `ros_gz_bridge`:

```bash
# Bridge RGB image
ros2 run ros_gz_bridge parameter_bridge \
    /rgbd_camera/image@sensor_msgs/msg/Image@gz.msgs.Image

# Bridge depth image  
ros2 run ros_gz_bridge parameter_bridge \
    /rgbd_camera/depth_image@sensor_msgs/msg/Image@gz.msgs.Image

# Bridge point cloud
ros2 run ros_gz_bridge parameter_bridge \
    /rgbd_camera/points@sensor_msgs/msg/PointCloud2@gz.msgs.PointCloudPacked
```

### Testing Simulated Camera

```bash
# Launch Gazebo with your robot and camera
ros2 launch your_package your_gazebo.launch.py

# Verify topics
ros2 topic list | grep camera

# Check in RViz
rviz2
# Add PointCloud2 display
# Set Fixed Frame to camera_depth_optical_frame or world
```

---

## 5. Camera Calibration

### Types of Calibration

| Type | Purpose | When Needed |
|------|---------|-------------|
| **Intrinsic** | Corrects lens distortion, establishes pixel-to-ray mapping | Factory-calibrated for RealSense, but can be refined |
| **Extrinsic (Hand-Eye)** | Determines camera pose relative to robot | Required for any manipulation task |

### Intrinsic Calibration

RealSense cameras come factory-calibrated. Access intrinsics via:

```bash
ros2 topic echo /camera/camera/color/camera_info --once
```

**Key Fields:**
- `K`: 3×3 intrinsic matrix (focal length, principal point)
- `D`: Distortion coefficients
- `P`: Projection matrix

If refinement is needed, use the ROS2 `camera_calibration` package:

```bash
ros2 run camera_calibration cameracalibrator \
    --size 8x6 \
    --square 0.025 \
    --ros-args -r image:=/camera/camera/color/image_raw \
               -r camera:=/camera/camera/color
```

### Hand-Eye Calibration (Extrinsic)

Hand-eye calibration finds the transformation between the camera frame and the robot base frame (eye-to-hand) or end-effector frame (eye-in-hand).

**Why It Matters:**

Without accurate hand-eye calibration, object positions detected by the camera cannot be accurately transformed into the robot's coordinate frame for manipulation.

**The AX = XB Problem:**

```
For eye-to-hand:
    T_base_camera = ?  (what we want)
    
We collect multiple pose pairs:
    T_base_ee (from robot FK)
    T_camera_marker (from marker detection)
    
The algorithm solves for T_base_camera
```

**Using MoveIt2 Hand-Eye Calibration:**

1. **Install the package:**
```bash
sudo apt install ros-jazzy-moveit-calibration
```

2. **Print an ArUco marker** or ChArUco board

3. **Launch your robot with MoveIt and camera:**
```bash
ros2 launch kinova_gen3_lite_moveit_config robot.launch.py robot_ip:=192.168.1.10
ros2 launch realsense2_camera rs_launch.py
```

4. **In RViz, add the HandEyeCalibration panel:**
   - Panels → Add New Panel → HandEyeCalibration

5. **Configure the Target tab:**
   - Set marker type and dimensions
   - Verify marker detection in the image

6. **Configure the Context tab:**
   - Set Sensor Frame: `camera_color_optical_frame`
   - Set End-Effector Frame: `tool_frame`
   - Set Robot Base Frame: `base_link`
   - Select calibration type: `eye-to-hand` or `eye-in-hand`

7. **Collect samples (minimum 5, recommended 15+):**
   - Move the robot to different poses
   - Ensure the marker is visible
   - Click "Take Sample"
   - **Important**: Include rotation around multiple axes

8. **Calculate and save the calibration**

**Publishing the Calibration:**

After calibration, publish the transform as a static TF:

```bash
ros2 run tf2_ros static_transform_publisher \
    x y z qx qy qz qw \
    base_link camera_link
```

Or in a launch file:

```python
Node(
    package='tf2_ros',
    executable='static_transform_publisher',
    arguments=['0.5', '0.3', '0.8', '0', '0.38', '0', '0.92', 'base_link', 'camera_link'],
)
```

---

## 6. Point Cloud Processing Fundamentals

### Understanding Point Clouds

A `sensor_msgs/PointCloud2` message contains:
- **points**: Array of 3D coordinates (x, y, z)
- **colors**: Optional RGB values per point
- **fields**: Description of data layout
- **header**: Frame ID and timestamp

### Common Processing Operations

#### Filtering

| Filter | Purpose | When to Use |
|--------|---------|-------------|
| **Voxel Grid** | Downsample by replacing points in each voxel with centroid | Reduce computational load |
| **PassThrough** | Crop to region of interest | Remove points outside workspace |
| **Statistical Outlier** | Remove noise/isolated points | Clean noisy data |
| **Radius Outlier** | Remove points with few neighbors | Remove sparse noise |

#### Segmentation

| Method | Purpose | When to Use |
|--------|---------|-------------|
| **RANSAC Plane** | Find dominant plane (table) | Isolate objects from table |
| **Euclidean Clustering** | Group nearby points | Separate individual objects |
| **Region Growing** | Segment based on normals/curvature | Smooth surface segmentation |

### Processing Pipeline Example (Python with Open3D)

```python
import numpy as np
import open3d as o3d
from sensor_msgs.msg import PointCloud2
import sensor_msgs_py.point_cloud2 as pc2

def process_point_cloud(msg: PointCloud2):
    """Basic point cloud processing pipeline."""
    
    # Convert ROS message to numpy array
    points = []
    for p in pc2.read_points(msg, field_names=("x", "y", "z"), skip_nans=True):
        points.append([p[0], p[1], p[2]])
    points = np.array(points)
    
    # Convert to Open3D point cloud
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(points)
    
    # 1. Voxel downsampling
    pcd_down = pcd.voxel_down_sample(voxel_size=0.005)
    
    # 2. Remove statistical outliers
    pcd_clean, _ = pcd_down.remove_statistical_outlier(
        nb_neighbors=20,
        std_ratio=2.0
    )
    
    # 3. Crop to region of interest (workspace)
    # Define bounding box in camera frame
    min_bound = np.array([-0.5, -0.5, 0.2])  # x, y, z min
    max_bound = np.array([0.5, 0.5, 1.0])    # x, y, z max
    bbox = o3d.geometry.AxisAlignedBoundingBox(min_bound, max_bound)
    pcd_cropped = pcd_clean.crop(bbox)
    
    # 4. Plane segmentation (RANSAC) to find table
    plane_model, inliers = pcd_cropped.segment_plane(
        distance_threshold=0.01,
        ransac_n=3,
        num_iterations=1000
    )
    
    # 5. Extract objects (points NOT on the table)
    pcd_objects = pcd_cropped.select_by_index(inliers, invert=True)
    
    # 6. Cluster the remaining points (individual objects)
    labels = np.array(pcd_objects.cluster_dbscan(
        eps=0.02,
        min_points=50
    ))
    
    return pcd_objects, labels
```

### Using PCL with ROS2 (C++)

```cpp
#include <pcl/point_cloud.h>
#include <pcl/point_types.h>
#include <pcl/filters/voxel_grid.h>
#include <pcl/filters/passthrough.h>
#include <pcl/segmentation/sac_segmentation.h>
#include <pcl/segmentation/extract_clusters.h>
#include <pcl_conversions/pcl_conversions.h>

void cloudCallback(const sensor_msgs::msg::PointCloud2::SharedPtr msg)
{
    // Convert ROS message to PCL
    pcl::PointCloud<pcl::PointXYZRGB>::Ptr cloud(new pcl::PointCloud<pcl::PointXYZRGB>);
    pcl::fromROSMsg(*msg, *cloud);
    
    // Voxel grid downsampling
    pcl::VoxelGrid<pcl::PointXYZRGB> vg;
    pcl::PointCloud<pcl::PointXYZRGB>::Ptr cloud_filtered(new pcl::PointCloud<pcl::PointXYZRGB>);
    vg.setInputCloud(cloud);
    vg.setLeafSize(0.005f, 0.005f, 0.005f);
    vg.filter(*cloud_filtered);
    
    // PassThrough filter for Z (depth)
    pcl::PassThrough<pcl::PointXYZRGB> pass;
    pass.setInputCloud(cloud_filtered);
    pass.setFilterFieldName("z");
    pass.setFilterLimits(0.2, 1.0);
    pass.filter(*cloud_filtered);
    
    // RANSAC plane segmentation
    pcl::SACSegmentation<pcl::PointXYZRGB> seg;
    pcl::ModelCoefficients::Ptr coefficients(new pcl::ModelCoefficients);
    pcl::PointIndices::Ptr inliers(new pcl::PointIndices);
    
    seg.setOptimizeCoefficients(true);
    seg.setModelType(pcl::SACMODEL_PLANE);
    seg.setMethodType(pcl::SAC_RANSAC);
    seg.setDistanceThreshold(0.01);
    seg.setInputCloud(cloud_filtered);
    seg.segment(*inliers, *coefficients);
    
    // Extract objects (non-plane points)
    pcl::ExtractIndices<pcl::PointXYZRGB> extract;
    pcl::PointCloud<pcl::PointXYZRGB>::Ptr cloud_objects(new pcl::PointCloud<pcl::PointXYZRGB>);
    extract.setInputCloud(cloud_filtered);
    extract.setIndices(inliers);
    extract.setNegative(true);  // Get points NOT on plane
    extract.filter(*cloud_objects);
    
    // Euclidean clustering
    pcl::search::KdTree<pcl::PointXYZRGB>::Ptr tree(new pcl::search::KdTree<pcl::PointXYZRGB>);
    tree->setInputCloud(cloud_objects);
    
    std::vector<pcl::PointIndices> cluster_indices;
    pcl::EuclideanClusterExtraction<pcl::PointXYZRGB> ec;
    ec.setClusterTolerance(0.02);
    ec.setMinClusterSize(100);
    ec.setMaxClusterSize(25000);
    ec.setSearchMethod(tree);
    ec.setInputCloud(cloud_objects);
    ec.extract(cluster_indices);
    
    // Process each cluster...
}
```

---

## 7. Object Detection Pipeline

### Approach Overview

For pick-and-place, we need to:
1. **Detect** objects in the scene
2. **Localize** them in 3D (get pose)
3. **Identify** what they are (optional, for sorting)
4. **Plan grasps** based on geometry

### Simple Geometric Detection

For known object shapes, use geometric fitting:

```python
def detect_cylindrical_objects(pcd, min_radius=0.02, max_radius=0.05):
    """Detect cylindrical objects (e.g., cans, bottles)."""
    
    # After clustering, for each cluster:
    clusters = []  # From previous clustering step
    
    detected_cylinders = []
    for cluster_pcd in clusters:
        # Compute centroid
        centroid = np.mean(np.asarray(cluster_pcd.points), axis=0)
        
        # Compute bounding box
        bbox = cluster_pcd.get_axis_aligned_bounding_box()
        extent = bbox.get_extent()
        
        # Simple heuristic: cylinder has one dimension much larger
        dims = sorted(extent)
        if dims[2] > 2 * dims[1]:  # Height > 2 * diameter
            radius = (dims[0] + dims[1]) / 4
            if min_radius < radius < max_radius:
                detected_cylinders.append({
                    'centroid': centroid,
                    'radius': radius,
                    'height': dims[2],
                    'bbox': bbox
                })
    
    return detected_cylinders
```

### Using Color for Object Identification

```python
def segment_by_color(pcd, target_color_hsv, tolerance=20):
    """Segment points by color in HSV space."""
    import cv2
    
    colors = np.asarray(pcd.colors) * 255  # Open3D uses 0-1 range
    colors_bgr = colors[:, ::-1].astype(np.uint8).reshape(-1, 1, 3)
    colors_hsv = cv2.cvtColor(colors_bgr, cv2.COLOR_BGR2HSV).reshape(-1, 3)
    
    # Create mask for target color
    lower = np.array([target_color_hsv[0] - tolerance, 50, 50])
    upper = np.array([target_color_hsv[0] + tolerance, 255, 255])
    mask = cv2.inRange(colors_hsv, lower, upper)
    
    # Extract matching points
    indices = np.where(mask > 0)[0]
    filtered_pcd = pcd.select_by_index(indices)
    
    return filtered_pcd
```

### Computing Grasp Poses

For simple top-down grasps:

```python
def compute_top_grasp_pose(cluster_centroid, table_height, approach_height=0.1):
    """Compute a top-down grasp pose for an object."""
    from geometry_msgs.msg import Pose
    from scipy.spatial.transform import Rotation
    
    pose = Pose()
    
    # Position: above the object centroid
    pose.position.x = cluster_centroid[0]
    pose.position.y = cluster_centroid[1]
    pose.position.z = cluster_centroid[2] + approach_height
    
    # Orientation: gripper pointing down (Z-axis down in tool frame)
    # Adjust based on your gripper's convention
    r = Rotation.from_euler('xyz', [180, 0, 0], degrees=True)
    q = r.as_quat()  # [x, y, z, w]
    
    pose.orientation.x = q[0]
    pose.orientation.y = q[1]
    pose.orientation.z = q[2]
    pose.orientation.w = q[3]
    
    return pose
```

### Frame Transformations

Objects detected in the camera frame must be transformed to the robot base frame:

```python
import tf2_ros
from tf2_geometry_msgs import do_transform_pose
from geometry_msgs.msg import PoseStamped

class ObjectDetector(Node):
    def __init__(self):
        super().__init__('object_detector')
        
        # TF buffer and listener
        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer, self)
    
    def transform_to_base(self, pose_camera_frame: PoseStamped) -> PoseStamped:
        """Transform pose from camera frame to robot base frame."""
        try:
            transform = self.tf_buffer.lookup_transform(
                'base_link',
                pose_camera_frame.header.frame_id,
                rclpy.time.Time(),
                timeout=rclpy.duration.Duration(seconds=1.0)
            )
            pose_base_frame = do_transform_pose(pose_camera_frame.pose, transform)
            
            result = PoseStamped()
            result.header.frame_id = 'base_link'
            result.header.stamp = self.get_clock().now().to_msg()
            result.pose = pose_base_frame
            return result
            
        except tf2_ros.TransformException as e:
            self.get_logger().error(f'Transform failed: {e}')
            return None
```

---

## 8. MoveIt2 Perception Integration

### Octomap for Collision Avoidance

MoveIt2 can automatically build an occupancy map (Octomap) from point cloud data, enabling collision-aware planning.

**Configuration File: `sensors.yaml`**

```yaml
sensors:
  - sensor_plugin: occupancy_map_monitor/PointCloudOctomapUpdater
    point_cloud_topic: /camera/camera/depth/color/points
    max_range: 2.5
    point_subsample: 1
    padding_offset: 0.03
    padding_scale: 1.0
    max_update_rate: 1.0
    filtered_cloud_topic: filtered_cloud
```

**Launch Configuration:**

```python
# In your launch file
octomap_config = {
    'octomap_frame': 'camera_depth_optical_frame',
    'octomap_resolution': 0.025,  # 2.5cm voxels
    'max_range': 2.5,
}

sensors_config = load_yaml('your_package', 'config/sensors.yaml')

move_group_node = Node(
    package='moveit_ros_move_group',
    executable='move_group',
    parameters=[
        robot_description,
        robot_description_semantic,
        octomap_config,
        sensors_config,
        # ... other parameters
    ],
)
```

### Visualizing the Octomap

In RViz:
1. Add "MotionPlanning" display
2. Expand "Scene Geometry"
3. Check "Show Scene Geometry"
4. Set "Voxel Coloring" to "Z-Axis" or "Occupied"

### Adding Detected Objects as Collision Objects

Rather than relying solely on Octomap (which can be noisy), add detected objects as explicit collision primitives:

```python
from moveit_msgs.msg import CollisionObject
from shape_msgs.msg import SolidPrimitive
from geometry_msgs.msg import Pose

def add_detected_object_to_scene(moveit2, object_id: str, 
                                  position: tuple, dimensions: tuple):
    """Add a detected object as a collision box."""
    
    # Using pymoveit2
    moveit2.add_collision_box(
        id=object_id,
        size=dimensions,  # (x, y, z) dimensions
        position=position,  # (x, y, z) center
        quat_xyzw=(0, 0, 0, 1),  # orientation
        frame_id='base_link'
    )
```

### Planning with Perception

```python
def plan_with_perception(moveit2, target_pose):
    """Plan a motion that avoids perceived obstacles."""
    
    # The Octomap is automatically considered by MoveIt2
    # Just plan normally
    trajectory = moveit2.plan(
        position=target_pose.position,
        quat_xyzw=(
            target_pose.orientation.x,
            target_pose.orientation.y,
            target_pose.orientation.z,
            target_pose.orientation.w
        )
    )
    
    if trajectory is None:
        print("Planning failed - possibly due to obstacles")
        return None
    
    return trajectory
```

---

## 9. Dynamic Pick and Place

### State Machine Architecture

```
┌─────────────────┐
│     IDLE        │
└────────┬────────┘
         │ Trigger
         ▼
┌─────────────────┐
│  DETECT_OBJECTS │◄───────────────┐
└────────┬────────┘                │
         │ Objects found           │
         ▼                         │
┌─────────────────┐                │
│ SELECT_TARGET   │                │
└────────┬────────┘                │
         │ Target selected         │
         ▼                         │
┌─────────────────┐                │
│ PLAN_APPROACH   │                │
└────────┬────────┘                │
         │ Plan succeeded          │
         ▼                         │
┌─────────────────┐                │
│ EXECUTE_APPROACH│                │
└────────┬────────┘                │
         │ At approach pose        │
         ▼                         │
┌─────────────────┐                │
│   PLAN_GRASP    │                │
└────────┬────────┘                │
         │ Plan succeeded          │
         ▼                         │
┌─────────────────┐                │
│  EXECUTE_GRASP  │                │
└────────┬────────┘                │
         │ At grasp pose           │
         ▼                         │
┌─────────────────┐                │
│  CLOSE_GRIPPER  │                │
└────────┬────────┘                │
         │ Gripper closed          │
         ▼                         │
┌─────────────────┐                │
│  PLAN_RETREAT   │                │
└────────┬────────┘                │
         │ Plan succeeded          │
         ▼                         │
┌─────────────────┐                │
│ EXECUTE_RETREAT │                │
└────────┬────────┘                │
         │ Retreated               │
         ▼                         │
┌─────────────────┐                │
│  PLAN_PLACE     │                │
└────────┬────────┘                │
         │ Plan succeeded          │
         ▼                         │
┌─────────────────┐                │
│ EXECUTE_PLACE   │                │
└────────┬────────┘                │
         │ At place pose           │
         ▼                         │
┌─────────────────┐                │
│  OPEN_GRIPPER   │                │
└────────┬────────┘                │
         │ Object released         │
         ▼                         │
┌─────────────────┐                │
│ RETURN_HOME     │────────────────┘
└─────────────────┘    More objects
```

### Implementation Outline

```python
#!/usr/bin/env python3
"""
Dynamic Pick and Place with RGBD Perception

This is a structural outline - implementation details will depend on
your specific setup and requirements.
"""

import rclpy
from rclpy.node import Node
from rclpy.callback_groups import ReentrantCallbackGroup
from sensor_msgs.msg import PointCloud2
from geometry_msgs.msg import PoseStamped
from pymoveit2 import MoveIt2, MoveIt2State, GripperInterface
from enum import Enum, auto
import threading


class PickPlaceState(Enum):
    IDLE = auto()
    DETECTING = auto()
    PLANNING_APPROACH = auto()
    EXECUTING_APPROACH = auto()
    PLANNING_GRASP = auto()
    EXECUTING_GRASP = auto()
    CLOSING_GRIPPER = auto()
    PLANNING_RETREAT = auto()
    EXECUTING_RETREAT = auto()
    PLANNING_PLACE = auto()
    EXECUTING_PLACE = auto()
    OPENING_GRIPPER = auto()
    RETURNING_HOME = auto()


class DynamicPickPlace(Node):
    def __init__(self):
        super().__init__('dynamic_pick_place')
        
        self.callback_group = ReentrantCallbackGroup()
        
        # State
        self.state = PickPlaceState.IDLE
        self.detected_objects = []
        self.current_target = None
        
        # Point cloud subscriber
        self.pc_sub = self.create_subscription(
            PointCloud2,
            '/camera/camera/depth/color/points',
            self.point_cloud_callback,
            10,
            callback_group=self.callback_group
        )
        self.latest_cloud = None
        
        # TODO: Initialize MoveIt2 interface
        # self.moveit2 = MoveIt2(...)
        # self.gripper = GripperInterface(...)
        
        # Place location (fixed for this example)
        self.place_pose = PoseStamped()
        self.place_pose.header.frame_id = 'base_link'
        self.place_pose.pose.position.x = 0.3
        self.place_pose.pose.position.y = 0.3
        self.place_pose.pose.position.z = 0.1
        # Set orientation...
        
        # State machine timer
        self.timer = self.create_timer(0.1, self.state_machine_tick)
        
        self.get_logger().info('Dynamic Pick and Place initialized')
    
    def point_cloud_callback(self, msg: PointCloud2):
        """Store latest point cloud for processing."""
        self.latest_cloud = msg
    
    def detect_objects(self) -> list:
        """
        Process point cloud to detect graspable objects.
        Returns list of object poses in base_link frame.
        """
        if self.latest_cloud is None:
            return []
        
        # TODO: Implement point cloud processing
        # 1. Convert to PCL/Open3D
        # 2. Filter and crop
        # 3. Segment table
        # 4. Cluster objects
        # 5. Compute centroids
        # 6. Transform to base_link frame
        
        detected = []
        # ... processing ...
        return detected
    
    def select_target(self, objects: list):
        """Select which object to pick (e.g., closest, specific color)."""
        if not objects:
            return None
        
        # Simple strategy: pick closest to robot base
        # TODO: Implement selection logic
        return objects[0]
    
    def compute_grasp_poses(self, target_pose: PoseStamped) -> dict:
        """Compute approach, grasp, and retreat poses."""
        approach_height = 0.10  # 10cm above object
        grasp_height = 0.02     # 2cm above object center (adjust for your gripper)
        
        poses = {
            'approach': PoseStamped(),
            'grasp': PoseStamped(),
            'retreat': PoseStamped(),
        }
        
        # TODO: Compute actual poses based on target and gripper geometry
        
        return poses
    
    def state_machine_tick(self):
        """Main state machine loop."""
        
        if self.state == PickPlaceState.IDLE:
            # Wait for trigger or automatically start
            pass
        
        elif self.state == PickPlaceState.DETECTING:
            self.detected_objects = self.detect_objects()
            if self.detected_objects:
                self.current_target = self.select_target(self.detected_objects)
                self.state = PickPlaceState.PLANNING_APPROACH
            else:
                self.get_logger().info('No objects detected')
                self.state = PickPlaceState.IDLE
        
        elif self.state == PickPlaceState.PLANNING_APPROACH:
            # TODO: Plan motion to approach pose
            # If success: self.state = PickPlaceState.EXECUTING_APPROACH
            # If failure: handle error
            pass
        
        # ... implement remaining states ...
        
        elif self.state == PickPlaceState.RETURNING_HOME:
            # TODO: Return to home position
            # Check if more objects to pick
            self.state = PickPlaceState.IDLE
    
    def start_pick_place(self):
        """Trigger the pick and place sequence."""
        if self.state == PickPlaceState.IDLE:
            self.state = PickPlaceState.DETECTING


def main():
    rclpy.init()
    node = DynamicPickPlace()
    
    # Use multi-threaded executor for callbacks
    executor = rclpy.executors.MultiThreadedExecutor()
    executor.add_node(node)
    
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
```

### Key Considerations for Robust Pick and Place

**Perception:**
- Re-detect objects between picks (scene changes)
- Handle occlusions from the robot arm
- Filter outliers and noise
- Validate detected poses are reachable

**Motion Planning:**
- Use approach/retreat motions (don't dive straight at objects)
- Consider gripper clearance
- Plan in joint space for reliability, Cartesian for precision
- Have fallback strategies if planning fails

**Grasping:**
- Verify grasp success (force feedback if available)
- Handle grasp failures gracefully
- Consider object slip detection

**Error Recovery:**
- Timeout handling for all states
- Re-planning on execution failure
- Safe return to home on unrecoverable errors

---

## 10. Troubleshooting

### Camera Issues

| Problem | Possible Cause | Solution |
|---------|---------------|----------|
| No topics published | Camera not recognized | Check USB connection, run `rs-enumerate-devices` |
| Low framerate | USB 2.0 connection | Use USB 3.0 port, shorter cable |
| Noisy depth | IR interference / sunlight | Reduce ambient IR, shade sensor |
| Missing point cloud | `pointcloud.enable:=false` | Add parameter to launch |
| Misaligned RGB/depth | `align_depth.enable:=false` | Enable depth alignment |

### TF Issues

```bash
# View TF tree
ros2 run tf2_tools view_frames

# Check specific transform
ros2 run tf2_ros tf2_echo base_link camera_link

# Monitor TF for errors
ros2 run tf2_ros tf2_monitor
```

### Point Cloud Processing Issues

| Problem | Possible Cause | Solution |
|---------|---------------|----------|
| Empty cloud after filtering | Filter bounds too restrictive | Visualize intermediate steps, adjust bounds |
| No table detected | RANSAC threshold wrong | Adjust `distance_threshold` |
| Objects merged | Clustering tolerance too high | Reduce `eps` parameter |
| Too many clusters | Clustering tolerance too low | Increase `eps` or `min_points` |

### MoveIt2 Perception Issues

| Problem | Possible Cause | Solution |
|---------|---------------|----------|
| No Octomap visible | Wrong topic / frame | Check `point_cloud_topic` matches, verify TF |
| Octomap includes robot | Self-filtering not working | Check URDF collision geometry |
| Planning ignores Octomap | Scene not published | Verify planning scene is active |
| Slow Octomap updates | High resolution / large cloud | Increase `point_subsample`, reduce resolution |

### Useful Debug Commands

```bash
# Check camera topics
ros2 topic list | grep camera
ros2 topic hz /camera/camera/depth/color/points

# Visualize point cloud
rviz2
# Add PointCloud2 display

# Check TF
ros2 run tf2_ros tf2_echo base_link camera_depth_optical_frame

# Check MoveIt planning scene
ros2 topic echo /monitored_planning_scene

# Verify octomap
ros2 topic echo /move_group/filtered_cloud
```

---

## References

- [Intel RealSense ROS2 Wrapper](https://github.com/IntelRealSense/realsense-ros)
- [MoveIt2 Perception Pipeline](https://moveit.picknik.ai/main/doc/examples/perception_pipeline/perception_pipeline_tutorial.html)
- [MoveIt2 Hand-Eye Calibration](https://moveit.picknik.ai/main/doc/examples/hand_eye_calibration/hand_eye_calibration_tutorial.html)
- [Open3D Documentation](http://www.open3d.org/docs/)
- [PCL Tutorials](https://pcl.readthedocs.io/projects/tutorials/en/latest/)
- [ROS2 TF2 Tutorials](https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Tf2/Tf2-Main.html)

---

*This guide is intended for the Duke Robotics Lab. Specific parameters and configurations may need adjustment for your particular hardware setup and application requirements.*
