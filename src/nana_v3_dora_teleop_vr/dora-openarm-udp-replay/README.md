# dora-openarm-udp-replay

Provides recorder (`dora-openarm-udp-recorder`) and player (`dora-openarm-udp-player`) Dora nodes for VR UDP teleoperation telemetry.

## Usage
- **Recorder**: Records incoming VR telemetry inputs into a JSONL session file.
  `dora-openarm-udp-recorder --file recordings/vr_session.jsonl`
- **Player**: Replays recorded VR telemetry inputs to downstream Dora nodes (IK, Mujoco, Follower, Hamsa).
  `dora-openarm-udp-player --file recordings/vr_session.jsonl [--loop]`
