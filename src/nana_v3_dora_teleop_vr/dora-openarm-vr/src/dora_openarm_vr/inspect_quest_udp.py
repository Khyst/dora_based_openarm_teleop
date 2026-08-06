# Copyright 2026 Enactic, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Meta Quest3 UDP Packet Inspector CLI tool.

Parses and inspects incoming UDP packets from Meta Quest 3 teleoperation app,
displaying field breakdown, data types, and packet reception frequency (Hz).
"""

import argparse
import json
import socket
import time

_DEFAULT_HOST = "0.0.0.0"
_DEFAULT_PORT = 5006

_EXPECTED_KEYS = {
    "t": "Headset Monotonic Timestamp",
    "rf": "Reference (HMD) Pose Dict",
    "rc": "Right Controller Pose Dict",
    "lc": "Left Controller Pose Dict",
    "rt": "Right Index Trigger (0.0-1.0)",
    "lt": "Left Index Trigger (0.0-1.0)",
    "rg": "Right Grip Button (0.0-1.0)",
    "lg": "Left Grip Button (0.0-1.0)",
    "rsx": "Right Stick X (-1.0 to 1.0)",
    "rsy": "Right Stick Y (-1.0 to 1.0)",
    "lsx": "Left Stick X (-1.0 to 1.0)",
    "lsy": "Left Stick Y (-1.0 to 1.0)",
    "a": "A Button (bool)",
    "b": "B Button (bool)",
    "x": "X Button (bool)",
    "y": "Y Button (bool)",
    "v": "Overall Validity (0:OK, 1:STALE, 2:INVALID)",
    "vr": "Right Controller Validity (0:OK, 1:STALE, 2:INVALID)",
    "vl": "Left Controller Validity (0:OK, 1:STALE, 2:INVALID)",
}


def print_packet_analysis(msg: dict, packet_idx: int, addr: tuple[str, int]) -> None:
    print(f"\n=================== [ Packet #{packet_idx} from {addr[0]}:{addr[1]} ] ===================")
    print(f"{'Key':<8} | {'Present':<7} | {'Type':<10} | {'Sample / Value Summary'}")
    print("-" * 75)

    present_keys = set(msg.keys())
    
    for key, desc in _EXPECTED_KEYS.items():
        if key in msg:
            val = msg[key]
            val_type = type(val).__name__
            if isinstance(val, dict):
                val_str = f"keys: {list(val.keys())}"
            else:
                val_str = str(val)
            print(f"{key:<8} | {'YES':<7} | {val_type:<10} | {val_str}")
        else:
            print(f"{key:<8} | {'NO':<7} | {'N/A':<10} | (Not provided in packet)")

    # Check for any unexpected or custom extra keys
    extra_keys = present_keys - set(_EXPECTED_KEYS.keys())
    if extra_keys:
        print("\n--- Additional / Custom Keys Found in Packet ---")
        for key in extra_keys:
            val = msg[key]
            print(f"{key:<8} | {'YES':<7} | {type(val).__name__:<10} | {val}")

    print("\n[Parsed Pose Quick View]")
    for pose_key in ["rf", "rc", "lc"]:
        if pose_key in msg and isinstance(msg[pose_key], dict):
            p = msg[pose_key]
            pos_str = f"pos=({p.get('x',0):.3f}, {p.get('y',0):.3f}, {p.get('z',0):.3f})"
            quat_str = f"quat=(w:{p.get('qw',1):.3f}, x:{p.get('qx',0):.3f}, y:{p.get('qy',0):.3f}, z:{p.get('qz',0):.3f})"
            print(f"  - {pose_key.upper()} ({_EXPECTED_KEYS[pose_key].split()[0]}): {pos_str} | {quat_str}")


def inspect_quest_udp(host: str, port: int, timeout: float, count: int) -> None:
    print(f"[Quest3 UDP Inspector] Listening on {host}:{port}...")
    print("Press Ctrl+C to stop listening.\n")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.settimeout(timeout)

    try:
        sock.bind((host, port))
    except Exception as e:
        print(f"[Error] Failed to bind UDP socket on {host}:{port} — {e}")
        return

    received = 0
    start_time = time.time()
    last_recv_time = start_time
    intervals = []

    try:
        while count <= 0 or received < count:
            try:
                data, addr = sock.recvfrom(65535)
                now = time.time()
                received += 1
                
                if received > 1:
                    intervals.append(now - last_recv_time)
                last_recv_time = now

                raw_str = data.decode("utf-8", errors="replace").strip()
                try:
                    msg = json.loads(raw_str)
                    print_packet_analysis(msg, received, addr)
                except json.JSONDecodeError as je:
                    print(f"[Warning] Received packet #{received} from {addr} but JSON decode failed: {je}")
                    print(f"Raw string: {raw_str[:200]}")

            except socket.timeout:
                print(f"[Timeout] Waiting for Quest3 UDP packet on {host}:{port} ({timeout}s elapsed with no data)...")
                if count > 0 and received == 0:
                    break

    except KeyboardInterrupt:
        print("\n[Stopped] User interrupted inspection.")
    finally:
        sock.close()

    total_elapsed = time.time() - start_time
    print(f"\n=================== [ Inspection Summary ] ===================")
    print(f"Total Packets Received : {received}")
    print(f"Total Elapsed Time     : {total_elapsed:.2f} seconds")
    if intervals:
        avg_dt = sum(intervals) / len(intervals)
        avg_hz = 1.0 / avg_dt if avg_dt > 0 else 0.0
        print(f"Average Packet Rate    : {avg_hz:.1f} Hz (dt = {avg_dt * 1000.0:.2f} ms)")
    print("==============================================================")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Inspect and parse raw Quest 3 UDP packets."
    )
    parser.add_argument("--host", default=_DEFAULT_HOST, help="Host/IP to bind (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=_DEFAULT_PORT, help="UDP port (default: 5006)")
    parser.add_argument(
        "--timeout",
        type=float,
        default=5.0,
        help="Timeout in seconds when waiting for packet (default: 5.0)",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=3,
        help="Number of packets to inspect before exiting (0 for continuous mode, default: 3)",
    )
    args = parser.parse_args()
    inspect_quest_udp(host=args.host, port=args.port, timeout=args.timeout, count=args.count)


if __name__ == "__main__":
    main()
