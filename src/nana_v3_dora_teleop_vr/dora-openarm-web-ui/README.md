# dora-openarm-web-ui

Three.js & WebGL based Cyberpunk 3D Web Visualizer and Trajectory Recording UI for OpenArm Teleoperation system in `dora-rs`.

## Features
- **Three.js 3D Viewport**: Real-time rendering of OpenArm 3D kinematic mesh robot and tracked HMD/Controller VR poses.
- **Precision Coordinate Transformation**: Strict ROS/MuJoCo (Z-Up) to Three.js (Y-Up) conversion.
- **Recording Mode**: Toggle recording using Button X / A (or keyboard 'X' / 'A').
- **Waypoint Trajectory Capture**: Save trajectory waypoints using Button Y / B (or keyboard 'Y' / 'B').
- **4-Tier Data Panels**: Real-time display of Joint States, Tracked Poses, Button States, and Trigger Progress Bars.
