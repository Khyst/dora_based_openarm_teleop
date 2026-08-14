# dora-openarm-foxglove

A [Dora](https://dora-rs.ai/) node that runs a [Foxglove Studio](https://foxglove.dev/) WebSocket server to visualize NANA v3 robot joint states, 3D transform frames (`/tf`), and Meta Quest VR telemetry in real time.

## Topics Provided

- `/robot/joint_states` (`foxglove.JointState`): Real-time joint positions for left/right arms and grippers.
- `/tf` (`foxglove.FrameTransforms`): 3D pose tracking for Quest 3 headset (`quest_headset`) and left/right controllers (`quest_controller_left`, `quest_controller_right`).
- `/quest/inputs` (`custom.QuestInputs`): Real-time trigger percentage values (0.0~100.0%) and button states (`a`, `b`, `x`, `y`).

## CLI Usage

```bash
dora-openarm-foxglove --host 0.0.0.0 --port 8765
```
