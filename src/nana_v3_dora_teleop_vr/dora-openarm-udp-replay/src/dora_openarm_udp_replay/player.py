#!/usr/bin/env python3

import argparse
import json
import logging
import os
from pathlib import Path
import threading
import time

import dora
import pyarrow as pa

logging.basicConfig(level=logging.INFO, format="[dora-udp-player] %(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def play_session(node, file_path: Path, loop: bool, speed: float):
    if not file_path.exists():
        logger.error(f"Record file not found: {file_path}")
        return

    logger.info(f"Loading recorded session from: {file_path}")
    records = []
    with file_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))

    if not records:
        logger.error("No valid recorded events found in file.")
        return

    logger.info(f"Loaded {len(records)} events. Starting playback (speed={speed}x, loop={loop})...")

    while True:
        playback_start = time.time()
        first_rel_time = records[0].get("rel_time", 0.0)

        for record in records:
            event_id = record["id"]
            data = record["data"]
            data_type = record.get("type", "float32")
            rel_time = record.get("rel_time", 0.0)

            target_elapsed = (rel_time - first_rel_time) / max(speed, 0.01)
            actual_elapsed = time.time() - playback_start
            wait_sec = target_elapsed - actual_elapsed

            if wait_sec > 0:
                time.sleep(wait_sec)

            if data_type == "bool":
                pa_arr = pa.array([bool(x) for x in data], type=pa.bool_())
            else:
                pa_arr = pa.array([float(x) for x in data], type=pa.float32())

            node.send_output(event_id, pa_arr)

        logger.info("Finished one playback cycle.")
        if not loop:
            break
        logger.info("Looping playback...")


def main():
    parser = argparse.ArgumentParser(description="Dora VR UDP Telemetry Player Node")
    parser.add_argument(
        "--file",
        type=str,
        default="recordings/vr_session.jsonl",
        help="Recorded telemetry filepath to replay",
    )
    parser.add_argument("--loop", action="store_true", help="Loop playback endlessly")
    parser.add_argument("--speed", type=float, default=1.0, help="Playback speed multiplier (default: 1.0)")
    args = parser.parse_args()

    file_path = Path(args.file).resolve()
    node = dora.Node()

    # Start playback thread
    t = threading.Thread(
        target=play_session,
        args=(node, file_path, args.loop, args.speed),
        daemon=True,
    )
    t.start()

    logger.info("dora-udp-player node running...")
    # Keep node alive listening to ticks/stop events
    for event in node:
        if event["type"] == "STOP":
            logger.info("Received STOP event. Exiting player...")
            break


if __name__ == "__main__":
    main()
